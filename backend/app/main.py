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

    if not os.getenv("DATABASE_URL", "").strip():
        log.error(
            "database_url.missing_env_using_sqlite_fallback",
            fallback_url=settings.database_url_effective,
        )
    if not os.getenv("REDIS_URL", "").strip():
        log.warning("redis_url.missing_env_disabling_redis")

    settings.validate_production_security()
    await ensure_sqlite_schema()
    setup_tracing(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        sample_ratio=settings.otel_sample_ratio,
    )
    instrument_app(app)
    log.info("app.startup", env=settings.app_env, azure_mock=not settings.azure_credentials_available)

    # Daily auto-sync background task — syncs all cloud accounts every 24h
    async def _daily_sync_all():
        import asyncio
        from app.core.database import async_session_factory
        from app.domains.cloud_accounts.router import _run_inline_sync_pipeline
        while True:
            await asyncio.sleep(86400)  # 24 hours
            try:
                async with async_session_factory() as db:
                    from sqlalchemy import select
                    from app.domains.cloud_accounts.models import CloudAccount
                    result = await db.execute(select(CloudAccount).where(CloudAccount.status != "archived"))
                    accounts = result.scalars().all()
                log.info("daily_sync.starting", accounts=len(accounts))
                for account in accounts:
                    try:
                        await _run_inline_sync_pipeline(account.org_id, account.account_id, lookback_days=1)
                    except Exception as exc:
                        log.warning("daily_sync.account_failed", account_id=str(account.account_id), error=str(exc))
            except Exception as exc:
                log.warning("daily_sync.failed", error=str(exc))

    sync_task = asyncio.create_task(_daily_sync_all())

    yield

    sync_task.cancel()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(str(index), media_type="text/html")
