from __future__ import annotations
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CostQueryParams(BaseModel):
    start_date: date
    end_date: date
    provider: str | None = None
    service: str | None = None
    environment: str | None = None
    owner_team: str | None = None
    group_by: list[str] = Field(default=["date"])


class CostRow(BaseModel):
    dimension: str
    cost_usd: float
    usage_quantity: float | None = None


class CostSummary(BaseModel):
    total_cost_usd: float
    period_start: date
    period_end: date
    rows: list[CostRow]
    currency: str = "USD"


class CostTrend(BaseModel):
    date: date
    cost_usd: float
    provider: str | None = None


class ServiceBreakdown(BaseModel):
    service: str
    cost_usd: float
    percentage: float


class DashboardMetrics(BaseModel):
    current_month_cost: float
    previous_month_cost: float
    mom_change_pct: float
    daily_trend: list[CostTrend]
    top_services: list[ServiceBreakdown]
    top_teams: list[ServiceBreakdown]
    event_count_7d: int
    active_accounts: int


class DetailedCostRow(BaseModel):
    date: date
    account_id: str
    provider: str
    subscription_id: str | None = None
    service: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    region: str | None = None
    environment: str | None = None
    owner_team: str | None = None
    cost_usd: float
    usage_quantity: float | None = None
    usage_unit: str | None = None
    currency: str | None = None


class IngestRequest(BaseModel):
    account_id: UUID
    start_date: date
    end_date: date


class IngestResult(BaseModel):
    account_id: UUID
    cost_records: int
    event_records: int
    status: str
    message: str | None = None
