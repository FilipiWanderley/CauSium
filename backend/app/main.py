from __future__ import annotations
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import ensure_sqlite_schema
from app.core.logging import configure_logging, get_logger
from app.core.middleware import install_middlewares
from app.core.observability import build_sli_slo_snapshot, render_metrics_prometheus
from app.core.tracing import instrument_app, setup_tracing, shutdown_tracing

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    log.info(
        "app.lifespan.init",
        app_env=settings.app_env,
        redis_url_configured=settings.redis_enabled,
        ingestion_worker_enabled=settings.ingestion_worker_enabled,
        ingestion_interval_hours=settings.ingestion_interval_hours,
        database_url_set=bool(os.getenv("DATABASE_URL", "").strip()),
        clickhouse_host=settings.clickhouse_host,
    )

    if not os.getenv("DATABASE_URL", "").strip():
        log.error(
            "database_url.missing_env_using_sqlite_fallback",
            fallback_url=settings.database_url_effective,
        )
    if not os.getenv("REDIS_URL", "").strip():
        log.warning("redis_url.missing_env_disabling_redis")

    settings.validate_production_security()
    await ensure_sqlite_schema()
    from app.core.clickhouse_init import ensure_clickhouse_schema
    ensure_clickhouse_schema()
    setup_tracing(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        sample_ratio=settings.otel_sample_ratio,
    )
    instrument_app(app)
    log.info("app.startup", env=settings.app_env, azure_mock=not settings.azure_credentials_available)

    worker_task = None
    if settings.ingestion_worker_enabled:
        if not settings.redis_enabled:
            log.error(
                "ingestion_worker.skipped",
                reason="REDIS_URL not configured — ingestion pipeline is non-functional. "
                       "No cost/usage data will be collected until Redis is available.",
            )
        else:
            log.info("ingestion_worker.startup_requested")
            from app.workers.ingestion_worker import run_ingestion_worker
            try:
                worker_task = asyncio.create_task(run_ingestion_worker())
                log.info("ingestion_worker.task_created")
            except Exception as exc:
                log.error(
                    "ingestion_worker.startup_failed",
                    error=type(exc).__name__,
                    reason=str(exc)[:200],
                )
    else:
        log.warning("ingestion_worker.disabled", reason="INGESTION_WORKER_ENABLED=false")

    yield

    if worker_task is not None:
        worker_task.cancel()
    from app.core.redis import close_redis
    await close_redis()
    shutdown_tracing()
    log.info("app.shutdown")


settings = get_settings()

_CDN = "https://cdn.jsdelivr.net/npm"
_SWAGGER_JS = f"{_CDN}/swagger-ui-dist@5.18.2/swagger-ui-bundle.js"
_SWAGGER_CSS = f"{_CDN}/swagger-ui-dist@5.18.2/swagger-ui.css"
_REDOC_JS = f"{_CDN}/redoc@2.1.5/bundles/redoc.standalone.js"

app = FastAPI(
    title="CauSium API",
    description="FinOps + Governance + Operations platform for multi-cloud efficiency",
    version="0.1.0",
    # Disable built-in docs routes — custom routes below pin CDN asset versions.
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

required_cors_origins = [
    "https://gentle-sea-0b9925a0f.7.azurestaticapps.net",
    "http://localhost:5173",
]
allow_origins = list(dict.fromkeys(required_cors_origins + settings.cors_origins_list))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_middlewares(app)

app.include_router(api_router)


if not settings.is_production:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="CauSium API",
            swagger_js_url=_SWAGGER_JS,
            swagger_css_url=_SWAGGER_CSS,
        )

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc() -> HTMLResponse:
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="CauSium API",
            redoc_js_url=_REDOC_JS,
        )


def _is_production_runtime() -> bool:
    app_env = os.getenv("APP_ENV", settings.app_env).strip().lower()
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    return app_env == "production" or environment == "production"


