from __future__ import annotations
"""Ingestion worker — polls Redis queue for account IDs and ingests cost/event data."""
import asyncio
from datetime import date, timedelta
from uuid import UUID

from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.core.redis import get_redis_pool

log = get_logger(__name__)

QUEUE_KEY = "ingestion:queue"
LOCK_TTL = 3600  # 1 hour


async def process_account(account_id_str: str) -> None:
    account_id = UUID(account_id_str)
    lock_key = f"ingestion:lock:{account_id_str}"
    redis = get_redis_pool()

    # Distributed lock to prevent duplicate ingestion
    acquired = await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True)
    if not acquired:
        log.info("ingestion.skipped.locked", account_id=account_id_str)
        return

    try:
        async with async_session_factory() as db:
            from app.domains.cloud_accounts.service import CloudAccountService
            from app.domains.cloud_ledger.service import CloudLedgerService

            account_service = CloudAccountService(db)

            # Find the account (we need org_id — look up by account_id directly)
            from sqlalchemy import select
            from app.domains.cloud_accounts.models import CloudAccount

            result = await db.execute(select(CloudAccount).where(CloudAccount.id == account_id))
            account = result.scalar_one_or_none()
            if not account:
                log.warning("ingestion.account_not_found", account_id=account_id_str)
                return

            end = date.today()
            start = end - timedelta(days=7)

            ledger = CloudLedgerService(db)
            result = await ledger.ingest_account(account.org_id, account_id, start, end)
            await db.commit()

            log.info(
                "ingestion.completed",
                account_id=account_id_str,
                costs=result.cost_records,
                events=result.event_records,
            )

            # Queue scoring after successful ingestion
            await redis.lpush("scoring:queue", account_id_str)

    except Exception as e:
        log.error("ingestion.failed", account_id=account_id_str, error=str(e))
        await EmailService().send_critical_alert(
            subject="[StratoPulse][Critical] Ingestion worker failure",
            text_body=(
                "A critical failure occurred in ingestion worker.\n\n"
                f"account_id: {account_id_str}\n"
                f"error: {str(e)}\n"
            ),
        )
    finally:
        await redis.delete(lock_key)


async def run_ingestion_worker() -> None:
    redis = get_redis_pool()
    log.info("ingestion_worker.started")
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, account_id_str = item
                log.info("ingestion.dequeued", account_id=account_id_str)
                await process_account(account_id_str)
        except Exception as e:
            log.error("ingestion_worker.error", error=str(e))
            await asyncio.sleep(5)
