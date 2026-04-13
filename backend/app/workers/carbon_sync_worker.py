from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.core.redis import get_redis_pool
from app.core.slack import SlackService
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.workers.job_runtime import MAX_RETRIES, parse_job, push_to_dlq, retry_key

log = get_logger(__name__)

QUEUE_KEY = "carbon:queue"


async def process_carbon_sync(raw_payload: str) -> None:
    job = parse_job(QUEUE_KEY, raw_payload)
    if job.account_id is None:
        log.error("carbon_sync.invalid_payload", payload=raw_payload)
        return

    redis = get_redis_pool()
    account_id_str = str(job.account_id)

    try:
        async with async_session_factory() as db:
            from app.domains.cloud_accounts.models import CloudAccount
            from app.domains.cloud_ledger.service import CloudLedgerService
            from sqlalchemy import select

            result = await db.execute(select(CloudAccount).where(CloudAccount.id == job.account_id))
            account = result.scalar_one_or_none()
            if not account:
                log.warning("carbon_sync.account_not_found", account_id=account_id_str)
                return

            if job.org_id and account.org_id != job.org_id:
                log.error(
                    "carbon_sync.org_mismatch",
                    account_id=account_id_str,
                    expected_org_id=str(job.org_id),
                    actual_org_id=str(account.org_id),
                )
                return

            end = date.today()
            start = end - timedelta(days=90)

            service = CloudLedgerService(db)
            records = await service.ingest_carbon_account(account.org_id, account.id, start, end)
            await db.commit()
            await redis.delete(retry_key(QUEUE_KEY, raw_payload))
            log.info("carbon_sync.completed", account_id=account_id_str, carbon_records=records)

    except Exception as e:
        attempts = await redis.incr(retry_key(QUEUE_KEY, raw_payload))
        if attempts < MAX_RETRIES:
            backoff_seconds = min(60, 2 ** attempts)
            log.warning(
                "carbon_sync.retry_scheduled",
                account_id=account_id_str,
                attempts=attempts,
                backoff_seconds=backoff_seconds,
                error=str(e),
            )
            await asyncio.sleep(backoff_seconds)
            await redis.lpush(QUEUE_KEY, raw_payload)
            return

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

        log.error("carbon_sync.failed_to_dlq", account_id=account_id_str, error=str(e))
        subject = "[CauSium][Critical] Carbon sync worker failure"
        body = (
            "A critical failure occurred in carbon sync worker and was moved to DLQ.\n\n"
            f"account_id: {account_id_str}\n"
            f"org_id: {str(job.org_id) if job.org_id else 'unknown'}\n"
            f"error: {str(e)}\n"
        )
        await EmailService().send_critical_alert(subject=subject, text_body=body)

        async with async_session_factory() as db:
            if job.org_id:
                await NotificationsService(db).create_if_rule_matches(
                    org_id=job.org_id,
                    category=AlertCategory.GOVERNANCE,
                    severity=AlertSeverity.CRITICAL,
                    event_type="worker.carbon_sync.dlq_failure",
                    title="Critical carbon sync worker failure",
                    body=body,
                    source_type="worker_failure",
                    source_id=f"carbon_sync:{account_id_str}:{attempts}",
                )
                await db.commit()
            await SlackService(db).send_critical_alert(
                org_id=job.org_id,
                subject=subject,
                text_body=body,
            )


async def run_carbon_sync_worker() -> None:
    redis = get_redis_pool()
    log.info("carbon_sync_worker.started")
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw_payload = item
                await process_carbon_sync(raw_payload)
        except Exception as e:
            log.error("carbon_sync_worker.error", error=str(e))
            await asyncio.sleep(5)
