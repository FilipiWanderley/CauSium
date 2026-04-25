from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import Page, PageParams
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.auth.models import UserRole
from app.core.dependencies import require_roles
from app.domains.intel.anomaly_detection_service import CostAnomalyDetectionService
from app.domains.intel.cost_explanation_service import CostExplanationService
from app.domains.intel.insights_service import IntelInsightsService
from app.domains.intel.models import CostAnomaly, CostAnomalySeverity
from app.domains.intel.schemas import (
    CreateExecutionPlanRequest,
    CostAnomalyOut,
    DetectCostAnomaliesOut,
    DetectCostAnomaliesRequest,
    ExecutionPlanExecutionStatusOut,
    ExecutionPlanListItemOut,
    ExecutionPlanHandoffIn,
    ExecutionPlanOut,
    ExecutionPlanScheduleIn,
    ExecutionPlanStatusUpdateIn,
    ExplainCostChangeOut,
    ExplainCostChangeRequest,
    IntelInsightsOut,
)
from app.domains.decision_engine.optimization_plan_service import OptimizationPlanService
from app.domains.decision_engine.schemas import OptimizationPlanOut
from app.domains.intel.execution_plan_service import (
    ExecutionPlanNotFoundError,
    ExecutionPlanService,
    InvalidExecutionPlanTransitionError,
)

router = APIRouter(prefix="/intel", tags=["intel"])


@router.post("/explain-cost", response_model=ExplainCostChangeOut)
async def explain_cost_change(
    req: ExplainCostChangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExplainCostChangeOut:
    if req.end_date < req.start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period")

    svc = CostExplanationService(db)
    try:
        return await svc.explain_cost_change(
            org_id=current_user.org_id,
            start_date=req.start_date,
            end_date=req.end_date,
            provider=req.provider.lower() if req.provider else None,
            language=req.language or "en",
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI feature not enabled for this workspace plan",
        )


def _to_cost_anomaly_out(item: CostAnomaly) -> CostAnomalyOut:
    return CostAnomalyOut(
        id=str(item.id),
        provider=item.provider,
        service=item.service,
        observed_date=item.observed_date,
        current_cost_usd=item.current_cost_usd,
        historical_mean_usd=item.historical_mean_usd,
        historical_stddev_usd=item.historical_stddev_usd,
        z_score=item.z_score,
        deviation_pct=item.deviation_pct,
        severity=item.severity.value,
        window_days=item.window_days,
        z_threshold=item.z_threshold,
        created_at=item.created_at.isoformat(),
    )


@router.post("/cost-anomalies/detect", response_model=DetectCostAnomaliesOut)
async def detect_cost_anomalies(
    req: DetectCostAnomaliesRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER, UserRole.PLATFORM_ADMIN)),
) -> DetectCostAnomaliesOut:
    svc = CostAnomalyDetectionService(db)
    result = await svc.detect_for_org(
        org_id=current_user.org_id,
        lookback_days=req.lookback_days,
        z_threshold=req.z_threshold,
        min_history_days=req.min_history_days,
        min_delta_usd=req.min_delta_usd,
    )
    return DetectCostAnomaliesOut(
        observed_date=result.observed_date,
        scanned_services=result.scanned_services,
        detected=result.detected,
        created=result.created,
        anomalies=[_to_cost_anomaly_out(item) for item in result.anomalies],
    )


