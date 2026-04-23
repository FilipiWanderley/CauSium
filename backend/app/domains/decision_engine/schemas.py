from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)


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
