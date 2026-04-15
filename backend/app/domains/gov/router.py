from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.gov.schemas import (
    GovSummaryOut,
    InventorySummaryOut,
    LabelComplianceRowOut,
    RecommendationRowOut,
    RecommendationsSummaryOut,
    ResourceRowOut,
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
    return GovSummaryOut(**vars(summary))


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


# ── Recommendations ────────────────────────────────────────────────────────────

@router.get("/recommendations/summary", response_model=RecommendationsSummaryOut)
def get_recommendations_summary(
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> RecommendationsSummaryOut:
    svc = GovService()
    s = svc.get_recommendations_summary(current_user.org_id)
    return RecommendationsSummaryOut(**vars(s))


@router.get("/recommendations", response_model=List[RecommendationRowOut])
def get_recommendations(
    category: str | None = Query(default=None),
    impact: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[RecommendationRowOut]:
    svc = GovService()
    rows = svc.get_recommendations(
        current_user.org_id, category=category, impact=impact, limit=limit
    )
    return [RecommendationRowOut(**vars(r)) for r in rows]


# ── Inventory ──────────────────────────────────────────────────────────────────

@router.get("/inventory/summary", response_model=InventorySummaryOut)
def get_inventory_summary(
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> InventorySummaryOut:
    svc = GovService()
    s = svc.get_inventory_summary(current_user.org_id)
    return InventorySummaryOut(**vars(s))


@router.get("/inventory", response_model=List[ResourceRowOut])
def get_inventory(
    resource_type: str | None = Query(default=None),
    owner_team: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> List[ResourceRowOut]:
    svc = GovService()
    rows, _total = svc.get_inventory(
        current_user.org_id,
        resource_type=resource_type,
        owner_team=owner_team,
        environment=environment,
        limit=limit,
        offset=offset,
    )
    return [ResourceRowOut(**vars(r)) for r in rows]