@router.get("/cost-anomalies", response_model=Page[CostAnomalyOut])
async def list_cost_anomalies(
    provider: str | None = Query(default=None),
    service: str | None = Query(default=None),
    severity: CostAnomalySeverity | None = Query(default=None),
    observed_from: date | None = Query(default=None),
    observed_to: date | None = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> Page[CostAnomalyOut]:
    svc = CostAnomalyDetectionService(db)
    items, total = await svc.list_anomalies(
        org_id=current_user.org_id,
        provider=provider,
        service=service,
        severity=severity,
        observed_from=observed_from,
        observed_to=observed_to,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([_to_cost_anomaly_out(item) for item in items], total, page_params)


@router.get("/insights", response_model=IntelInsightsOut)
async def get_intel_insights(
    language: str = Query(default="en"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> IntelInsightsOut:
    svc = IntelInsightsService(db)
    try:
        return await svc.get_insights(org_id=current_user.org_id, language=language)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI feature not enabled for this workspace plan",
        )


@router.get("/optimization-plan", response_model=OptimizationPlanOut)
async def get_optimization_plan(
    language: str = Query(default="pt"),
    include_ai_summary: bool = Query(default=False),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> OptimizationPlanOut:
    svc = OptimizationPlanService(db)
    return await svc.build_plan(
        org_id=current_user.org_id,
        language=(language or "pt").lower(),
        include_ai_summary=include_ai_summary,
    )


@router.post("/execution-plan", response_model=ExecutionPlanOut)
async def create_execution_plan(
    req: CreateExecutionPlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanOut:
    svc = ExecutionPlanService(db)
    try:
        return await svc.prepare_plan(
            org_id=current_user.org_id,
            req=req,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/execution-plan", response_model=Page[ExecutionPlanListItemOut])
async def list_execution_plans(
    status_filter: str | None = Query(default=None, alias="status"),
    risk_level: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> Page[ExecutionPlanListItemOut]:
    if created_from and created_to and created_to < created_from:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period")
    svc = ExecutionPlanService(db)
    items, total = await svc.list_plans(
        org_id=current_user.org_id,
        status=status_filter,
        risk_level=risk_level,
        created_from=created_from,
        created_to=created_to,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of(items, total, page_params)


@router.get("/execution-plan/{execution_plan_id}", response_model=ExecutionPlanOut)
async def get_execution_plan(
    execution_plan_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanOut:
    svc = ExecutionPlanService(db)
    plan = await svc.get_plan(org_id=current_user.org_id, execution_plan_id=execution_plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution plan not found")
    return plan


@router.patch("/execution-plan/{execution_plan_id}/status", response_model=ExecutionPlanOut)
async def update_execution_plan_status(
    execution_plan_id: UUID,
    req: ExecutionPlanStatusUpdateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanOut:
    svc = ExecutionPlanService(db)
    try:
        return await svc.update_plan_status(
            org_id=current_user.org_id,
            execution_plan_id=execution_plan_id,
            new_status=req.status,
            actor_user_id=current_user.id,
            comment=req.comment,
        )
    except ExecutionPlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidExecutionPlanTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.patch("/execution-plan/{execution_plan_id}/schedule", response_model=ExecutionPlanOut)
async def schedule_execution_plan(
    execution_plan_id: UUID,
    req: ExecutionPlanScheduleIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanOut:
    svc = ExecutionPlanService(db)
    try:
        return await svc.schedule_plan(
            org_id=current_user.org_id,
            execution_plan_id=execution_plan_id,
            actor_user_id=current_user.id,
            scheduled_for=req.scheduled_for,
            maintenance_window=req.maintenance_window,
            comment=req.comment,
        )
    except ExecutionPlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidExecutionPlanTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/execution-plan/{execution_plan_id}/handoff", response_model=ExecutionPlanOut)
async def create_execution_plan_handoff(
    execution_plan_id: UUID,
    req: ExecutionPlanHandoffIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanOut:
    svc = ExecutionPlanService(db)
    try:
        return await svc.create_pulselab_handoff(
            org_id=current_user.org_id,
            execution_plan_id=execution_plan_id,
            actor_user_id=current_user.id,
            target_environment=req.target_environment,
            target_criticality=req.target_criticality,
            comment=req.comment,
        )
    except ExecutionPlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidExecutionPlanTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/execution-plan/{execution_plan_id}/execution-status", response_model=ExecutionPlanExecutionStatusOut)
async def get_execution_plan_execution_status(
    execution_plan_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ExecutionPlanExecutionStatusOut:
    svc = ExecutionPlanService(db)
    try:
        return await svc.get_execution_status(
            org_id=current_user.org_id,
            execution_plan_id=execution_plan_id,
            actor_user_id=current_user.id,
        )
    except ExecutionPlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidExecutionPlanTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
