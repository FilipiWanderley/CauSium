from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.experiments.models import ExperimentOutcome, ExperimentStatus, RunStatus, RunType


class GuardrailsConfig(BaseModel):
    max_blast_radius_pct: float = Field(default=0.2, ge=0, le=1)
    rollback_on_error_rate: float = Field(default=0.05, ge=0, le=1)
    max_cost_increase_pct: float = Field(default=0.10, ge=0, le=1)
    require_approval: bool = True


class ExperimentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    hypothesis: Optional[str] = None
    description: Optional[str] = None
    opportunity_id: Optional[UUID] = None
    risk_budget_id: Optional[UUID] = None
    guardrails: Optional[GuardrailsConfig] = None
    causal_change_event_ids: Optional[list[str]] = None
    target_environment: str = Field(default="unknown", min_length=2, max_length=50)
    target_criticality: str = Field(default="medium", min_length=2, max_length=50)


class ExperimentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    hypothesis: Optional[str] = None
    description: Optional[str] = None
    simulation_notes: Optional[str] = None
    simulated_savings_usd: Optional[float] = None
    simulated_confidence: Optional[float] = Field(None, ge=0, le=1)
    causal_summary: Optional[str] = None
    guardrails: Optional[GuardrailsConfig] = None
    target_environment: Optional[str] = Field(default=None, min_length=2, max_length=50)
    target_criticality: Optional[str] = Field(default=None, min_length=2, max_length=50)
    actual_savings_usd: Optional[float] = None
    actual_confidence: Optional[float] = Field(None, ge=0, le=1)
    outcome: Optional[ExperimentOutcome] = None


class ExperimentTransition(BaseModel):
    status: ExperimentStatus
    notes: Optional[str] = None


class ExperimentOut(BaseModel):
    id: UUID
    org_id: UUID
    opportunity_id: Optional[UUID]
    title: str
    hypothesis: Optional[str]
    description: Optional[str]
    target_environment: str
    target_criticality: str
    status: ExperimentStatus
    outcome: Optional[ExperimentOutcome]
    simulated_savings_usd: Optional[float]
    simulated_confidence: Optional[float]
    simulation_notes: Optional[str]
    guardrails: Optional[dict]
    causal_change_event_ids: Optional[list]
    causal_summary: Optional[str]
    owner_id: Optional[UUID]
    approved_by_id: Optional[UUID]
    risk_budget_id: Optional[UUID]
    estimated_risk_score: Optional[float]
    actual_savings_usd: Optional[float]
    actual_confidence: Optional[float]
    started_at: Optional[datetime]
    concluded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunCreate(BaseModel):
    run_type: RunType
    notes: Optional[str] = None
    metrics_before: Optional[dict] = None


class RunUpdate(BaseModel):
    status: Optional[RunStatus] = None
    metrics_after: Optional[dict] = None
    impact_usd: Optional[float] = None
    error_rate_before: Optional[float] = None
    error_rate_after: Optional[float] = None
    rollback_triggered: Optional[bool] = None
    rollback_reason: Optional[str] = None
    notes: Optional[str] = None


class RunOut(BaseModel):
    id: UUID
    experiment_id: UUID
    org_id: UUID
    run_type: RunType
    status: RunStatus
    metrics_before: Optional[dict]
    metrics_after: Optional[dict]
    impact_usd: Optional[float]
    error_rate_before: Optional[float]
    error_rate_after: Optional[float]
    rollback_triggered: bool
    rollback_reason: Optional[str]
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperimentSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    total_simulated_savings_usd: float
    total_actual_savings_usd: float
    success_rate: float  # concluded as improved / total concluded


class ExperimentApprovalCreate(BaseModel):
    note: Optional[str] = None


class ExperimentApprovalOut(BaseModel):
    id: UUID
    org_id: UUID
    experiment_id: UUID
    approver_user_id: UUID
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
