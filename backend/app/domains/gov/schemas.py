from __future__ import annotations

from pydantic import BaseModel


class GovSummaryOut(BaseModel):
    total_resources: int
    unowned_resources: int
    unowned_cost_usd: float
    unowned_pct: float
    teams_evaluated: int
    avg_compliance_pct: float


class UnownedCostRowOut(BaseModel):
    service: str
    resource_id: str
    region: str
    environment: str
    cost_usd: float
    days_active: int


class LabelComplianceRowOut(BaseModel):
    team: str
    total_cost_usd: float
    untagged_cost_usd: float
    compliance_pct: float
