from __future__ import annotations
import asyncio

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.domains.audit_chain.service import AuditChainService

log = get_logger(__name__)


async def run_audit_checkpoint_worker() -> None:
    settings = get_settings()
    interval_seconds = max(60, settings.audit_checkpoint_interval_minutes * 60)
    keep_last = max(1, settings.audit_checkpoint_retention_count)
    log.info("audit_checkpoint_worker.started", interval_seconds=interval_seconds, keep_last=keep_last)
    while True:
        try:
            async with async_session_factory() as db:
                svc = AuditChainService(db)
                stats = await svc.generate_checkpoints_for_all_orgs(keep_last=keep_last)
                log.info("audit_checkpoint_worker.tick", **stats)
        except Exception as e:
            log.error("audit_checkpoint_worker.error", error=str(e))
        await asyncio.sleep(interval_seconds)
