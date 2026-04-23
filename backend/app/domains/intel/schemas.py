from __future__ import annotations

from datetime import date
from typing import Literal
from typing import Any

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
