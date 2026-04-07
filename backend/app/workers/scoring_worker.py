from __future__ import annotations
"""Scoring worker — regenerates opportunities for accounts after ingestion."""
import asyncio
from uuid import UUID

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.core.redis import get_redis_pool

log = get_logger(__name__)

QUEUE_KEY = "scoring:queue"


async def process_scoring(account_id_str: str) -> None:
    account_id = UUID(account_id_str)
    try:
        async with async_session_factory() as db:
            from sqlalchemy import select
            from app.domains.cloud_accounts.models import CloudAccount
            from app.domains.decision_engine.service import DecisionEngineService

            result = await db.execute(select(CloudAccount).where(CloudAccount.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                log.warning("scoring.account_not_found", account_id=account_id_str)
                return

            service = DecisionEngineService(db)
            opps = await service.generate_opportunities_for_account(account.org_id, account_id)
            await db.commit()
            log.info("scoring.completed", account_id=account_id_str, opportunities=len(opps))
    except Exception as e:
        log.error("scoring.failed", account_id=account_id_str, error=str(e))


async def run_scoring_worker() -> None:
    redis = get_redis_pool()
    log.info("scoring_worker.started")
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, account_id_str = item
                await process_scoring(account_id_str)
        except Exception as e:
            log.error("scoring_worker.error", error=str(e))
            await asyncio.sleep(5)
