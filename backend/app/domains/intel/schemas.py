from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExplainCostChangeRequest(BaseModel):
    start_date: date
    end_date: date
    provider: str | None = None
    language: Literal["pt", "en"] | None = None


class ExplainCostCause(BaseModel):
    cause: str
    evidence: list[str] = Field(default_factory=list)
    estimated_impact_usd: float | None = None


class ExplainCostChangeOut(BaseModel):
    summary: str
    causes: list[ExplainCostCause]
    impact: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    model: str | None = None
    debug: dict[str, Any] | None = None


class CostAnomalyOut(BaseModel):
    id: str
    provider: str
    service: str
    observed_date: date
    current_cost_usd: float
    historical_mean_usd: float
    historical_stddev_usd: float
    z_score: float
    deviation_pct: float | None = None
    severity: Literal["low", "medium", "high"]
    window_days: int
    z_threshold: float
    created_at: str


class DetectCostAnomaliesRequest(BaseModel):
    lookback_days: int = Field(default=14, ge=7, le=60)
    z_threshold: float = Field(default=2.5, ge=1.0, le=10.0)
    min_history_days: int = Field(default=7, ge=3, le=30)
    min_delta_usd: float = Field(default=10.0, ge=0.0, le=100000.0)


class DetectCostAnomaliesOut(BaseModel):
    observed_date: date | None = None
    scanned_services: int
    detected: int
    created: int
    anomalies: list[CostAnomalyOut] = Field(default_factory=list)


class IntelInsightsOut(BaseModel):
    top_saving_opportunity: str
    main_risk: str
    cost_trend_summary: str
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    model: str | None = None
    debug: dict[str, Any] | None = None


class ExplainRecommendationOut(BaseModel):
    summary: str
    why_now: str
    expected_impact: str
    risks: list[str] = Field(default_factory=list)
    recommended_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    model: str | None = None
    debug: dict[str, Any] | None = None


class CreateExecutionPlanRequest(BaseModel):
    opportunity_ids: list[UUID] = Field(min_length=1)
    mode: Literal["manual_review", "pulselab_handoff"] = "manual_review"


class ExecutionPlanOut(BaseModel):
    execution_plan_id: str
    status: Literal["review_required", "blocked"]
    mode: Literal["manual_review", "pulselab_handoff"]
    total_savings_monthly: float
    risk_level: Literal["low", "medium", "high"]
    conflicts: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    gates_triggered: list[str] = Field(default_factory=list)
    selected_opportunity_ids: list[str] = Field(default_factory=list)


class ExecutionPlanListItemOut(BaseModel):
    execution_plan_id: str
    status: str
    risk_level: str
    total_savings_monthly: float
    gates_triggered: list[str] = Field(default_factory=list)
    selected_opportunity_ids: list[str] = Field(default_factory=list)
    created_at: datetime