def _require_internal_monitoring_key(
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
) -> None:
    if not _is_production_runtime():
        return
    expected_key = os.getenv("INTERNAL_MONITORING_KEY", "").strip()
    if not expected_key or x_internal_key != expected_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/health/detailed", dependencies=[Depends(_require_internal_monitoring_key)])
async def health_detailed():
    import time

    from app.core.clickhouse import execute_query
    from app.core.database import engine
    from app.core.redis import get_redis_pool

    checks = {}

    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        redis = get_redis_pool()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # ClickHouse
    try:
        execute_query("SELECT 1")
        checks["clickhouse"] = "ok"
    except Exception as e:
        checks["clickhouse"] = f"error: {e}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(_require_internal_monitoring_key)])
async def metrics() -> str:
    return render_metrics_prometheus()


@app.get("/metrics/slo")
async def metrics_slo(
    error_budget_pct: float = 1.0,
    api_p95_ms: float = 500.0,
):
    """SLI/SLO snapshot — JSON suitable for dashboards and CI gates."""
    return build_sli_slo_snapshot(
        error_budget_pct=error_budget_pct,
        api_p95_ms_target=api_p95_ms,
    )


@app.get("/diagnostic/tenant", dependencies=[Depends(_require_internal_monitoring_key)])
async def diagnostic_tenant(
    email: str | None = None,
    account_id: str | None = None,
):
    from sqlalchemy import select
    from app.domains.auth.models import User
    from app.domains.cloud_accounts.models import CloudAccount
    from app.core.database import async_session_factory
    
    async with async_session_factory() as session:
        if email:
            stmt = select(User.org_id).where(User.email == email)
            res = await session.execute(stmt)
            org_id = res.scalar_one_or_none()
            return {"org_id": org_id}
        if account_id:
            from uuid import UUID
            try:
                acc_uuid = UUID(account_id)
            except ValueError:
                return {"error": "Invalid account_id format"}
            stmt = select(CloudAccount.org_id).where(CloudAccount.id == acc_uuid)
            res = await session.execute(stmt)
            org_id = res.scalar_one_or_none()
            return {"org_id": org_id}
    return {"error": "Provide email or account_id"}


@app.get("/diagnostic/ingest", dependencies=[Depends(_require_internal_monitoring_key)])
async def diagnostic_ingest(org_id: str):
    from app.core.clickhouse import execute_query
    from app.domains.cloud_accounts.models import CloudAccount
    from app.core.database import async_session_factory
    from sqlalchemy import select
    from uuid import UUID
    
    try:
        org_uuid = UUID(org_id)
    except ValueError:
        return {"error": "Invalid org_id format"}

    counts = {}
    for table in ["cost_facts", "usage_facts", "event_facts"]:
        try:
            res = execute_query(f"SELECT count() as cnt FROM {table} WHERE org_id = '{org_id}'")
            counts[table] = res[0]["cnt"] if res else 0
        except Exception as e:
            counts[table] = f"error: {e}"

    # Check for mock/seed data
    mock_counts = {}
    for table in ["cost_facts", "event_facts"]:
        try:
            res = execute_query(f"SELECT count() as cnt FROM {table} WHERE org_id LIKE 'mock-%' OR org_id = '00000000-0000-0000-0000-000000000000'")
            mock_counts[f"{table}_global_mock"] = res[0]["cnt"] if res else 0
        except Exception as e:
            mock_counts[f"{table}_global_mock"] = f"error: {e}"

    # Distinct account_ids in cost_facts for this org
    distinct_accounts_in_data = []
    try:
        res = execute_query(f"SELECT DISTINCT account_id FROM cost_facts WHERE org_id = '{org_id}'")
        distinct_accounts_in_data = [r["account_id"] for r in res]
    except Exception as e:
        distinct_accounts_in_data = [f"error: {e}"]

    # Sample rows to detect mock data patterns
    sample_rows = []
    try:
        res = execute_query(f"SELECT account_id, service, cost_usd, date FROM cost_facts WHERE org_id = '{org_id}' ORDER BY date DESC LIMIT 5")
        sample_rows = res
    except Exception as e:
        sample_rows = [{"error": str(e)}]

    account_info = {}
    async with async_session_factory() as session:
        stmt = select(CloudAccount).where(CloudAccount.org_id == org_uuid)
        res = await session.execute(stmt)
        accounts = res.scalars().all()
        for acc in accounts:
            account_info[str(acc.id)] = {
                "status": acc.status,
                "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
                "external_id": acc.external_id,
                "display_name": acc.display_name,
            }

    # Cross-check: do account_ids in data match registered accounts?
    registered_account_ids = set(account_info.keys())
    data_account_ids = set(str(a) for a in distinct_accounts_in_data if not str(a).startswith("error"))
    account_id_match = registered_account_ids & data_account_ids
    account_id_mismatch = data_account_ids - registered_account_ids

    diagnosis = "unknown"
    if counts.get("cost_facts", 0) == 0:
        diagnosis = "NO_DATA — ingest has not produced any cost_facts for this org"
    elif account_id_mismatch:
        diagnosis = f"FOREIGN_DATA — cost_facts contain account_ids not belonging to this org: {account_id_mismatch}"
    elif not account_id_match:
        diagnosis = "ACCOUNT_MISMATCH — data exists but no account_id matches registered accounts"
    else:
        diagnosis = f"OK_REAL — cost_facts belong to registered account(s): {account_id_match}"

    return {
        "counts": counts,
        "mock_counts": mock_counts,
        "distinct_account_ids_in_cost_facts": distinct_accounts_in_data,
        "registered_accounts": account_info,
        "account_id_match": list(account_id_match),
        "account_id_mismatch": list(account_id_mismatch),
        "sample_rows": sample_rows,
        "diagnosis": diagnosis,
    }


