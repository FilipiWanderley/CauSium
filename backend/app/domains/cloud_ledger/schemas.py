from __future__ import annotations
from datetime import date, datetime
from typing import Literal
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
    currency: str = "USD"
    data_min_date: date | None = None
    data_max_date: date | None = None
    subscriptions_included: int = 0
    cost_basis: str = "actual_pre_tax"
    billing_currency: str = "BRL"


class ReservationCoverageByService(BaseModel):
    service: str
    compute_cost_usd: float
    reserved_cost_usd: float
    uncovered_cost_usd: float
    coverage_pct: float


class ReservationCoverageSummary(BaseModel):
    period_start: date
    period_end: date
    total_compute_cost_usd: float
    total_reserved_cost_usd: float
    uncovered_compute_cost_usd: float
    coverage_pct: float
    has_active_reservations: bool
    services: list[ReservationCoverageByService]
    recommendation: str


class ReservationEfficiencyByFamily(BaseModel):
    family: str
    reserved_capacity_units: float
    effective_used_units: float
    idle_reserved_units: float
    utilization_pct: float
    waste_cost_usd: float
    payg_equivalent_cost_usd: float
    exchange_candidate: bool
    recommended_action: Literal[
        "keep",
        "resize_resource",
        "schedule_stop",
        "exchange_reservation",
        "do_not_renew",
    ]
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    action_priority: int = Field(ge=1, le=5)
    exchange_eligible: bool = False
    renewal_window_days: int | None = None
    advisory_signals: list[str] = Field(default_factory=list)


class ReservationEfficiencySummary(BaseModel):
    period_start: date
    period_end: date
    total_families: int
    total_reserved_capacity_units: float
    total_effective_used_units: float
    total_idle_reserved_units: float
    avg_utilization_pct: float
    total_waste_cost_usd: float
    total_payg_equivalent_cost_usd: float
    families: list[ReservationEfficiencyByFamily]
    recommendation: str


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


class SubscriptionCostBreakdown(BaseModel):
    subscription_id: str
    subscription_name: str | None = None
    total_cost_usd: float
    row_count: int
    max_date: date
    percentage_of_total: float


class SubscriptionCostSummary(BaseModel):
    days: int
    total_cost_usd: float
    subscription_count: int
    items: list[SubscriptionCostBreakdown]


class IngestRequest(BaseModel):
    account_id: UUID
    start_date: date
    end_date: date


class IngestResult(BaseModel):
    account_id: UUID
    cost_records: int
    event_records: int
    recommendation_records: int = 0
    inventory_records: int = 0
    usage_records: int = 0
    status: str
    message: str | None = None


class ReconciliationSubscriptionRow(BaseModel):
    subscription_id: str
    account_id: str | None = None
    display_name: str | None = None
    provider: str | None = None
    total_cost: float
    records_count: int
    min_date: date | None = None
    max_date: date | None = None
    currency: str | None = None
    external_id_match: bool = False


class ReconciliationWarnings(BaseModel):
    no_data: bool = False
    mixed_currency: bool = False
    partial_range: bool = False
    missing_subscription_id: bool = False
    account_mismatch: bool = False
    orphan_records: int = 0


class ReconciliationReport(BaseModel):
    org_id: str
    account_id: str | None = None
    subscription_id: str | None = None
    provider: str | None = None
    start_date: date
    end_date: date
    total_cost: float
    dashboard_equivalent_total: float
    difference: float
    difference_pct: float
    records_count: int
    min_date: date | None = None
    max_date: date | None = None
    distinct_services: int
    distinct_resources: int
    subscription_count: int
    currencies: list[str]
    dominant_currency: str
    mixed_currency: bool
    by_subscription: list[ReconciliationSubscriptionRow]
    warnings: ReconciliationWarnings
    note: str = "This report reflects ingested data only and is not an official cloud provider invoice."


class IntegrityMetadata(BaseModel):
    ingestion_gap_days: int
    sync_age_minutes: float | None = None
    reconciliation_status: Literal["healthy", "delayed", "partial", "warning"]
    last_sync_at: datetime | None = None
    data_through_date: date | None = None
    billing_period: str = "calendar_month"
    subscriptions_active: int = 0
    # FINOPS-4.1: export capability detection
    detected_cost_type: Literal["actual", "amortized", "mixed", "unknown"] = "unknown"
    export_format_hint: Literal["legacy", "modern", "focus", "unknown"] = "unknown"
    reservation_metadata_available: bool = False
    pricing_model_available: bool = False
    charge_type_available: bool = False
    benefit_metadata_available: bool = False
    cost_basis_explanation: str = ""
    portal_comparison_hint: str = ""
