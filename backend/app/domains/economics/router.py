from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.domains.auth.models import UserRole
from app.domains.economics.schemas import WorkspaceBudgetOut, WorkspaceBudgetUpsert
from app.domains.economics.service import EconomicsService

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
