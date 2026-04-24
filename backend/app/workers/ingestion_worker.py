from __future__ import annotations
"""Ingestion worker — polls Redis queue for account IDs and ingests cost/event data."""
import asyncio
import json
from datetime import date, timedelta
import time
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.domains.cloud_accounts.models import CloudAccount, ConnectorStatus
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.core.redis import get_redis_pool
from app.core.slack import SlackService
from app.workers.job_runtime import MAX_RETRIES, parse_job, push_to_dlq, retry_key

log = get_logger(__name__)

QUEUE_KEY = "ingestion:queue"
LOCK_TTL = 3600  # 1 hour
SCHEDULED_SYNC_LOCK_PREFIX = "ingestion:scheduled"


async def enqueue_periodic_sync_jobs(interval_seconds: int, lookback_days: int) -> int:
    redis = get_redis_pool()
    queued = 0
    bucket = int(time.time() // max(interval_seconds, 1))

    async with async_session_factory() as db:
        result = await db.execute(
            select(CloudAccount.id, CloudAccount.org_id).where(
                CloudAccount.status.in_([ConnectorStatus.ACTIVE, ConnectorStatus.ERROR])
            )
        )
        accounts = result.all()

    for account_id, org_id in accounts:
        schedule_lock_key = (
            f"{SCHEDULED_SYNC_LOCK_PREFIX}:{org_id}:{account_id}:{bucket}"
        )
        acquired = await redis.set(schedule_lock_key, "1", ex=interval_seconds + 300, nx=True)
        if not acquired:
            continue

        payload = json.dumps(
            {
                "org_id": str(org_id),
                "account_id": str(account_id),
                "lookback_days": lookback_days,
            }
        )
        await redis.lpush(QUEUE_KEY, payload)
        queued += 1

    if queued > 0:
        log.info(
            "ingestion.periodic_jobs_queued",
            queued=queued,
            interval_seconds=interval_seconds,
            lookback_days=lookback_days,
        )
    return queued


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
            # Business rule: always analyze up to the last 3 months.
            # If the tenant has less historical data, connector returns only what's available.
            default_lookback_days = 90
            requested_lookback_days = job.lookback_days if job.lookback_days is not None else default_lookback_days
            lookback_days = max(7, min(requested_lookback_days, 90))
            start = end - timedelta(days=lookback_days)

            ledger = CloudLedgerService(db)
            result = await ledger.ingest_account(account.org_id, account_id, start, end)
            await db.commit()

            log.info(
                "ingestion.completed",
                account_id=account_id_str,
                lookback_days=lookback_days,
                costs=result.cost_records,
                events=result.event_records,
            )
            await NotificationsService(db).create_realtime_alert(
                org_id=account.org_id,
                category=AlertCategory.ACTIVITY,
                severity=AlertSeverity.INFO if result.status == "ok" else AlertSeverity.WARNING,
                event_type="cloud_account.sync.completed" if result.status == "ok" else "cloud_account.sync.warning",
                title=f"Sync finished for {account.display_name}",
                body=(
                    f"Costs: {result.cost_records}, events: {result.event_records}"
                    if result.status == "ok"
                    else (result.message or "Sync finished with partial errors.")
                ),
                source_type="cloud_account_sync_result",
                source_id=f"{account_id_str}:{start.isoformat()}:{end.isoformat()}",
                extra_metadata={
                    "account_id": account_id_str,
                    "lookback_days": lookback_days,
                    "status": result.status,
                },
            )

            await redis.delete(retry_key(QUEUE_KEY, raw_payload))

            # Queue downstream jobs after successful ingestion
            next_payload = json.dumps(
                {
                    "org_id": str(account.org_id),
                    "account_id": account_id_str,
                }
            )
            await redis.lpush("scoring:queue", next_payload)
            await redis.lpush("carbon:queue", next_payload)

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
                if job.org_id:
                    await NotificationsService(db).create_realtime_alert(
                        org_id=job.org_id,
                        category=AlertCategory.SECURITY,
                        severity=AlertSeverity.CRITICAL,
                        event_type="worker.ingestion.dlq_failure",
                        title="Critical ingestion worker failure",
                        body=(
                            "A critical failure occurred in ingestion worker and was moved to DLQ.\n\n"
                            f"account_id: {account_id_str}\n"
                            f"org_id: {str(job.org_id) if job.org_id else 'unknown'}\n"
                            f"error: {str(e)}\n"
                        ),
                        source_type="worker_failure",
                        source_id=f"ingestion:{account_id_str}:{attempts}",
                    )
                await db.commit()
            await redis.delete(retry_key(QUEUE_KEY, raw_payload))

            log.error("ingestion.failed_to_dlq", account_id=account_id_str, error=str(e))
            subject = "[CauSium][Critical] Ingestion worker failure"
            body = (
                "A critical failure occurred in ingestion worker and was moved to DLQ.\n\n"
                f"account_id: {account_id_str}\n"
                f"org_id: {str(job.org_id) if job.org_id else 'unknown'}\n"
                f"error: {str(e)}\n"
            )
            await EmailService().send_critical_alert(
                subject=subject,
                text_body=body,
            )
            if job.org_id:
                async with async_session_factory() as db:
                    await SlackService(db).send_critical_alert(
                        org_id=job.org_id,
                        subject=subject,
                        text_body=body,
                    )
    finally:
        await redis.delete(lock_key)


async def run_ingestion_worker() -> None:
    redis = get_redis_pool()
    settings = get_settings()
    interval_seconds = max(300, int(settings.ingestion_interval_hours) * 3600)
    lookback_days = max(7, min(int(settings.ingestion_interval_hours * 7), 90))
    next_periodic_run_at = 0.0
    log.info(
        "ingestion_worker.started",
        periodic_interval_seconds=interval_seconds,
        periodic_lookback_days=lookback_days,
    )

    while True:
        try:
            now = time.monotonic()
            if now >= next_periodic_run_at:
                await enqueue_periodic_sync_jobs(interval_seconds, lookback_days)
                next_periodic_run_at = now + interval_seconds

            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw_payload = item
                log.info("ingestion.dequeued", payload=raw_payload)
                await process_account(raw_payload)
        except Exception as e:
            log.error("ingestion_worker.error", error=str(e))
            await asyncio.sleep(5)
