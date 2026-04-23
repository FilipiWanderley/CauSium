from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.domains.auth.models import Organization, WorkspaceLifecycleState
from app.domains.intel.anomaly_detection_service import CostAnomalyDetectionService

log = get_logger(__name__)


async def run_once() -> None:
    settings = get_settings()
    async with async_session_factory() as db:
        result = await db.execute(
            select(Organization.id).where(
                Organization.is_active.is_(True),
                Organization.lifecycle_state == WorkspaceLifecycleState.ACTIVE,
            )
        )
        org_ids = list(result.scalars().all())

        svc = CostAnomalyDetectionService(db)
        for org_id in org_ids:
            try:
                run_result = await svc.detect_for_org(
                    org_id=org_id,
                    lookback_days=settings.anomaly_detection_lookback_days,
                    z_threshold=settings.anomaly_detection_zscore_threshold,
                    min_history_days=settings.anomaly_detection_min_history_days,
                    min_delta_usd=settings.anomaly_detection_min_delta_usd,
                )
                await db.commit()
                log.info(
                    "anomaly_detection.org_processed",
                    org_id=str(org_id),
                    observed_date=(
                        run_result.observed_date.isoformat() if run_result.observed_date else None
                    ),
                    scanned_services=run_result.scanned_services,
                    detected=run_result.detected,
                    created=run_result.created,
                )
            except Exception as exc:
                await db.rollback()
                log.error("anomaly_detection.org_failed", org_id=str(org_id), error=str(exc))


async def run_anomaly_detection_worker() -> None:
    settings = get_settings()
    poll_seconds = max(60, int(settings.anomaly_detection_interval_minutes) * 60)
    log.info(
        "anomaly_detection_worker.started",
        interval_minutes=settings.anomaly_detection_interval_minutes,
    )
    while True:
        try:
            await run_once()
        except Exception as exc:
            log.error("anomaly_detection_worker.error", error=str(exc))
        await asyncio.sleep(poll_seconds)
