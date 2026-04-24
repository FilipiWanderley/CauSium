from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)


class OpportunityDecisionEvidence(BaseModel):
    cpu_p95: float | None = None
    memory_p95: float | None = None
    window_days: int | None = None
    history_days: int | None = None
    current_sku: str | None = None
    recommended_sku: str | None = None
    current_monthly_cost: float | None = None
    estimated_monthly_cost: float | None = None
    estimated_savings: float | None = None
    estimated_savings_pct: float | None = None
    confidence: float | None = None
    risk_level: RiskLevel | None = None
    reason: str | None = None
    resource_type: str | None = None
    cluster_name: str | None = None
    node_pool: str | None = None
    current_node_count: int | None = None
    recommended_node_count: int | None = None
    node_sku: str | None = None
    allocated_cpu: float | None = None
    allocated_memory: float | None = None
    requested_cpu: float | None = None
    requested_memory: float | None = None
    is_system_pool: bool | None = None
    autoscaler_enabled: bool | None = None
    autoscaler_min_count: int | None = None
    autoscaler_max_count: int | None = None
    has_kube_system_workloads: bool | None = None
    has_critical_workloads: bool | None = None
    requested_pressure: bool | None = None
    cpu_p95_stddev: float | None = None
    memory_p95_stddev: float | None = None

    model_config = ConfigDict(extra="allow")


class OpportunityOut(BaseModel):
    id: UUID
    org_id: UUID
    account_id: UUID | None
    title: str
    description: str
    category: OpportunityCategory
    composite_score: float
    financial_impact_score: float
    risk_score: float
    effort_score: float
    criticality_score: float
    estimated_monthly_savings_usd: float
    estimated_annual_savings_usd: float
    current_monthly_cost_usd: float
    risk_level: RiskLevel
    effort_level: EffortLevel
    status: OpportunityStatus
    resource_id: str | None
    resource_name: str | None
    sku_name: str | None
    machine_family: str | None
    service: str | None
    region: str | None
    environment: str | None
    owner_team: str | None
    score_rationale: str | None
    playbook: str | None
    decision_evidence: OpportunityDecisionEvidence | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OpportunityCreate(BaseModel):
    title: str
    description: str
    category: OpportunityCategory
    estimated_monthly_savings_usd: float
    current_monthly_cost_usd: float = 0.0
    account_id: UUID | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    sku_name: str | None = None
    machine_family: str | None = None
    service: str | None = None
    region: str | None = None
    environment: str = "unknown"
    owner_team: str | None = None
    risk_level: RiskLevel | None = None
    effort_level: EffortLevel | None = None


class OpportunityStatusUpdate(BaseModel):
    status: OpportunityStatus


class OpportunitySummary(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    total_potential_savings_usd: float
    top_category: str | None
