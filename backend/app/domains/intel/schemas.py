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
