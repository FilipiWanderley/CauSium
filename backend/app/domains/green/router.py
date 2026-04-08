from __future__ import annotations

from typing import Annotated, List, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.green.schemas import (
    EmissionsBreakdownRowOut,
    EmissionsMonthRowOut,
    GreenSummaryOut,
)
from app.domains.green.service import GreenService

router = APIRouter(prefix="/green", tags=["green"])


@router.get("/summary", response_model=GreenSummaryOut)
def get_summary(
    months: int = Query(default=6, ge=1, le=24),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> GreenSummaryOut:
    svc = GreenService()
    s = svc.get_summary(current_user.org_id, months=months)
    return GreenSummaryOut(
        total_kg_co2e=s.total_kg_co2e,
        total_cost_usd=s.total_cost_usd,
        intensity_avg=s.intensity_avg,
        mom_delta_pct=s.mom_delta_pct,
        months_available=s.months_available,
        note=s.note,
    )


@router.get("/emissions", response_model=List[EmissionsMonthRowOut])
def get_emissions(
    months: int = Query(default=12, ge=1, le=24),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[EmissionsMonthRowOut]:
    svc = GreenService()
    rows = svc.get_emissions_monthly(current_user.org_id, months=months)
    return [EmissionsMonthRowOut(**vars(r)) for r in rows]


@router.get("/breakdown", response_model=List[EmissionsBreakdownRowOut])
def get_breakdown(
    by: Literal["service", "region", "environment", "owner_team"] = Query(default="service"),
    days: int = Query(default=30, ge=7, le=365),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[EmissionsBreakdownRowOut]:
    svc = GreenService()
    rows = svc.get_breakdown(current_user.org_id, by=by, days=days)
    return [EmissionsBreakdownRowOut(**vars(r)) for r in rows]
