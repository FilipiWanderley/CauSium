from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.intel.cost_explanation_service import CostExplanationService
from app.domains.intel.schemas import ExplainCostChangeOut, ExplainCostChangeRequest

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

