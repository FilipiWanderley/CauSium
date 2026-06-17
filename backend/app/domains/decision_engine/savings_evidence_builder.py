"""
Savings Evidence Builder — deterministic projection layer.

Transforms raw decision_evidence JSONB + opportunity fields into a
structured SavingsEvidence payload for the API response.

Design principles:
- Pure function, no DB access, no side effects
- Conservative estimates with explicit safety margins
- Transparent methodology and limitations
- Graceful degradation when evidence is incomplete
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.domains.decision_engine.models import (
    OpportunityCategory,
    RiskLevel,
)

if TYPE_CHECKING:
    from app.domains.decision_engine.models import OptimizationOpportunity
    from app.domains.decision_engine.schemas import SavingsEvidence


# Category-level heuristic rates (same as _estimate_savings in service.py)
_HEURISTIC_RATES: dict[OpportunityCategory, float] = {
    OpportunityCategory.IDLE_RESOURCES: 0.80,
    OpportunityCategory.RIGHTSIZING: 0.30,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: 0.20,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: 0.18,
    OpportunityCategory.STORAGE_OPTIMIZATION: 0.40,
    OpportunityCategory.NETWORK_OPTIMIZATION: 0.25,
    OpportunityCategory.RESERVED_INSTANCES: 0.35,
    OpportunityCategory.LICENSE_OPTIMIZATION: 0.20,
    OpportunityCategory.ARCHITECTURE_CHANGE: 0.45,
}

# Base confidence for heuristic-only estimates (no real usage evidence)
_HEURISTIC_CONFIDENCE: dict[OpportunityCategory, float] = {
    OpportunityCategory.IDLE_RESOURCES: 0.30,
    OpportunityCategory.RIGHTSIZING: 0.25,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: 0.25,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: 0.25,
    OpportunityCategory.STORAGE_OPTIMIZATION: 0.25,
    OpportunityCategory.NETWORK_OPTIMIZATION: 0.20,
    OpportunityCategory.RESERVED_INSTANCES: 0.30,
    OpportunityCategory.LICENSE_OPTIMIZATION: 0.20,
    OpportunityCategory.ARCHITECTURE_CHANGE: 0.15,
}

# Categories that have real deterministic engines with evidence
_EVIDENCE_BASED_CATEGORIES = frozenset({
    OpportunityCategory.RIGHTSIZING,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
})

_HEURISTIC_LIMITATIONS: dict[OpportunityCategory, list[str]] = {
    OpportunityCategory.IDLE_RESOURCES: [
        "No real-time usage metrics collected yet",
        "Savings estimate based on category heuristic (80% of current cost)",
        "Requires validation against provider activity logs",
    ],
    OpportunityCategory.STORAGE_OPTIMIZATION: [
        "No blob/object access pattern analysis available",
        "Savings estimate based on category heuristic (40% of current cost)",
        "Requires lifecycle policy evaluation",
    ],
    OpportunityCategory.NETWORK_OPTIMIZATION: [
        "No egress traffic pattern analysis available",
        "Savings estimate based on category heuristic (25% of current cost)",
        "Requires cross-region transfer audit",
    ],
    OpportunityCategory.RESERVED_INSTANCES: [
        "No commitment utilization analysis available",
        "Savings estimate based on category heuristic (35% of current cost)",
        "Requires 90-day usage stability validation",
    ],
    OpportunityCategory.LICENSE_OPTIMIZATION: [
        "No license assignment audit available",
        "Savings estimate based on category heuristic (20% of current cost)",
        "Requires IT/Procurement coordination",
    ],
    OpportunityCategory.ARCHITECTURE_CHANGE: [
        "No architecture cost model analysis available",
        "Savings estimate based on category heuristic (45% of current cost)",
        "High effort and risk — requires detailed migration planning",
    ],
}


def _confidence_tier(confidence: float, window_days: int | None) -> str:
    """Map raw confidence + observation window to a human-readable tier."""
    if confidence < 0.25:
        return "insufficient"
    if confidence >= 0.75 and (window_days or 0) >= 30:
        return "high"
    if confidence >= 0.50 and (window_days or 0) >= 14:
        return "medium"
    return "low"


def _apply_safety_margin(
    savings: float,
    *,
    is_heuristic: bool,
    window_days: int | None,
) -> tuple[float, bool]:
    """Apply conservative safety margin. Returns (adjusted_savings, margin_applied)."""
    if savings <= 0:
        return 0.0, False
    if is_heuristic:
        # 20% haircut for heuristic estimates
        return round(savings * 0.80, 2), True
    if (window_days or 0) < 14:
        # 10% haircut for short observation windows
        return round(savings * 0.90, 2), True
    return round(savings, 2), False


def build_savings_evidence(opportunity: "OptimizationOpportunity") -> "SavingsEvidence | None":
    """
    Build a structured SavingsEvidence from an opportunity's existing data.

    Returns None only if the opportunity has zero savings and no cost data.
    For subscription-level recommendations, generates evidence even without current_cost.
    """

    current_cost = float(opportunity.current_monthly_cost_usd or 0.0)
    monthly_savings = float(opportunity.estimated_monthly_savings_usd or 0.0)

    # If no savings and no cost, nothing to analyze
    if monthly_savings <= 0 and current_cost <= 0:
        return None

    category = opportunity.category
    evidence = opportunity.decision_evidence or {}
    risk_level = opportunity.risk_level or RiskLevel.MEDIUM

    # Check if this opportunity came from Azure Advisor (real provider data)
    if evidence.get("source") == "azure_advisor":
        return _build_from_advisor(opportunity, evidence, current_cost, category, risk_level)

    # Determine if this opportunity has real deterministic evidence
    has_real_evidence = (
        category in _EVIDENCE_BASED_CATEGORIES
        and bool(evidence)
        and evidence.get("confidence") is not None
        and float(evidence.get("confidence") or 0) > 0
    )

    if has_real_evidence:
        return _build_from_evidence(opportunity, evidence, current_cost, category, risk_level)
    else:
        return _build_from_heuristic(opportunity, current_cost, category, risk_level)


def _build_from_evidence(
    opportunity: "OptimizationOpportunity",
    evidence: dict,
    current_cost: float,
    category: OpportunityCategory,
    risk_level: RiskLevel,
) -> "SavingsEvidence":
    """Build SavingsEvidence from real deterministic engine output."""
    from app.domains.decision_engine.schemas import SavingsEvidence

    raw_confidence = float(evidence.get("confidence") or 0.0)
    window_days = evidence.get("window_days")
    if isinstance(window_days, (int, float)):
        window_days = int(window_days)
    else:
        window_days = None

    # Extract financial data from evidence
    ev_current_cost = float(evidence.get("current_monthly_cost") or current_cost)
    ev_projected_cost = evidence.get("estimated_monthly_cost")
    if ev_projected_cost is not None:
        ev_projected_cost = float(ev_projected_cost)
    ev_savings = float(evidence.get("estimated_savings") or 0.0)

    # If evidence doesn't have savings, compute from opportunity fields
    if ev_savings <= 0:
        ev_savings = float(opportunity.estimated_monthly_savings_usd or 0.0)

    # Apply safety margin
    adjusted_savings, margin_applied = _apply_safety_margin(
        ev_savings, is_heuristic=False, window_days=window_days
    )

    # Determine methodology
    if category == OpportunityCategory.RIGHTSIZING:
        methodology = "deterministic_sku_ratio"
        calculation_basis = _build_rightsizing_basis(evidence)
    elif category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING:
        methodology = "deterministic_node_reduction"
        calculation_basis = _build_aks_nodepool_basis(evidence)
    else:
        methodology = "deterministic_autoscaler"
        calculation_basis = _build_aks_autoscaler_basis(evidence)

    # Build evidence summary
    evidence_summary = _build_evidence_summary(evidence, category, adjusted_savings)

    # Determine limitations
    limitations: list[str] = []
    if (window_days or 0) < 30:
        limitations.append(f"Observation window is {window_days or 0} days (30+ recommended)")
    if raw_confidence < 0.75:
        limitations.append("Confidence below high-tier threshold")
    if margin_applied:
        limitations.append("Conservative safety margin applied to estimate")

    tier = _confidence_tier(raw_confidence, window_days)

    return SavingsEvidence(
        current_monthly_cost_estimate=round(ev_current_cost, 2),
        projected_monthly_cost_estimate=round(ev_projected_cost, 2) if ev_projected_cost is not None else None,
        estimated_monthly_savings=adjusted_savings,
        estimated_annual_savings=round(adjusted_savings * 12, 2),
        savings_confidence=round(raw_confidence, 3),
        confidence_tier=tier,
        calculation_basis=calculation_basis,
        evidence_summary=evidence_summary,
        evidence_window_days=window_days,
        risk_level=risk_level,
        safety_margin_applied=margin_applied,
        methodology=methodology,
        limitations=limitations,
    )


def _build_from_heuristic(
    opportunity: "OptimizationOpportunity",
    current_cost: float,
    category: OpportunityCategory,
    risk_level: RiskLevel,
) -> "SavingsEvidence":
    """Build SavingsEvidence from category-level heuristic (no real usage data)."""
    from app.domains.decision_engine.schemas import SavingsEvidence

    rate = _HEURISTIC_RATES.get(category, 0.20)
    base_confidence = _HEURISTIC_CONFIDENCE.get(category, 0.20)
    raw_savings = round(current_cost * rate, 2)

    # Apply 20% safety margin for heuristic estimates
    adjusted_savings, margin_applied = _apply_safety_margin(
        raw_savings, is_heuristic=True, window_days=None
    )

    projected_cost = round(current_cost - adjusted_savings, 2) if adjusted_savings > 0 else None

    calculation_basis = (
        f"Category heuristic: {rate * 100:.0f}% of current monthly cost "
        f"(${current_cost:,.2f}) with 20% conservative safety margin applied."
    )

    evidence_summary = (
        f"Estimated {adjusted_savings:,.2f}/month savings based on "
        f"{category.value} category benchmark. "
        f"This is a preliminary estimate — no real usage or performance "
        f"evidence has been collected yet for this resource."
    )

    limitations = _HEURISTIC_LIMITATIONS.get(category, [
        "No real usage evidence available",
        "Savings estimate based on category heuristic",
    ])

    tier = _confidence_tier(base_confidence, None)

    return SavingsEvidence(
        current_monthly_cost_estimate=round(current_cost, 2),
        projected_monthly_cost_estimate=projected_cost,
        estimated_monthly_savings=adjusted_savings,
        estimated_annual_savings=round(adjusted_savings * 12, 2),
        savings_confidence=round(base_confidence, 3),
        confidence_tier=tier,
        calculation_basis=calculation_basis,
        evidence_summary=evidence_summary,
        evidence_window_days=None,
        risk_level=risk_level,
        safety_margin_applied=margin_applied,
        methodology="heuristic_category_rate",
        limitations=list(limitations),
    )


def _build_from_advisor(
    opportunity: "OptimizationOpportunity",
    evidence: dict,
    current_cost: float,
    category: OpportunityCategory,
    risk_level: RiskLevel,
) -> "SavingsEvidence":
    """Build SavingsEvidence from Azure Advisor data (real provider-calculated savings).

    For subscription-level recommendations (Savings Plans, Reserved Instances):
    - Uses currentSpend from Advisor if available
    - Returns None for current_monthly_cost_estimate when Advisor doesn't provide it
    - This prevents showing R$ 0.00 which is misinterpreted by users
    """
    from app.domains.decision_engine.schemas import SavingsEvidence

    monthly_savings = float(opportunity.estimated_monthly_savings_usd or 0.0)

    # Check if Advisor provided currentSpend
    advisor_current_spend = evidence.get("current_spend")
    if advisor_current_spend is not None:
        current_cost = float(advisor_current_spend)
        projected_cost = round(current_cost - monthly_savings, 2) if monthly_savings > 0 else None
        current_monthly_cost_estimate = round(current_cost, 2)
    else:
        # Advisor does NOT provide currentSpend for Savings Plans/Reserved Instances
        # Return None to show "N/A" in frontend instead of "R$ 0.00"
        projected_cost = None
        current_monthly_cost_estimate = None

    advisor_desc = evidence.get("advisor_description") or ""
    advisor_impact = evidence.get("advisor_impact") or "N/A"
    is_subscription_level = evidence.get("is_subscription_level", False)

    # Map Advisor impact to confidence
    confidence_map = {"High": 0.90, "Medium": 0.80, "Low": 0.70}
    confidence = confidence_map.get(advisor_impact, 0.80)

    tier = _confidence_tier(confidence, 30)

    # Generate appropriate calculation basis and evidence summary
    if is_subscription_level:
        calculation_basis = (
            f"Azure Advisor subscription-level recommendation (impact: {advisor_impact}). "
            f"Savings calculated by the cloud provider based on subscription usage patterns."
        )
        evidence_summary = (
            f"Azure Advisor estimates monthly savings of {monthly_savings:,.2f} "
            f"for this subscription-level recommendation. "
            f"{advisor_desc}"
        )
    else:
        calculation_basis = (
            f"Azure Advisor recommendation (impact: {advisor_impact}). "
            f"Savings calculated by the cloud provider based on actual resource usage and pricing."
        )
        evidence_summary = (
            f"Economia de {monthly_savings:,.2f}/mês calculada pelo Azure Advisor. "
            f"{advisor_desc}"
        )

    limitations: list[str] = []
    if advisor_impact == "Low":
        limitations.append("Azure Advisor classifies this as low-impact")
    if is_subscription_level:
        limitations.append("Subscription-level recommendation - resource metrics not applicable")

    return SavingsEvidence(
        current_monthly_cost_estimate=current_monthly_cost_estimate,
        projected_monthly_cost_estimate=projected_cost,
        estimated_monthly_savings=round(monthly_savings, 2),
        estimated_annual_savings=round(monthly_savings * 12, 2),
        savings_confidence=confidence,
        confidence_tier=tier,
        calculation_basis=calculation_basis,
        evidence_summary=evidence_summary,
        evidence_window_days=30,
        risk_level=risk_level,
        safety_margin_applied=False,
        methodology="azure_advisor",
        limitations=limitations,
    )


# ── Evidence summary builders ──────────────────────────────────────────────────


def _build_rightsizing_basis(evidence: dict) -> str:
    current_sku = evidence.get("current_sku") or "unknown"
    recommended_sku = evidence.get("recommended_sku") or "unknown"
    cpu_p95 = evidence.get("cpu_p95")
    mem_p95 = evidence.get("memory_p95")
    window = evidence.get("window_days") or 0

    parts = [
        f"SKU downgrade: {current_sku} -> {recommended_sku}.",
        "Cost ratio derived from vCPU count reduction within same family.",
    ]
    if cpu_p95 is not None and mem_p95 is not None:
        parts.append(f"Utilization evidence: CPU p95={cpu_p95:.1f}%, memory p95={mem_p95:.1f}%.")
    if window:
        parts.append(f"Observation window: {window} days.")
    return " ".join(parts)


def _build_aks_nodepool_basis(evidence: dict) -> str:
    current_nodes = evidence.get("current_node_count")
    recommended_nodes = evidence.get("recommended_node_count")
    cpu_p95 = evidence.get("cpu_p95")
    mem_p95 = evidence.get("memory_p95")

    parts = []
    if current_nodes is not None and recommended_nodes is not None:
        parts.append(f"Node count reduction: {current_nodes} -> {recommended_nodes}.")
    if cpu_p95 is not None and mem_p95 is not None:
        parts.append(f"Utilization: CPU p95={cpu_p95:.1f}%, memory p95={mem_p95:.1f}%.")
    parts.append("Per-node cost derived from total pool cost / node count.")
    return " ".join(parts) if parts else "AKS node pool rightsizing based on utilization metrics."


def _build_aks_autoscaler_basis(evidence: dict) -> str:
    current_nodes = evidence.get("current_node_count")
    rec_min = evidence.get("recommended_min_count")
    rec_max = evidence.get("recommended_max_count")

    parts = ["Autoscaler enablement recommendation."]
    if current_nodes is not None:
        parts.append(f"Current fixed nodes: {current_nodes}.")
    if rec_min is not None and rec_max is not None:
        parts.append(f"Recommended bounds: min={rec_min}, max={rec_max}.")
    parts.append("Savings from elastic scaling during low-demand periods.")
    return " ".join(parts)


def _build_evidence_summary(evidence: dict, category: OpportunityCategory, savings: float) -> str:
    """Build a human-readable evidence summary."""
    reason = evidence.get("reason") or ""
    confidence = float(evidence.get("confidence") or 0.0)
    window = evidence.get("window_days") or 0

    if category == OpportunityCategory.RIGHTSIZING:
        current_sku = evidence.get("current_sku") or "current SKU"
        recommended_sku = evidence.get("recommended_sku") or "smaller SKU"
        return (
            f"Rightsizing from {current_sku} to {recommended_sku} "
            f"saves an estimated ${savings:,.2f}/month. "
            f"Based on {window}-day observation window with "
            f"{confidence * 100:.0f}% confidence. {reason}"
        ).strip()

    if category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING:
        cluster = evidence.get("cluster_name") or "cluster"
        pool = evidence.get("node_pool") or "pool"
        return (
            f"Reducing nodes in {cluster}/{pool} "
            f"saves an estimated ${savings:,.2f}/month. "
            f"{confidence * 100:.0f}% confidence. {reason}"
        ).strip()

    if category == OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION:
        cluster = evidence.get("cluster_name") or "cluster"
        pool = evidence.get("node_pool") or "pool"
        return (
            f"Enabling autoscaler on {cluster}/{pool} "
            f"saves an estimated ${savings:,.2f}/month. "
            f"{confidence * 100:.0f}% confidence. {reason}"
        ).strip()

    return f"Estimated ${savings:,.2f}/month savings. {reason}".strip()
