from __future__ import annotations

import asyncio
import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.core.observability import observe_worker_job
from app.core.redis import get_redis_pool
from app.domains.economics.export_runtime import build_report_export_artifact, persist_report_export_file
from app.domains.economics.models import ReportExportStatus
from app.domains.economics.service import EconomicsService
from app.workers.job_runtime import push_to_dlq, retry_key

log = get_logger(__name__)

QUEUE_KEY = "economics:reports:queue"
LOCK_TTL = 3600
STUCK_JOB_TIMEOUT_MINUTES = 10  # Jobs em running por mais de 10min são considerados órfãos
EXPORT_TIMEOUT_SECONDS = 300  # 5 minutos de timeout para geração de export


async def _cleanup_stuck_jobs() -> int:
    """Reset jobs órfãos em 'running' que estão lá há mais de STUCK_JOB_TIMEOUT_MINUTES."""
    try:
        async with async_session_factory() as db:
            stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_JOB_TIMEOUT_MINUTES)

            # Buscar jobs órfãos
            from sqlalchemy import select, update
            from app.domains.economics.models import ReportExportJob

            result = await db.execute(
                select(ReportExportJob).where(
                    ReportExportJob.status == ReportExportStatus.RUNNING,
                    ReportExportJob.started_at < stuck_cutoff,
                )
            )
            stuck_jobs = result.scalars().all()

            if stuck_jobs:
                job_ids = [str(j.id) for j in stuck_jobs]
                log.warning(
                    "economics.report_export.cleanup_stuck_jobs",
                    count=len(stuck_jobs),
                    job_ids=job_ids,
                )

                # Reset para queued
                await db.execute(
                    update(ReportExportJob)
                    .where(ReportExportJob.id.in_([j.id for j in stuck_jobs]))
                    .values(
                        status=ReportExportStatus.QUEUED,
                        started_at=None,
                        error_message="Job was stuck in running, auto-reset by worker cleanup",
                    )
                )
                await db.commit()
                return len(stuck_jobs)
            return 0
    except Exception as exc:
        log.error("economics.report_export.cleanup_stuck_jobs.error", error=str(exc))
        return 0


def _parse_payload(raw_payload: str) -> tuple[UUID, UUID]:
    data = json.loads(raw_payload)
    return UUID(data["org_id"]), UUID(data["job_id"])


