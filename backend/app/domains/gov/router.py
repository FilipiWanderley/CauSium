from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.gov.schemas import (
    GovSummaryOut,
    LabelComplianceRowOut,
    UnownedCostRowOut,
)
from app.domains.gov.service import GovService

router = APIRouter(prefix="/gov", tags=["gov"])


@router.get("/summary", response_model=GovSummaryOut)
def get_summary(
    days: int = Query(default=30, ge=7, le=365),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> GovSummaryOut:
    svc = GovService()
    summary = svc.get_summary(current_user.org_id, days=days)
    return GovSummaryOut(
        total_resources=summary.total_resources,
        unowned_resources=summary.unowned_resources,
        unowned_cost_usd=summary.unowned_cost_usd,
        unowned_pct=summary.unowned_pct,
        teams_evaluated=summary.teams_evaluated,
        avg_compliance_pct=summary.avg_compliance_pct,
    )


@router.get("/unowned-costs", response_model=List[UnownedCostRowOut])
def get_unowned_costs(
    days: int = Query(default=30, ge=7, le=365),
    limit: int = Query(default=50, ge=1, le=200),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[UnownedCostRowOut]:
    svc = GovService()
    rows = svc.get_unowned_costs(current_user.org_id, days=days, limit=limit)
    return [UnownedCostRowOut(**vars(r)) for r in rows]


@router.get("/label-compliance", response_model=List[LabelComplianceRowOut])
def get_label_compliance(
    days: int = Query(default=30, ge=7, le=365),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[LabelComplianceRowOut]:
    svc = GovService()
    rows = svc.get_label_compliance(current_user.org_id, days=days)
    return [LabelComplianceRowOut(**vars(r)) for r in rows]
