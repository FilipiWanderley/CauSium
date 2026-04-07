from __future__ import annotations
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.schemas import Page, PageParams
from app.domains.audit_chain.schemas import (
    AuditCheckpointCleanupOut,
    AuditCheckpointOut,
    AuditCheckpointVerificationOut,
    AuditEventOut,
    AuditVerificationOut,
)
from app.domains.audit_chain.service import AuditChainService

router = APIRouter(prefix="/audit-chain", tags=["audit-chain"])


@router.get("/events", response_model=Page[AuditEventOut])
async def list_audit_events(
    event_type: Optional[str] = Query(default=None),
    event_prefix: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    events, total = await svc.list_events(
        current_user.org_id,
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
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    events, total = await svc.list_events(
        current_user.org_id,
        event_prefix="auth.",
        created_after=created_after,
        created_before=created_before,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([AuditEventOut.model_validate(e) for e in events], total, page_params)


@router.get("/events/export/jsonl")
async def export_audit_events_jsonl(
    event_type: Optional[str] = Query(default=None),
    event_prefix: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    content = await svc.export_events_jsonl(
        current_user.org_id,
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    return await svc.verify_chain(current_user.org_id)


@router.post("/checkpoints", response_model=AuditCheckpointOut)
async def create_audit_checkpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    checkpoint = await svc.create_checkpoint(current_user.org_id, current_user.id)
    return AuditCheckpointOut.model_validate(checkpoint)


@router.get("/checkpoints", response_model=List[AuditCheckpointOut])
async def list_audit_checkpoints(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    checkpoints = await svc.list_checkpoints(current_user.org_id, limit=limit, offset=offset)
    return [AuditCheckpointOut.model_validate(c) for c in checkpoints]


@router.get("/checkpoints/{checkpoint_id}/verify", response_model=AuditCheckpointVerificationOut)
async def verify_audit_checkpoint(
    checkpoint_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    return await svc.verify_checkpoint(current_user.org_id, checkpoint_id)


@router.delete("/checkpoints/retention", response_model=AuditCheckpointCleanupOut)
async def cleanup_audit_checkpoints(
    keep_last: int = Query(default=200, ge=1, le=5000),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = AuditChainService(db)
    deleted, kept = await svc.cleanup_checkpoints(current_user.org_id, keep_last=keep_last)
    await db.commit()
    return AuditCheckpointCleanupOut(org_id=current_user.org_id, deleted_count=deleted, kept_count=kept)
