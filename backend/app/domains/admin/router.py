from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_platform_admin
from app.core.schemas import Page, PageParams
from app.domains.admin.schemas import AdminForceLifecycle, AdminOrgListItem, AdminUserItem
from app.domains.admin.service import PlatformAdminService
from app.domains.workspaces.schemas import WorkspaceOut

router = APIRouter(prefix="/admin", tags=["platform-admin"])


@router.get("/orgs", response_model=Page[AdminOrgListItem])
async def list_all_orgs(
    current_user=Depends(require_platform_admin),
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    params: Annotated[PageParams, Depends(PageParams)] = ...,
) -> Page[AdminOrgListItem]:
    """List every organization on the platform (PLATFORM_ADMIN only)."""
    service = PlatformAdminService(db, current_user.id)
    items, total = await service.list_orgs(params)
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
