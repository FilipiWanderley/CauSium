from __future__ import annotations
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.schemas import Page, PageParams
from app.domains.risk_budgets.schemas import RiskBudgetCreate, RiskBudgetOut, RiskBudgetUpdate
from app.domains.risk_budgets.service import RiskBudgetService

router = APIRouter(prefix="/risk-budgets", tags=["risk-budgets"])


@router.post("", response_model=RiskBudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
    req: RiskBudgetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = RiskBudgetService(db)
    budget = await svc.create(current_user.org_id, req, actor_user_id=current_user.id)
    return RiskBudgetOut.model_validate(budget)


@router.get("", response_model=Page[RiskBudgetOut])
async def list_budgets(
    active_only: bool = Query(default=False),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = RiskBudgetService(db)
    budgets, total = await svc.list(
        current_user.org_id,
        active_only=active_only,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([RiskBudgetOut.model_validate(b) for b in budgets], total, page_params)


@router.get("/{budget_id}", response_model=RiskBudgetOut)
async def get_budget(
    budget_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = RiskBudgetService(db)
    budget = await svc.get(current_user.org_id, budget_id)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk budget not found")
    return RiskBudgetOut.model_validate(budget)


@router.patch("/{budget_id}", response_model=RiskBudgetOut)
async def update_budget(
    budget_id: UUID,
    req: RiskBudgetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = RiskBudgetService(db)
    budget = await svc.update(current_user.org_id, budget_id, req, actor_user_id=current_user.id)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk budget not found")
    return RiskBudgetOut.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    svc = RiskBudgetService(db)
    deleted = await svc.delete(current_user.org_id, budget_id, actor_user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk budget not found")
