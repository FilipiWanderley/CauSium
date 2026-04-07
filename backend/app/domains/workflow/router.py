from __future__ import annotations
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.schemas import Page, PageParams
from app.domains.workflow.models import InitiativeStatus
from app.domains.workflow.schemas import (
    CommentCreate,
    CommentOut,
    InitiativeBoard,
    InitiativeCreate,
    InitiativeOut,
    InitiativeStatusTransition,
    InitiativeUpdate,
)
from app.domains.workflow.service import WorkflowService

router = APIRouter(prefix="/initiatives", tags=["workflow"])


@router.post("", response_model=InitiativeOut, status_code=status.HTTP_201_CREATED)
async def create_initiative(
    req: InitiativeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    initiative = await service.create_initiative(current_user.org_id, req, actor_user_id=current_user.id)
    return InitiativeOut.from_model(initiative)


@router.get("/board", response_model=InitiativeBoard)
async def get_board(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    return await service.get_board(current_user.org_id)


@router.get("", response_model=Page[InitiativeOut])
async def list_initiatives(
    status: Optional[InitiativeStatus] = None,
    owner_id: Optional[UUID] = None,
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    initiatives, total = await service.list_initiatives(
        current_user.org_id,
        status=status,
        owner_id=owner_id,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([InitiativeOut.from_model(i) for i in initiatives], total, page_params)


@router.get("/{initiative_id}", response_model=InitiativeOut)
async def get_initiative(
    initiative_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    initiative = await service.get_initiative(current_user.org_id, initiative_id)
    if not initiative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    return InitiativeOut.from_model(initiative)


@router.patch("/{initiative_id}", response_model=InitiativeOut)
async def update_initiative(
    initiative_id: UUID,
    req: InitiativeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    initiative = await service.update_initiative(current_user.org_id, initiative_id, req)
    if not initiative:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    return InitiativeOut.from_model(initiative)


@router.post("/{initiative_id}/transition", response_model=InitiativeOut)
async def transition_status(
    initiative_id: UUID,
    req: InitiativeStatusTransition,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    try:
        initiative = await service.transition_status(
            current_user.org_id, initiative_id, req, actor_user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return InitiativeOut.from_model(initiative)


@router.get("/{initiative_id}/comments", response_model=List[CommentOut])
async def list_comments(
    initiative_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    comments = await service.list_comments(current_user.org_id, initiative_id)
    return [CommentOut.model_validate(c) for c in comments]


@router.post("/{initiative_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(
    initiative_id: UUID,
    req: CommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = WorkflowService(db)
    try:
        comment = await service.add_comment(current_user.org_id, initiative_id, current_user.id, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CommentOut.model_validate(comment)
