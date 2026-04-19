from __future__ import annotations
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.cloud_accounts.service import CloudAccountService
from app.domains.cloud_ledger.schemas import (
    CostTrend,
    DashboardMetrics,
    DetailedCostRow,
    IngestRequest,
    IngestResult,
    ReservationCoverageSummary,
    ServiceBreakdown,
)
from app.domains.cloud_ledger.service import CloudLedgerService

router = APIRouter(prefix="/ledger", tags=["cloud-ledger"])


@router.post("/ingest", response_model=IngestResult)
async def trigger_ingest(
    req: IngestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = CloudLedgerService(db)
    return await service.ingest_account(current_user.org_id, req.account_id, req.start_date, req.end_date)


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    accounts, _ = await CloudAccountService(db).list_accounts(current_user.org_id)
    active = sum(1 for a in accounts if a.status.value == "active")
    service = CloudLedgerService(db)
    return await service.get_dashboard_metrics(current_user.org_id, active)


@router.get("/costs/trend", response_model=List[CostTrend])
async def cost_trend(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=365),
):
    service = CloudLedgerService(db)
    return service.get_cost_trend(current_user.org_id, days=days)


@router.get("/reservations/coverage", response_model=ReservationCoverageSummary)
async def reservation_coverage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=365),
):
    service = CloudLedgerService(db)
    return service.get_reservation_coverage(current_user.org_id, days=days)



@router.get("/costs/services", response_model=Page[ServiceBreakdown])
async def top_services(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=365),
    page_params: PageParams = Depends(PageParams),
):
    service = CloudLedgerService(db)
    items, total = service.get_top_services(current_user.org_id, days=days, limit=page_params.limit, offset=page_params.offset)
    return Page.of(items, total, page_params)



@router.get("/costs/teams", response_model=Page[ServiceBreakdown])
async def top_teams(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=365),
    page_params: PageParams = Depends(PageParams),
):
    service = CloudLedgerService(db)
    items, total = service.get_top_teams(current_user.org_id, days=days, limit=page_params.limit, offset=page_params.offset)
    return Page.of(items, total, page_params)


@router.get("/costs", response_model=Page[DetailedCostRow])
async def detailed_costs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=365),
    service: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    owner_team: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    region: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    resource_name: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    page_params: PageParams = Depends(PageParams),
):
    service_layer = CloudLedgerService(db)
    items, total = service_layer.get_detailed_costs(
        current_user.org_id,
        days=days,
        service=service,
        provider=provider,
        owner_team=owner_team,
        environment=environment,
        region=region,
        resource_id=resource_id,
        resource_name=resource_name,
        account_id=account_id,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of(items, total, page_params)
