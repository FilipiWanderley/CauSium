from __future__ import annotations
"""
Decision Engine scorer.

Composite score formula (0–100):
  score = (financial_impact * 0.45) + (inverse_risk * 0.25) + (inverse_effort * 0.20) + (criticality * 0.10)

financial_impact  : normalized monthly savings potential
inverse_risk      : 100 - risk_score (lower risk = higher score)
inverse_effort    : 100 - effort_score (lower effort = higher score)
criticality       : service criticality weight
"""

from dataclasses import dataclass
from typing import Any

from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    RiskLevel,
)

WEIGHTS = {
    "financial": 0.45,
    "risk": 0.25,
    "effort": 0.20,
    "criticality": 0.10,
}

RISK_SCORES = {
    RiskLevel.LOW: 20.0,
    RiskLevel.MEDIUM: 55.0,
    RiskLevel.HIGH: 90.0,
}

EFFORT_SCORES = {
    EffortLevel.LOW: 15.0,
    EffortLevel.MEDIUM: 50.0,
    EffortLevel.HIGH: 85.0,
}

CATEGORY_RISK = {
    OpportunityCategory.IDLE_RESOURCES: RiskLevel.LOW,
    OpportunityCategory.RIGHTSIZING: RiskLevel.MEDIUM,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: RiskLevel.MEDIUM,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: RiskLevel.MEDIUM,
    OpportunityCategory.STORAGE_OPTIMIZATION: RiskLevel.LOW,
    OpportunityCategory.NETWORK_OPTIMIZATION: RiskLevel.MEDIUM,
    OpportunityCategory.RESERVED_INSTANCES: RiskLevel.LOW,
    OpportunityCategory.LICENSE_OPTIMIZATION: RiskLevel.MEDIUM,
    OpportunityCategory.ARCHITECTURE_CHANGE: RiskLevel.HIGH,
}

CATEGORY_EFFORT = {
    OpportunityCategory.IDLE_RESOURCES: EffortLevel.LOW,
    OpportunityCategory.RIGHTSIZING: EffortLevel.MEDIUM,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: EffortLevel.MEDIUM,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: EffortLevel.MEDIUM,
    OpportunityCategory.STORAGE_OPTIMIZATION: EffortLevel.LOW,
    OpportunityCategory.NETWORK_OPTIMIZATION: EffortLevel.MEDIUM,
    OpportunityCategory.RESERVED_INSTANCES: EffortLevel.LOW,
    OpportunityCategory.LICENSE_OPTIMIZATION: EffortLevel.MEDIUM,
    OpportunityCategory.ARCHITECTURE_CHANGE: EffortLevel.HIGH,
}

ENVIRONMENT_CRITICALITY = {
    "production": 100.0,
    "staging": 60.0,
    "development": 30.0,
    "unknown": 50.0,
}


def normalize_financial_impact(monthly_savings: float, max_savings: float = 5000.0) -> float:
    """Map monthly savings to 0–100. $5k/month = 100."""
    return min(monthly_savings / max_savings * 100, 100.0)


@dataclass
class ScoreResult:
    financial_impact_score: float
    risk_score: float
    effort_score: float
    criticality_score: float
    composite_score: float
    risk_level: RiskLevel
    effort_level: EffortLevel
    rationale: str


def compute_score(
    category: OpportunityCategory,
    monthly_savings_usd: float,
    environment: str = "unknown",
    override_risk: RiskLevel | None = None,
    override_effort: EffortLevel | None = None,
    max_savings: float = 5000.0,
) -> ScoreResult:
    risk_level = override_risk or CATEGORY_RISK[category]
    effort_level = override_effort or CATEGORY_EFFORT[category]

    financial = normalize_financial_impact(monthly_savings_usd, max_savings)
    risk_raw = RISK_SCORES[risk_level]
    effort_raw = EFFORT_SCORES[effort_level]
    criticality = ENVIRONMENT_CRITICALITY.get(environment, 50.0)

    # Inverse: lower risk/effort = higher score
    inv_risk = 100.0 - risk_raw
    inv_effort = 100.0 - effort_raw

    composite = (
        financial * WEIGHTS["financial"]
        + inv_risk * WEIGHTS["risk"]
        + inv_effort * WEIGHTS["effort"]
        + criticality * WEIGHTS["criticality"]
    )

    rationale = (
        f"Financial impact: {financial:.0f}/100 (${monthly_savings_usd:,.0f}/month savings). "
        f"Risk: {risk_level.value} ({risk_raw:.0f} raw → {inv_risk:.0f} inverted). "
        f"Effort: {effort_level.value} ({effort_raw:.0f} raw → {inv_effort:.0f} inverted). "
        f"Environment criticality: {criticality:.0f} ({environment}). "
        f"Composite: {composite:.1f}/100."
    )

    return ScoreResult(
        financial_impact_score=round(financial, 1),
        risk_score=round(risk_raw, 1),
        effort_score=round(effort_raw, 1),
        criticality_score=round(criticality, 1),
        composite_score=round(composite, 1),
        risk_level=risk_level,
        effort_level=effort_level,
        rationale=rationale,
    )


