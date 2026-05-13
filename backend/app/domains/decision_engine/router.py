from __future__ import annotations
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.decision_engine.explanation_service import OpportunityExplanationService
from app.domains.decision_engine.models import OpportunityCategory, OpportunityStatus
from app.domains.decision_engine.savings_evidence_builder import build_savings_evidence
from app.domains.decision_engine.resource_context_builder import build_resource_context
from app.domains.decision_engine.performance_context_builder import build_performance_context
from app.domains.decision_engine.csv_export_service import generate_csv_content
from app.domains.decision_engine.schemas import (
    OpportunityCreate,
    OpportunityOut,
    OpportunityStatusUpdate,
    OpportunitySummary,
)
from app.domains.decision_engine.service import DecisionEngineService
from app.domains.intel.schemas import ExplainRecommendationOut

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _enrich_opportunity(opp_out: OpportunityOut, opp_model) -> OpportunityOut:
    """Attach computed savings_evidence, resource_context, and performance_context."""
    evidence = build_savings_evidence(opp_model)
    if evidence is not None:
        opp_out.savings_evidence = evidence
    context = build_resource_context(opp_model)
    if context is not None:
        opp_out.resource_context = context
    perf = build_performance_context(opp_model)
    if perf is not None:
        opp_out.performance_context = perf
    return opp_out


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
    items = [_enrich_opportunity(OpportunityOut.model_validate(o), o) for o in opps]
    return Page.of(items, total, page_params)


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
    return _enrich_opportunity(OpportunityOut.model_validate(op), op)


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
    return _enrich_opportunity(OpportunityOut.model_validate(op), op)


@router.patch("/{opp_id}/status", response_model=OpportunityOut)
async def update_status(
    opp_id: UUID,
    req: OpportunityStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = DecisionEngineService(db)
    op = await service.update_status(
        current_user.org_id,
        opp_id,
        req,
        actor_user_id=current_user.id,
    )
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return _enrich_opportunity(OpportunityOut.model_validate(op), op)


@router.get("/{opp_id}/explain", response_model=ExplainRecommendationOut)
async def explain_opportunity(
    opp_id: UUID,
    language: str = Query(default="en"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    svc = OpportunityExplanationService(db)
    try:
        return await svc.explain_opportunity(
            org_id=current_user.org_id,
            opportunity_id=opp_id,
            language=language,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI feature not enabled for this workspace plan",
        )


@router.post("/generate/{account_id}", response_model=List[OpportunityOut])
async def generate_opportunities(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = DecisionEngineService(db)
    opps = await service.generate_opportunities_for_account(current_user.org_id, account_id)
    return [_enrich_opportunity(OpportunityOut.model_validate(o), o) for o in opps]


@router.get("/export/csv")
async def export_opportunities_csv(
    status_filter: Optional[OpportunityStatus] = Query(None, alias="status"),
    category: Optional[OpportunityCategory] = None,
    owner_team: Optional[str] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
):
    """Export opportunities as CSV. Tenant-isolated, auditable."""
    service = DecisionEngineService(db)
    opps, _ = await service.list_opportunities(
        current_user.org_id,
        status=status_filter,
        category=category,
        owner_team=owner_team,
        limit=5000,
        offset=0,
    )
    csv_content = generate_csv_content(opps)
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=opportunities_export.csv",
        },
    )
