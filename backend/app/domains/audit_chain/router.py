from __future__ import annotations
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import SupportAccessContext, get_current_user, get_support_access_context
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.audit_chain.schemas import (
    AuditCheckpointCleanupOut,
    AuditCheckpointOut,
    AuditCheckpointVerificationOut,
    AuditEventOut,
    AuditVerificationOut,
)
from app.domains.audit_chain.service import AuditChainService

router = APIRouter(prefix="/audit-chain", tags=["audit-chain"])


def _resolve_scope_org_id(current_user, support_ctx: SupportAccessContext, org_id: UUID | None) -> UUID:
    """Resolve effective org scope for audit operations.

    - Regular users/admins are always scoped to their own workspace.
    - platform_admin may optionally provide ``org_id`` to inspect another workspace.
    """
    if org_id is None:
        return support_ctx.effective_org_id
    if current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform_admin can query audit scope for another workspace",
        )
    if (
        support_ctx.support_access_session_id is not None
        and org_id != support_ctx.effective_org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="org_id must match active support access target during support session.",
        )
    return org_id


@router.get("/events", response_model=Page[AuditEventOut])
async def list_audit_events(
    org_id: Optional[UUID] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    event_prefix: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    events, total = await svc.list_events(
        effective_org_id,
        event_type=event_type,
        event_prefix=event_prefix,
        entity_type=entity_type,
        created_after=created_after,
        created_before=created_before,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([AuditEventOut.model_validate(e) for e in events], total, page_params)


@router.get("/events/auth", response_model=Page[AuditEventOut])
async def list_auth_audit_events(
    org_id: Optional[UUID] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    events, total = await svc.list_events(
        effective_org_id,
        event_prefix="auth.",
        created_after=created_after,
        created_before=created_before,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([AuditEventOut.model_validate(e) for e in events], total, page_params)


@router.get("/events/export/jsonl")
async def export_audit_events_jsonl(
    org_id: Optional[UUID] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    event_prefix: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    content = await svc.export_events_jsonl(
        effective_org_id,
        event_type=event_type,
        event_prefix=event_prefix,
        entity_type=entity_type,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        offset=offset,
    )
    return Response(
        content=content,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="audit_events.ndjson"'},
    )


@router.get("/verify", response_model=AuditVerificationOut)
async def verify_audit_chain(
    org_id: Optional[UUID] = Query(default=None),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    return await svc.verify_chain(effective_org_id)


@router.post("/checkpoints", response_model=AuditCheckpointOut)
async def create_audit_checkpoint(
    org_id: Optional[UUID] = Query(default=None),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    checkpoint = await svc.create_checkpoint(effective_org_id, current_user.id)
    return AuditCheckpointOut.model_validate(checkpoint)


@router.get("/checkpoints", response_model=List[AuditCheckpointOut])
async def list_audit_checkpoints(
    org_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    checkpoints = await svc.list_checkpoints(effective_org_id, limit=limit, offset=offset)
    return [AuditCheckpointOut.model_validate(c) for c in checkpoints]


@router.get("/checkpoints/{checkpoint_id}/verify", response_model=AuditCheckpointVerificationOut)
async def verify_audit_checkpoint(
    checkpoint_id: UUID,
    org_id: Optional[UUID] = Query(default=None),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    return await svc.verify_checkpoint(effective_org_id, checkpoint_id)


@router.delete("/checkpoints/retention", response_model=AuditCheckpointCleanupOut)
async def cleanup_audit_checkpoints(
    org_id: Optional[UUID] = Query(default=None),
    keep_last: int = Query(default=200, ge=1, le=5000),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
    support_ctx: SupportAccessContext = Depends(get_support_access_context),
):
    effective_org_id = _resolve_scope_org_id(current_user, support_ctx, org_id)
    svc = AuditChainService(db)
    deleted, kept = await svc.cleanup_checkpoints(effective_org_id, keep_last=keep_last)
    await db.commit()
    return AuditCheckpointCleanupOut(org_id=effective_org_id, deleted_count=deleted, kept_count=kept)
