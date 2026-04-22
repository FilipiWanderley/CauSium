from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GreenSummaryOut(BaseModel):
    total_kg_co2e: float
    total_cost_usd: float
    intensity_avg: float
    mom_delta_pct: Optional[float]
    months_available: int
    data_source: str
    note: str


class EmissionsMonthRowOut(BaseModel):
    month: str
    kg_co2e: float
    cost_usd: float
    delta_pct: Optional[float]


class EmissionsBreakdownRowOut(BaseModel):
    dimension: str
    kg_co2e: float
    cost_usd: float
    share_pct: float
