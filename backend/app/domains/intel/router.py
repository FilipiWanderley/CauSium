from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import Page, PageParams
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.auth.models import UserRole
from app.core.dependencies import require_roles
from app.domains.intel.anomaly_detection_service import CostAnomalyDetectionService
from app.domains.intel.cost_explanation_service import CostExplanationService
from app.domains.intel.models import CostAnomaly, CostAnomalySeverity
from app.domains.intel.schemas import (
    CostAnomalyOut,
    DetectCostAnomaliesOut,
    DetectCostAnomaliesRequest,
    ExplainCostChangeOut,
    ExplainCostChangeRequest,
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