PLAYBOOKS: dict[OpportunityCategory, str] = {
    OpportunityCategory.IDLE_RESOURCES: (
        "1. Identify resource via resource_id in Azure Portal.\n"
        "2. Validate last-accessed date (check Activity Log).\n"
        "3. Create snapshot/backup if required.\n"
        "4. Schedule deallocation during off-peak hours.\n"
        "5. Monitor for 72h to confirm no impact.\n"
        "6. Delete resource and archive evidence."
    ),
    OpportunityCategory.RIGHTSIZING: (
        "1. Pull CPU/memory utilization for last 30 days.\n"
        "2. Identify SKU downgrade target (e.g., D4s_v3 → D2s_v3).\n"
        "3. Create change request and notify service owner.\n"
        "4. Schedule resize in maintenance window.\n"
        "5. Validate application health metrics post-resize.\n"
        "6. Record realized savings in initiative."
    ),
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: (
        "1. Confirm node pool CPU/memory p95 in last 14 days.\n"
        "2. Validate autoscaler constraints (min/max) before action.\n"
        "3. Propose reducing node count by 1 in maintenance window.\n"
        "4. Monitor pod scheduling and saturation after change.\n"
        "5. Track realized savings and rollback if saturation increases."
    ),
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: (
        "1. Confirm node pool autoscaler is disabled and history >= 7 days.\n"
        "2. Validate security blockers: system pool, kube-system, critical workloads.\n"
        "3. Apply conservative autoscaler bounds (min/max) in maintenance window.\n"
        "4. Monitor scaling events, pod pending time, and saturation for 72h.\n"
        "5. Record realized savings and tune min/max if needed."
    ),
    OpportunityCategory.RESERVED_INSTANCES: (
        "1. Analyze usage trend for last 90 days.\n"
        "2. Identify stable workloads with >80% utilization.\n"
        "3. Calculate 1yr vs 3yr RI cost comparison.\n"
        "4. Submit purchase request to FinOps approval.\n"
        "5. Apply RI scope to target subscriptions.\n"
        "6. Track utilization rate monthly."
    ),
    OpportunityCategory.STORAGE_OPTIMIZATION: (
        "1. List storage accounts with low-access patterns.\n"
        "2. Identify blob containers eligible for Cool/Archive tier.\n"
        "3. Create lifecycle management policy.\n"
        "4. Apply policy and validate cost reduction.\n"
        "5. Document tier boundaries for team reference."
    ),
    OpportunityCategory.NETWORK_OPTIMIZATION: (
        "1. Analyze egress traffic patterns.\n"
        "2. Identify cross-region data transfer hotspots.\n"
        "3. Evaluate CDN or regional caching strategy.\n"
        "4. Implement changes with network team approval.\n"
        "5. Monitor bandwidth costs post-change."
    ),
    OpportunityCategory.LICENSE_OPTIMIZATION: (
        "1. Audit license assignments vs. active users.\n"
        "2. Identify unassigned or underused licenses.\n"
        "3. Coordinate with IT/Procurement for reallocation.\n"
        "4. Update license assignments.\n"
        "5. Set quarterly review cadence."
    ),
    OpportunityCategory.ARCHITECTURE_CHANGE: (
        "1. Document current architecture and cost drivers.\n"
        "2. Design target architecture with cost model.\n"
        "3. Review with Tech Lead and Security.\n"
        "4. Create migration plan with rollback strategy.\n"
        "5. Execute phased migration.\n"
        "6. Validate performance and cost after migration."
    ),
}
