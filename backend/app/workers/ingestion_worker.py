from __future__ import annotations
"""Ingestion worker — polls Redis queue for account IDs and ingests cost/event data."""
import asyncio
import json
from datetime import date, timedelta
from uuid import UUID

from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.core.redis import get_redis_pool
from app.workers.job_runtime import MAX_RETRIES, parse_job, push_to_dlq, retry_key

log = get_logger(__name__)

QUEUE_KEY = "ingestion:queue"
LOCK_TTL = 3600  # 1 hour


async def process_account(raw_payload: str) -> None:
    job = parse_job(QUEUE_KEY, raw_payload)
    if job.account_id is None:
        log.error("ingestion.invalid_payload", payload=raw_payload)
        return

    account_id = job.account_id
    lock_key = f"ingestion:lock:{job.org_id}:{account_id}"
    account_id_str = str(account_id)
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

            # SP-WK02: org-aware isolation guard — if payload carries org_id,
            # ensure the job only touches the intended workspace.
            if job.org_id and account.org_id != job.org_id:
                log.error(
                    "ingestion.org_mismatch",
                    account_id=account_id_str,
                    expected_org_id=str(job.org_id),
                    actual_org_id=str(account.org_id),
                )
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

            await redis.delete(retry_key(QUEUE_KEY, raw_payload))

            # Queue scoring after successful ingestion
            scoring_payload = json.dumps(
                {
                    "org_id": str(account.org_id),
                    "account_id": account_id_str,
                }
            )
            await redis.lpush("scoring:queue", scoring_payload)

    except Exception as e:
        attempts = await redis.incr(retry_key(QUEUE_KEY, raw_payload))
        if attempts < MAX_RETRIES:
            await redis.lpush(QUEUE_KEY, raw_payload)
            log.error(
                "ingestion.retry_scheduled",
                account_id=account_id_str,
                attempts=attempts,
                max_retries=MAX_RETRIES,
                error=str(e),
            )
        else:
            async with async_session_factory() as db:
                await push_to_dlq(
                    db,
                    queue_name=QUEUE_KEY,
                    payload=raw_payload,
                    org_id=job.org_id,
                    account_id=job.account_id,
                    error_message=str(e),
                    retry_count=attempts,
                )
                await db.commit()
            await redis.delete(retry_key(QUEUE_KEY, raw_payload))

            log.error("ingestion.failed_to_dlq", account_id=account_id_str, error=str(e))
            await EmailService().send_critical_alert(
                subject="[StratoPulse][Critical] Ingestion worker failure",
                text_body=(
                    "A critical failure occurred in ingestion worker and was moved to DLQ.\n\n"
                    f"account_id: {account_id_str}\n"
                    f"org_id: {str(job.org_id) if job.org_id else 'unknown'}\n"
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
                _, raw_payload = item
                log.info("ingestion.dequeued", payload=raw_payload)
                await process_account(raw_payload)
        except Exception as e:
            log.error("ingestion_worker.error", error=str(e))
            await asyncio.sleep(5)
