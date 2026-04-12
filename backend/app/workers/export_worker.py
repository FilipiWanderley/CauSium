from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.email import EmailService
from app.core.logging import get_logger
from app.core.observability import observe_worker_job
from app.core.redis import get_redis_pool
from app.core.slack import SlackService
from app.domains.economics.export_runtime import build_report_export_artifact, persist_report_export_file
from app.domains.economics.service import EconomicsService
from app.workers.job_runtime import MAX_RETRIES, push_to_dlq, retry_key

log = get_logger(__name__)

QUEUE_KEY = "economics:reports:queue"
LOCK_TTL = 3600


def _parse_payload(raw_payload: str) -> tuple[UUID, UUID]:
    data = json.loads(raw_payload)
    return UUID(data["org_id"]), UUID(data["job_id"])


async def process_report_export(raw_payload: str) -> None:
    started = time.perf_counter()
    status = "unknown"
    org_id, job_id = _parse_payload(raw_payload)
    redis = get_redis_pool()
    lock_key = f"economics:reports:lock:{job_id}"

    acquired = await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True)
    if not acquired:
        status = "locked"
        log.info("economics.report_export.locked", export_job_id=str(job_id))
        observe_worker_job("economics_export", status, (time.perf_counter() - started) * 1000)
        return

    try:
        async with async_session_factory() as db:
            svc = EconomicsService(db)
            job = await svc.get_report_export_job(org_id, job_id)
            if job is None:
                status = "job_not_found"
                log.warning("economics.report_export.job_not_found", export_job_id=str(job_id), org_id=str(org_id))
                await redis.delete(retry_key(QUEUE_KEY, raw_payload))
                return

            await svc.mark_report_export_running(job)
            await db.commit()

            artifact = await build_report_export_artifact(db, job)
            storage_path = persist_report_export_file(str(job.id), job.file_format, artifact.content)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=get_settings().report_export_retention_hours)

            await svc.mark_report_export_completed(
                job,
                file_name=artifact.file_name,
                storage_path=str(storage_path),
                content_type=artifact.content_type,
                expires_at=expires_at,
            )
            await db.commit()
            await redis.delete(retry_key(QUEUE_KEY, raw_payload))
            status = "success"
            log.info("economics.report_export.completed", export_job_id=str(job_id), org_id=str(org_id))
    except Exception as exc:
        attempts = await redis.incr(retry_key(QUEUE_KEY, raw_payload))
        if attempts < MAX_RETRIES:
            await redis.lpush(QUEUE_KEY, raw_payload)
            status = "retry"
            log.error(
                "economics.report_export.retry_scheduled",
                export_job_id=str(job_id),
                attempts=attempts,
                max_retries=MAX_RETRIES,
                error=str(exc),
            )
            return

        async with async_session_factory() as db:
            svc = EconomicsService(db)
            job = await svc.get_report_export_job(org_id, job_id)
            if job is not None:
                await svc.mark_report_export_failed(job, str(exc))
            await push_to_dlq(
                db,
                queue_name=QUEUE_KEY,
                payload=raw_payload,
                org_id=org_id,
                account_id=None,
                error_message=str(exc),
                retry_count=attempts,
            )
            await db.commit()

            subject = "[StratoPulse][Critical] Economics export worker failure"
            body = (
                "A critical failure occurred while generating an economics export.\n\n"
                f"export_job_id: {job_id}\n"
                f"org_id: {org_id}\n"
                f"error: {exc}\n"
            )
            await EmailService().send_critical_alert(subject=subject, text_body=body)
            await SlackService(db).send_critical_alert(org_id=org_id, subject=subject, text_body=body)
        await redis.delete(retry_key(QUEUE_KEY, raw_payload))
        status = "failed"
        log.error("economics.report_export.failed_to_dlq", export_job_id=str(job_id), error=str(exc))
    finally:
        await redis.delete(lock_key)
        if status == "unknown":
            status = "error"
        observe_worker_job("economics_export", status, (time.perf_counter() - started) * 1000)


async def run_export_worker() -> None:
    redis = get_redis_pool()
    log.info("economics_export_worker.started")
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw_payload = item
                await process_report_export(raw_payload)
        except Exception as exc:
            log.error("economics_export_worker.error", error=str(exc))
            await asyncio.sleep(5)