async def process_report_export(raw_payload: str) -> None:
    started = time.perf_counter()
    status = "unknown"
    org_id, job_id = _parse_payload(raw_payload)
    redis = get_redis_pool()
    lock_key = f"economics:reports:lock:{job_id}"
    job_id_str = str(job_id)

    log.info(
        "economics.report_export.started",
        export_job_id=job_id_str,
        org_id=str(org_id),
        queue=QUEUE_KEY,
    )

    acquired = await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True)
    if not acquired:
        status = "locked"
        log.warning("economics.report_export.locked", export_job_id=job_id_str)
        observe_worker_job("economics_export", status, (time.perf_counter() - started) * 1000)
        return

    try:
        # === FASE 1: Setup e busca do job ===
        log.info("economics.report_export.phase.setup", export_job_id=job_id_str, phase=1)
        async with async_session_factory() as db:
            svc = EconomicsService(db)
            job = await svc.get_report_export_job(org_id, job_id)
            if job is None:
                status = "job_not_found"
                log.warning(
                    "economics.report_export.job_not_found",
                    export_job_id=job_id_str,
                    org_id=str(org_id),
                )
                await redis.delete(retry_key(QUEUE_KEY, raw_payload))
                return

            file_format = job.file_format.value
            log.info(
                "economics.report_export.job_found",
                export_job_id=job_id_str,
                file_format=file_format,
                report_type=job.report_type.value,
                window_days=job.window_days,
            )

            # === FASE 2: Marcar como running ===
            log.info("economics.report_export.phase.mark_running", export_job_id=job_id_str, phase=2)
            await svc.mark_report_export_running(job)
            await db.commit()
            log.info("economics.report_export.marked_running", export_job_id=job_id_str)

            # === FASE 3: Construir artifact ===
            log.info(
                "economics.report_export.phase.build_artifact",
                export_job_id=job_id_str,
                phase=3,
                file_format=file_format,
            )
            artifact = await build_report_export_artifact(db, job)
            log.info(
                "economics.report_export.artifact_built",
                export_job_id=job_id_str,
                file_format=file_format,
                content_size=len(artifact.content),
                file_name=artifact.file_name,
            )

            # === FASE 4: Salvar arquivo ===
            log.info(
                "economics.report_export.phase.save_file",
                export_job_id=job_id_str,
                phase=4,
            )
            storage_path = persist_report_export_file(job_id_str, job.file_format, artifact.content)
            log.info(
                "economics.report_export.file_saved",
                export_job_id=job_id_str,
                storage_path=str(storage_path),
            )

            # === FASE 5: Marcar como completed ===
            expires_at = datetime.now(timezone.utc) + timedelta(hours=get_settings().report_export_retention_hours)
            log.info(
                "economics.report_export.phase.mark_completed",
                export_job_id=job_id_str,
                phase=5,
            )
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
            elapsed_ms = (time.perf_counter() - started) * 1000
            log.info(
                "economics.report_export.completed",
                export_job_id=job_id_str,
                org_id=str(org_id),
                file_format=file_format,
                elapsed_ms=elapsed_ms,
            )
            observe_worker_job("economics_export", status, elapsed_ms)
            return

    except asyncio.CancelledError:
        # Worker shutdown - não marcar como failed, apenas liberar lock
        status = "cancelled"
        log.warning("economics.report_export.cancelled", export_job_id=job_id_str)
        await redis.delete(lock_key)
        observe_worker_job("economics_export", status, (time.perf_counter() - started) * 1000)
        raise

    except Exception as exc:
        tb_str = traceback.format_exc()
        elapsed_ms = (time.perf_counter() - started) * 1000

        # Log detalhado da exceção
        log.error(
            "economics.report_export.failed",
            export_job_id=job_id_str,
            org_id=str(org_id),
            error_type=type(exc).__name__,
            error_message=str(exc),
            elapsed_ms=elapsed_ms,
            traceback=tb_str,
        )

        # Marcar como failed IMEDIATAMENTE - não fazer retry automático
        # O usuário pode criar um novo job se quiser tentar novamente
        try:
            async with async_session_factory() as db:
                svc = EconomicsService(db)
                job = await svc.get_report_export_job(org_id, job_id)
                if job is not None:
                    # Truncar mensagem de erro para caber no campo
                    error_msg = f"{type(exc).__name__}: {exc}"[:2000]
                    await svc.mark_report_export_failed(job, error_msg)
                    await db.commit()
                    log.info(
                        "economics.report_export.marked_failed",
                        export_job_id=job_id_str,
                        error_message=error_msg[:200],
                    )

                # Não enfileirar para retry - isso só causa jobs travados
                # Apenas registrar no DLQ para análise
                await push_to_dlq(
                    db,
                    queue_name=QUEUE_KEY,
                    payload=raw_payload,
                    org_id=org_id,
                    account_id=None,
                    error_message=str(exc)[:2000],
                    retry_count=0,
                )
                await db.commit()
        except Exception as db_exc:
            log.error(
                "economics.report_export.failed_to_mark",
                export_job_id=job_id_str,
                error=str(db_exc),
            )

        await redis.delete(retry_key(QUEUE_KEY, raw_payload))
        status = "failed"
        observe_worker_job("economics_export", status, elapsed_ms)

    finally:
        await redis.delete(lock_key)
        if status == "unknown":
            status = "error"
            observe_worker_job("economics_export", status, (time.perf_counter() - started) * 1000)


async def run_export_worker() -> None:
    redis = get_redis_pool()
    log.info("economics_export_worker.started")
    cleanup_counter = 0

    while True:
        try:
            # Limpar jobs órfãos a cada 10 iterações (~50 segundos)
            cleanup_counter += 1
            if cleanup_counter >= 10:
                cleaned = await _cleanup_stuck_jobs()
                if cleaned > 0:
                    log.info("economics.report_export.cleanup_completed", count=cleaned)
                cleanup_counter = 0

            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw_payload = item
                await process_report_export(raw_payload)
        except Exception as exc:
            log.error("economics_export_worker.error", error=str(exc))
            await asyncio.sleep(5)