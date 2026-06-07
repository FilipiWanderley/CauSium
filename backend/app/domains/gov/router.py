from __future__ import annotations

import re
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
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
    TagComplianceOut,
    TopUntaggedRow,
    UnownedCostRowOut,
)
from app.domains.gov.service import GovService

router = APIRouter(prefix="/gov", tags=["gov"])

# Tag key validation: alphanumeric, underscore, hyphen, max 64 chars
_TAG_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


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


# ── Tag Compliance (monitored tag) ─────────────────────────────────────────────

@router.get("/tag-compliance", response_model=TagComplianceOut)
def get_tag_compliance(
    tag_key: str = Query(default="team", description="Monitored tag key (alphanumeric, underscore, hyphen). Max 64 chars."),
    days: int = Query(default=30, ge=7, le=365),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> TagComplianceOut:
    # Validate tag_key: alphanumeric, underscore, hyphen, 1-64 chars
    if not _TAG_KEY_PATTERN.match(tag_key):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tag_key '{tag_key}'. Must be 1-64 chars, alphanumeric with underscore or hyphen only.",
        )
    svc = GovService()
    metrics = svc.get_tag_compliance(current_user.org_id, tag_key=tag_key, days=days)
    return TagComplianceOut(
        configured_tag_key=metrics.configured_tag_key,
        total_cost=metrics.total_cost,
        tagged_cost=metrics.tagged_cost,
        untagged_cost=metrics.untagged_cost,
        coverage_pct=metrics.coverage_pct,
        total_records=metrics.total_records,
        tagged_records=metrics.tagged_records,
        untagged_records=metrics.untagged_records,
        top_untagged_resource_groups=[TopUntaggedRow(**vars(r)) for r in metrics.top_untagged_resource_groups],
        top_untagged_services=[TopUntaggedRow(**vars(r)) for r in metrics.top_untagged_services],
    )


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
