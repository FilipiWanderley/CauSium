from __future__ import annotations
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)


class SavingsEvidence(BaseModel):
    """Structured savings evidence projection — computed at read time, no DB storage."""

    current_monthly_cost_estimate: float
    projected_monthly_cost_estimate: float | None = None
    estimated_monthly_savings: float
    estimated_annual_savings: float
    savings_confidence: float  # 0.0–1.0
    confidence_tier: Literal["high", "medium", "low", "insufficient"]
    calculation_basis: str
    evidence_summary: str
    evidence_window_days: int | None = None
    risk_level: RiskLevel
    safety_margin_applied: bool
    methodology: Literal[
        "deterministic_sku_ratio",
        "deterministic_node_reduction",
        "deterministic_autoscaler",
        "heuristic_category_rate",
    ]
    limitations: list[str]


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
    autoscaler_action: str | None = None
    recommended_min_count: int | None = None
    recommended_max_count: int | None = None
    has_kube_system_workloads: bool | None = None
    has_critical_workloads: bool | None = None
    variability_score: float | None = None
    blocked_by: list[str] | None = None
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
    savings_evidence: SavingsEvidence | None = None
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


class OptimizationPlanRecommendation(BaseModel):
    opportunity_id: UUID
    category: OpportunityCategory
    title: str
    resource_id: str | None
    resource_name: str | None
    service: str | None
    environment: str | None
    owner_team: str | None
    estimated_monthly_savings_usd: float
    confidence: float
    base_confidence: float | None = None
    confidence_adjustment: float | None = None
    historical_accuracy: float | None = None
    risk_level: RiskLevel
    effort_level: EffortLevel
    priority_score: float
    rank: int
    why_now: str
    next_step: str
    conflict_hints: list[str]
    conflicting_with_opportunity_ids: list[UUID]


class OptimizationPlanGroup(BaseModel):
    key: str
    label: str
    total_items: int
    total_estimated_monthly_savings_usd: float
    opportunity_ids: list[UUID]


class OptimizationPlanOut(BaseModel):
    total_recommendations: int
    total_savings_monthly_raw_usd: float
    total_savings_monthly_adjusted_usd: float
    total_savings_annual_adjusted_usd: float
    total_savings_monthly: float
    total_savings_annual: float
    confidence_global: float
    summary: str
    summary_source: Literal["deterministic", "ai"]
    ai_summary: str | None = None
    ai_model: str | None = None
    quick_wins: list[OptimizationPlanRecommendation]
    prioritized: list[OptimizationPlanRecommendation]
    groups: list[OptimizationPlanGroup]
    conflict_hints: list[str]