@app.get("/diagnostic/sync-account", dependencies=[Depends(_require_internal_monitoring_key)])
async def diagnostic_sync_account(account_id: str, lookback_days: int = 30):
    from uuid import UUID
    from datetime import date, timedelta
    from app.core.database import async_session_factory
    from app.domains.cloud_accounts.models import CloudAccount
    from app.domains.cloud_ledger.service import CloudLedgerService
    from sqlalchemy import select

    try:
        acc_uuid = UUID(account_id)
    except ValueError:
        return {"error": "Invalid account_id format"}

    async with async_session_factory() as db:
        res = await db.execute(select(CloudAccount).where(CloudAccount.id == acc_uuid))
        account = res.scalar_one_or_none()
        if not account:
            return {"error": "Account not found"}

        end = date.today()
        start = end - timedelta(days=lookback_days)
        ledger = CloudLedgerService(db)
        result = await ledger.ingest_account(account.org_id, acc_uuid, start, end)
        await db.commit()

    return {
        "status": result.status,
        "cost_records": result.cost_records,
        "event_records": result.event_records,
        "message": result.message,
        "date_range": f"{start} → {end}",
    }


# ---------------------------------------------------------------------------
# Frontend SPA — serve React build from /home/site/wwwroot/frontend_dist
# Falls back to index.html for all non-API, non-asset routes (SPA routing).
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend_dist"

if _FRONTEND_DIST.is_dir():
    # React app assets (JS/CSS chunks)
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    # Landing page static assets — served with correct MIME types via StaticFiles
    if (_FRONTEND_DIST / "landing" / "assets").is_dir():
        app.mount("/landing/assets", StaticFiles(directory=str(_FRONTEND_DIST / "landing" / "assets")), name="landing-assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        return FileResponse(str(_FRONTEND_DIST / "favicon.svg"))

    @app.get("/", include_in_schema=False)
    async def landing_root():
        return FileResponse(str(_FRONTEND_DIST / "landing" / "index.html"), media_type="text/html")

    @app.get("/landing/favicon.svg", include_in_schema=False)
    async def landing_favicon():
        return FileResponse(str(_FRONTEND_DIST / "landing" / "favicon.svg"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Never intercept API routes — let FastAPI return 404/405 naturally.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(str(index), media_type="text/html")
