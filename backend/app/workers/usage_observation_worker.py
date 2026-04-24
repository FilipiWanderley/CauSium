from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.domains.intel.usage_observation_service import UsageObservationService

log = get_logger(__name__)


async def run_once() -> None:
    async with async_session_factory() as db:
        svc = UsageObservationService(db)
        result = await svc.ingest_recent_usage_observations(window_hours=3)
        await db.commit()
        log.info(
            "usage_observation_worker.cycle_done",
            scanned_accounts=result.scanned_accounts,
            created_rows=result.created_rows,
            deleted_rows=result.deleted_rows,
        )


async def run_usage_observation_worker() -> None:
    settings = get_settings()
    interval_seconds = max(300, int(settings.usage_observation_interval_minutes) * 60)
    log.info(
        "usage_observation_worker.started",
        interval_minutes=settings.usage_observation_interval_minutes,
    )
    while True:
        try:
            await run_once()
        except Exception as exc:
            log.error("usage_observation_worker.error", error=str(exc))
        await asyncio.sleep(interval_seconds)
