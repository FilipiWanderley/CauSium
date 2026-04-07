from __future__ import annotations
from datetime import date
from uuid import UUID

from pydantic import BaseModel


class SavingsRecord(BaseModel):
    initiative_id: UUID
    title: str
    realized_savings_usd: float
    completed_at: str | None


class ExecutiveSummary(BaseModel):
    # Costs
    current_month_cost_usd: float
    previous_month_cost_usd: float
    mom_change_pct: float
    ytd_cost_usd: float

    # Savings
    total_realized_savings_usd: float
    total_potential_savings_usd: float
    savings_this_month_usd: float

    # Opportunities
    open_opportunities: int
    in_progress_initiatives: int
    completed_initiatives: int

    # Forecast (simple linear)
    forecast_next_month_usd: float
    forecast_confidence: str

    # Top savings
    top_savings: list[SavingsRecord]


class TeamScorecard(BaseModel):
    team: str
    current_month_cost_usd: float
    previous_month_cost_usd: float
    mom_change_pct: float
    open_opportunities: int
    realized_savings_usd: float
    efficiency_score: float  # 0–100


class ScorecardResponse(BaseModel):
    teams: list[TeamScorecard]
    org_efficiency_score: float
