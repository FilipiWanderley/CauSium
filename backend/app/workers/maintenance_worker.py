"""Maintenance worker — DLQ cleanup and other periodic housekeeping tasks."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.core.database import async_session_factory
from app.core.logging import get_logger

log = get_logger(__name__)

# DLQ messages older than this are purged regardless of status
DLQ_RETENTION_DAYS = 30
# Only purge 'resolved' or 'requeued' messages — keep 'open' ones for investigation
DLQ_PURGEABLE_STATUSES = ("resolved", "requeued")

# Run every 6 hours
MAINTENANCE_INTERVAL_SECONDS = 6 * 60 * 60


async def _run_dlq_cleanup() -> int:
    """Delete DLQ messages that are resolved/requeued and older than DLQ_RETENTION_DAYS.
    Returns the number of rows deleted."""
    from sqlalchemy import delete
    from app.domains.admin.models import DlqMessage, DlqStatus

    cutoff = datetime.now(timezone.utc) - timedelta(days=DLQ_RETENTION_DAYS)

    async with async_session_factory() as db:
        result = await db.execute(
            delete(DlqMessage).where(
                DlqMessage.created_at < cutoff,
                DlqMessage.status.in_([DlqStatus.RESOLVED, DlqStatus.REQUEUED]),
            )
        )
        await db.commit()
        deleted = result.rowcount
        if deleted:
            log.info("dlq.cleanup.done", deleted=deleted, cutoff=cutoff.isoformat())
        return deleted


async def run_maintenance_worker() -> None:
    log.info("maintenance_worker.started")
    while True:
        try:
            deleted = await _run_dlq_cleanup()
            log.info("maintenance_worker.cycle", dlq_purged=deleted)
        except Exception:
            log.exception("maintenance_worker.error")
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)
