from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_platform_admin
from app.core.observability import build_sli_slo_snapshot
from app.core.schemas import Page, PageParams
from app.domains.admin.schemas import (
    AdminForceLifecycle,
    AdminOrgListItem,
    AdminUserItem,
    DlqMessageOut,
    DlqRequeueResponse,
    SeedPlatformAdminIn,
    SeedPlatformAdminOut,
    SupportAccessCreateIn,
    SupportAccessEndIn,
    SupportAccessSessionOut,
    SloOverviewOut,
)
from app.domains.auth.models import WorkspaceLifecycleState
from app.domains.admin.service import PlatformAdminService
from app.domains.workspaces.schemas import WorkspaceOut

router = APIRouter(prefix="/admin", tags=["platform-admin"])


@router.post("/seed-platform-admin", response_model=SeedPlatformAdminOut, status_code=200, include_in_schema=False)
async def seed_platform_admin(
    req: SeedPlatformAdminIn,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SeedPlatformAdminOut:
    """Promote an email to PLATFORM_ADMIN. Protected by X-Internal-Key."""
    import os
    from fastapi import HTTPException
    expected = os.getenv("INTERNAL_MONITORING_KEY", "").strip()
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = PlatformAdminService(db, actor_user_id=None)  # type: ignore[arg-type]
    created, promoted = await service.seed_platform_admin(req.email, req.full_name)
    await db.commit()
    return SeedPlatformAdminOut(email=req.email, created=created, promoted=promoted)


@router.get("/orgs", response_model=Page[AdminOrgListItem])
async def list_all_orgs(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    lifecycle_state: WorkspaceLifecycleState | None = Query(default=None),
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[AdminOrgListItem]:
    """List every organization on the platform (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_orgs(params, q=q, lifecycle_state=lifecycle_state)
    return Page.of(items, total, params)


@router.get("/orgs/{org_id}", response_model=WorkspaceOut)
async def get_org_detail(
    org_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Get full details of any organization (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.get_org(org_id)
    return WorkspaceOut.model_validate(org)


@router.get("/orgs/{org_id}/users", response_model=Page[AdminUserItem])
async def list_org_users(
    org_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[AdminUserItem]:
    """List users of any organization (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_org_users(org_id, params)
    return Page.of(items, total, params)


@router.post("/orgs/{org_id}/suspend", response_model=WorkspaceOut)
async def force_suspend_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Force-suspend any workspace (PLATFORM_ADMIN only). Audited."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_suspend(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.post("/orgs/{org_id}/restore", response_model=WorkspaceOut)
async def force_restore_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Force-restore a suspended workspace (PLATFORM_ADMIN only). Audited."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_restore(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.post("/orgs/{org_id}/archive", response_model=WorkspaceOut)
async def force_archive_org(
    org_id: UUID,
    req: AdminForceLifecycle,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> WorkspaceOut:
    """Permanently archive any workspace (PLATFORM_ADMIN only). Audited. Irreversible."""
    service = PlatformAdminService(db, current_user.id)
    org = await service.force_archive(org_id, req.reason)
    await db.commit()
    return WorkspaceOut.model_validate(org)


@router.get("/dlq", response_model=Page[DlqMessageOut])
async def list_dlq_messages(
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[DlqMessageOut]:
    """List DLQ messages to support operational triage and UI dashboards."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_dlq(params)
    return Page.of(items, total, params)


@router.post("/dlq/{dlq_id}/requeue", response_model=DlqRequeueResponse)
async def requeue_dlq_message(
    dlq_id: UUID,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> DlqRequeueResponse:
    """Requeue a DLQ message back to its original queue for reprocessing."""
    service = PlatformAdminService(db, current_user.id)
    msg = await service.requeue_dlq(dlq_id)
    await db.commit()
    return DlqRequeueResponse(dlq_id=msg.id, queue_name=msg.queue_name, requeued=True)


@router.get("/observability/slo", response_model=SloOverviewOut)
async def get_slo_overview(
    current_user=Depends(require_platform_admin),
) -> SloOverviewOut:
    _ = current_user
    snapshot = build_sli_slo_snapshot(error_budget_pct=1.0, api_p95_ms_target=500.0)
    return SloOverviewOut(**snapshot)


@router.post("/support-access", response_model=SupportAccessSessionOut, status_code=201)
async def create_support_access(
    req: SupportAccessCreateIn,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SupportAccessSessionOut:
    service = PlatformAdminService(db, current_user.id)
    session = await service.create_support_access_session(
        target_org_id=req.target_org_id,
        reason=req.reason,
        duration_minutes=req.duration_minutes,
    )
    await db.commit()
    return SupportAccessSessionOut.model_validate(session)


@router.get("/support-access/active", response_model=list[SupportAccessSessionOut])
async def list_active_support_access(
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> list[SupportAccessSessionOut]:
    service = PlatformAdminService(db, current_user.id)
    sessions = await service.list_active_support_access_sessions()
    await db.commit()
    return [SupportAccessSessionOut.model_validate(item) for item in sessions]


@router.post("/support-access/{session_id}/end", response_model=SupportAccessSessionOut)
async def end_support_access(
    session_id: UUID,
    req: SupportAccessEndIn,
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
) -> SupportAccessSessionOut:
    service = PlatformAdminService(db, current_user.id)
    session = await service.end_support_access_session(session_id, reason=req.reason)
    await db.commit()
    return SupportAccessSessionOut.model_validate(session)
