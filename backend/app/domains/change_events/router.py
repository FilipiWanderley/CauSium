from __future__ import annotations
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.schemas import Page, PageParams
from app.domains.change_events.models import ChangeEventType
from app.domains.change_events.schemas import ChangeEventCreate, ChangeEventOut
from app.domains.change_events.service import ChangeEventService

router = APIRouter(prefix="/change-events", tags=["change-events"])


@router.post("", response_model=ChangeEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    req: ChangeEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ChangeEventService(db)
    event = await svc.create(current_user.org_id, req)
    return ChangeEventOut.model_validate(event)


@router.get("", response_model=Page[ChangeEventOut])
async def list_events(
    event_type: Optional[ChangeEventType] = Query(default=None),
    environment: Optional[str] = Query(default=None),
    team: Optional[str] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = ChangeEventService(db)
    events, total = await svc.list(
        current_user.org_id,
        event_type=event_type,
        environment=environment,
        team=team,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([ChangeEventOut.model_validate(e) for e in events], total, page_params)


@router.get("/{event_id}", response_model=ChangeEventOut)
async def get_event(
    event_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = ChangeEventService(db)
    event = await svc.get(current_user.org_id, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return ChangeEventOut.model_validate(event)


@router.patch("/{event_id}/causal", response_model=ChangeEventOut)
async def link_causal(
    event_id: UUID,
    cost_impact_usd: float,
    confidence: float = Query(..., ge=0, le=1),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = ChangeEventService(db)
    event = await svc.link_causal(current_user.org_id, event_id, cost_impact_usd, confidence)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return ChangeEventOut.model_validate(event)
