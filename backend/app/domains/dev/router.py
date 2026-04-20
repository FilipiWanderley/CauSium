from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.dev.schemas import ClearResult, SeedRequest, SeedResult, SeedStatus
from app.domains.dev.service import DevSeedService

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get(
    "/seed/status",
    response_model=SeedStatus,
    summary="Check how many rows are in ClickHouse for the authenticated tenant",
    description="Returns row counts per table. Use this to diagnose empty dashboards.",
)
async def get_seed_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> SeedStatus:
    return await DevSeedService(db).status(current_user.org_id)


@router.post(
    "/seed",
    response_model=SeedResult,
    status_code=status.HTTP_201_CREATED,
    summary="Seed realistic mock data for the authenticated tenant",
    description=(
        "Generates 3 mock cloud accounts (Azure, AWS, GCP) and inserts "
        "historical cost, event, usage, recommendation, and inventory data "
        "into ClickHouse. Only available outside of production. "
        "Pass `force=true` to overwrite existing seed data."
    ),
)
async def seed_tenant_data(
    req: SeedRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> SeedResult:
    try:
        return await DevSeedService(db).seed(current_user.org_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/seed",
    response_model=ClearResult,
    summary="Remove all seeded mock data for the authenticated tenant",
    description=(
        "Deletes mock cloud accounts from PostgreSQL and purges all "
        "mock rows from every ClickHouse analytical table scoped to this tenant. "
        "Real (non-mock) accounts and their data are not touched."
    ),
)
async def clear_tenant_seed_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> ClearResult:
    return await DevSeedService(db).clear(current_user.org_id)
