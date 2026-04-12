from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.redis import get_redis_pool
from app.domains.auth.models import UserRole
from app.domains.economics.models import ReportExportStatus
from app.domains.economics.schemas import (
    ReportExportCreate,
    ReportExportJobOut,
    WorkspaceBudgetOut,
    WorkspaceBudgetUpsert,
)
from app.domains.economics.service import EconomicsService
from app.workers.export_worker import QUEUE_KEY as REPORT_EXPORT_QUEUE_KEY

router = APIRouter(prefix="/economics", tags=["economics"])


@router.get(
    "/budget",
    response_model=WorkspaceBudgetOut,
    summary="Get workspace budget with live consumption metrics",
    responses={404: {"description": "No budget configured for this workspace"}},
)
async def get_budget(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> WorkspaceBudgetOut:
    """Return the WorkspaceBudget for the authenticated user's workspace.

    Enriches the stored configuration with live consumption data from
    ClickHouse: **consumed_usd**, **consumed_pct**, and a linear
    **projected_eom_usd** (end-of-period projection).
    """
    svc = EconomicsService(db)
    budget = await svc.get_budget_with_consumption(current_user.org_id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No budget configured for this workspace. Use PUT /economics/budget to create one.",
        )
    return budget


@router.put(
    "/budget",
    response_model=WorkspaceBudgetOut,
    summary="Create or update workspace budget",
    status_code=status.HTTP_200_OK,
)
async def upsert_budget(
    req: WorkspaceBudgetUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(
        require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN, UserRole.FINOPS)
    ),
) -> WorkspaceBudgetOut:
    """Create or replace the workspace budget configuration.

    Only **admin**, **platform_admin**, and **finops** roles may call this endpoint.
    The operation is idempotent — a second PUT with identical data is a no-op.
    """
    svc = EconomicsService(db)
    return await svc.upsert_budget(current_user.org_id, req)


@router.post(
    "/reports/export",
    response_model=ReportExportJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create an asynchronous economics export job",
)
async def create_report_export(
    req: ReportExportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ReportExportJobOut:
    svc = EconomicsService(db)
    job = await svc.create_report_export_job(
        current_user.org_id,
        current_user.id,
        req,
    )
    await db.commit()
    try:
        await get_redis_pool().lpush(
            REPORT_EXPORT_QUEUE_KEY,
            json.dumps({"org_id": current_user.org_id, "job_id": job.id}, default=str),
        )
    except Exception as exc:
        job_row = await svc.get_report_export_job(current_user.org_id, job.id)
        if job_row is not None:
            await svc.mark_report_export_failed(job_row, f"Could not enqueue export job: {exc}")
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not enqueue export job",
        ) from exc
    return job


@router.get(
    "/reports/export/{job_id}",
    response_model=ReportExportJobOut,
    summary="Get economics export job status",
    responses={404: {"description": "Export job not found"}},
)
async def get_report_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ReportExportJobOut:
    svc = EconomicsService(db)
    job = await svc.get_report_export_job(current_user.org_id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
    return EconomicsService.serialize_report_export_job(job)


@router.get(
    "/reports/export/{job_id}/download",
    summary="Download a completed economics export",
    responses={404: {"description": "Export job not found"}, 409: {"description": "Export job not ready"}},
)
async def download_report_export(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = EconomicsService(db)
    job = await svc.get_report_export_job(current_user.org_id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
    if job.status != ReportExportStatus.COMPLETED or not job.storage_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export job is not ready for download")
    if job.expires_at and job.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Export job has expired")

    file_path = Path(job.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export artifact not found")

    return FileResponse(
        path=file_path,
        media_type=job.content_type or "application/octet-stream",
        filename=job.file_name or file_path.name,
    )
