from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.executive.schemas import ExecutiveSummary, ScorecardResponse
from app.domains.executive.service import ExecutiveService

router = APIRouter(prefix="/executive", tags=["executive"])


@router.get("/summary", response_model=ExecutiveSummary)
async def get_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = ExecutiveService(db)
    return await service.get_summary(current_user.org_id)


@router.get("/scorecard", response_model=ScorecardResponse)
async def get_scorecard(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = ExecutiveService(db)
    return await service.get_scorecard(current_user.org_id)
