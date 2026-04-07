from __future__ import annotations
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.decision_engine.models import OpportunityCategory, OpportunityStatus
from app.domains.decision_engine.schemas import (
    OpportunityCreate,
    OpportunityOut,
    OpportunityStatusUpdate,
    OpportunitySummary,
)
from app.domains.decision_engine.service import DecisionEngineService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=Page[OpportunityOut])
async def list_opportunities(
    status: Optional[OpportunityStatus] = None,
    category: Optional[OpportunityCategory] = None,
    owner_team: Optional[str] = None,
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    service = DecisionEngineService(db)
    opps, total = await service.list_opportunities(
        current_user.org_id,
        status=status,
        category=category,
        owner_team=owner_team,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([OpportunityOut.model_validate(o) for o in opps], total, page_params)


@router.get("/summary", response_model=OpportunitySummary)
async def get_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = DecisionEngineService(db)
    return await service.get_summary(current_user.org_id)


@router.post("", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    req: OpportunityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER, UserRole.FINOPS)),
):
    service = DecisionEngineService(db)
    op = await service.create_opportunity(current_user.org_id, req)
    return OpportunityOut.model_validate(op)


@router.get("/{opp_id}", response_model=OpportunityOut)
async def get_opportunity(
    opp_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = DecisionEngineService(db)
    op = await service.get_opportunity(current_user.org_id, opp_id)
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return OpportunityOut.model_validate(op)


@router.patch("/{opp_id}/status", response_model=OpportunityOut)
async def update_status(
    opp_id: UUID,
    req: OpportunityStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = DecisionEngineService(db)
    op = await service.update_status(current_user.org_id, opp_id, req)
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return OpportunityOut.model_validate(op)


@router.post("/generate/{account_id}", response_model=List[OpportunityOut])
async def generate_opportunities(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = DecisionEngineService(db)
    opps = await service.generate_opportunities_for_account(current_user.org_id, account_id)
    return [OpportunityOut.model_validate(o) for o in opps]
