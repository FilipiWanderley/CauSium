"""Maintenance worker — DLQ cleanup and other periodic housekeeping tasks."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from typing import cast

from sqlalchemy import select
from sqlalchemy.engine import CursorResult

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.domains.auth.anonymization import anonymize_user_identity
from app.domains.auth.models import User
from app.core.logging import get_logger

log = get_logger(__name__)

# DLQ messages older than this are purged regardless of status
DLQ_RETENTION_DAYS = 30
USER_RETENTION_DAYS = 30
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
        deleted = cast(CursorResult, result).rowcount
        if deleted:
            log.info("dlq.cleanup.done", deleted=deleted, cutoff=cutoff.isoformat())
        return deleted


async def _run_user_retention_anonymization() -> int:
    """Anonymize inactive users older than USER_RETENTION_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=USER_RETENTION_DAYS)
    secret_key = get_settings().secret_key

    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(
                User.is_active.is_(False),
                User.deleted_at.is_not(None),
                User.deleted_at < cutoff,
            )
        )
        users = result.scalars().all()
        anonymized = 0
        for user in users:
            if anonymize_user_identity(user, secret_key=secret_key):
                anonymized += 1
                log.info(
                    "user anonymized due to retention policy",
                    user_id=str(user.id),
                    deleted_at=user.deleted_at.isoformat() if user.deleted_at else None,
                )

        if anonymized:
            await db.commit()
        return anonymized


async def run_maintenance_worker() -> None:
    log.info("maintenance_worker.started")
    while True:
        try:
            deleted = await _run_dlq_cleanup()
            anonymized = await _run_user_retention_anonymization()
            log.info("maintenance_worker.cycle", dlq_purged=deleted, users_anonymized=anonymized)
        except Exception:
            log.exception("maintenance_worker.error")
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)
