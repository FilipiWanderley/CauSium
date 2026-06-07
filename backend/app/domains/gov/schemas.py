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


# ── Recommendations ────────────────────────────────────────────────────────────

class RecommendationRowOut(BaseModel):
    recommendation_id: str
    category: str
    impact: str
    resource_id: str
    resource_name: str
    resource_group: str
    service: str
    short_description: str
    estimated_savings_usd: float | None


class RecommendationsSummaryOut(BaseModel):
    total: int
    high_impact: int
    total_estimated_savings_usd: float
    by_category: dict[str, int]


# ── Inventory ──────────────────────────────────────────────────────────────────

class ResourceRowOut(BaseModel):
    resource_id: str
    name: str
    resource_type: str
    resource_group: str
    location: str
    environment: str
    owner_team: str
    sku_name: str
    provisioning_state: str


class InventorySummaryOut(BaseModel):
    total_resources: int
    resource_types: int
    resource_groups: int
    unowned_resources: int


# ── Tag Compliance ─────────────────────────────────────────────────────────────

class TopUntaggedRow(BaseModel):
    name: str
    cost_usd: float
    record_count: int


class TagComplianceOut(BaseModel):
    configured_tag_key: str
    total_cost: float
    tagged_cost: float
    untagged_cost: float
    coverage_pct: float
    total_records: int
    tagged_records: int
    untagged_records: int
    top_untagged_resource_groups: list[TopUntaggedRow]
    top_untagged_services: list[TopUntaggedRow]
