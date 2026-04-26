from __future__ import annotations
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import install_middlewares
from app.core.observability import build_sli_slo_snapshot, render_metrics_prometheus
from app.core.tracing import instrument_app, setup_tracing, shutdown_tracing

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_production_security()
    setup_tracing(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        sample_ratio=settings.otel_sample_ratio,
    )
    # instrument_app must run after setup_tracing so FastAPIInstrumentor
    # receives a properly configured TracerProvider, not the no-op default.
    instrument_app(app)
    log.info("app.startup", env=settings.app_env, azure_mock=not settings.azure_credentials_available)
    yield
    from app.core.redis import close_redis
    await close_redis()
    shutdown_tracing()
    log.info("app.shutdown")


settings = get_settings()

app = FastAPI(
    title="CauSium API",
    description="FinOps + Governance + Operations platform for multi-cloud efficiency",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
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
