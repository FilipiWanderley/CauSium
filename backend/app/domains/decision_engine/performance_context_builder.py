"""
Performance Context Builder — deterministic performance evidence layer.

Extracts CPU/memory utilization, trends, idle detection, and AKS pressure
from existing decision_evidence and model fields.

Design principles:
- Pure function, no DB access, no side effects
- Never invent performance data — null when unavailable
- Transparent evidence quality and limitations
- Deterministic extraction from existing opportunity data
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.decision_engine.models import OptimizationOpportunity
    from app.domains.decision_engine.schemas import PerformanceContext

from app.domains.decision_engine.models import OpportunityCategory


# Categories that typically have real performance evidence
_PERFORMANCE_CATEGORIES = frozenset({
    OpportunityCategory.RIGHTSIZING,
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
})


def build_performance_context(opportunity: "OptimizationOpportunity") -> "PerformanceContext | None":
    """
    Build a structured PerformanceContext from an opportunity's decision_evidence.

    Returns None if no performance data is available.
    """
    from app.domains.decision_engine.schemas import PerformanceContext

    evidence = opportunity.decision_evidence or {}
    category = opportunity.category

    # Only build if we have actual performance data
    cpu_p95 = _safe_float(evidence.get("cpu_p95"))
    memory_p95 = _safe_float(evidence.get("memory_p95"))

    # If no CPU or memory data at all, no performance context to build
    if cpu_p95 is None and memory_p95 is None:
        return None

    data_sources: list[str] = ["decision_evidence"]
    limitations: list[str] = []

    # Core utilization metrics
    avg_cpu = _safe_float(evidence.get("avg_cpu"))
    avg_memory = _safe_float(evidence.get("avg_memory"))

    # Observation window
    observation_window_days = _safe_int(evidence.get("window_days")) or _safe_int(evidence.get("history_days"))

    # Utilization trend (derived from stddev if available)
    cpu_p95_stddev = _safe_float(evidence.get("cpu_p95_stddev"))
    memory_p95_stddev = _safe_float(evidence.get("memory_p95_stddev"))
    utilization_trend = _compute_trend(cpu_p95, memory_p95, cpu_p95_stddev, memory_p95_stddev)

    # Idle detection
    idle_days = _compute_idle_days(cpu_p95, memory_p95, observation_window_days)

    # Resource allocation (AKS-specific)
    requested_cpu = _safe_float(evidence.get("requested_cpu"))
    allocated_cpu = _safe_float(evidence.get("allocated_cpu"))
    requested_memory = _safe_float(evidence.get("requested_memory"))
    allocated_memory = _safe_float(evidence.get("allocated_memory"))

    # AKS pressure indicators
    aks_pressure = _compute_aks_pressure(evidence, category)

    # Evidence quality assessment
    evidence_quality = _assess_quality(
        cpu_p95=cpu_p95,
        memory_p95=memory_p95,
        observation_window_days=observation_window_days,
        has_allocation_data=requested_cpu is not None or allocated_cpu is not None,
        category=category,
    )

    # Build limitations
    if observation_window_days is not None and observation_window_days < 14:
        limitations.append(f"Short observation window ({observation_window_days} days, 14+ recommended)")
    if observation_window_days is None:
        limitations.append("Observation window unknown")
        data_sources.append("inferred")
    if avg_cpu is None and avg_memory is None:
        limitations.append("Only p95 values available, no average utilization")
    if category not in _PERFORMANCE_CATEGORIES:
        limitations.append("Performance data not typical for this category")
    if cpu_p95_stddev is None and memory_p95_stddev is None:
        limitations.append("No variability data available for trend analysis")

    return PerformanceContext(
        cpu_p95=_round_or_none(cpu_p95),
        memory_p95=_round_or_none(memory_p95),
        avg_cpu=_round_or_none(avg_cpu),
        avg_memory=_round_or_none(avg_memory),
        utilization_trend=utilization_trend,
        idle_days=idle_days,
        requested_cpu=_round_or_none(requested_cpu),
        allocated_cpu=_round_or_none(allocated_cpu),
        requested_memory=_round_or_none(requested_memory),
        allocated_memory=_round_or_none(allocated_memory),
        aks_pressure=aks_pressure,
        observation_window_days=observation_window_days,
        evidence_quality=evidence_quality,
        data_sources=data_sources,
        limitations=limitations,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _safe_float(value: object) -> float | None:
    """Safely convert to float, returning None on failure."""
    if value is None:
        return None
    try:
        result = float(value)
        return result if result == result else None  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    """Safely convert to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _round_or_none(value: float | None, decimals: int = 2) -> float | None:
    """Round a float or return None."""
    if value is None:
        return None
    return round(value, decimals)


def _compute_trend(
    cpu_p95: float | None,
    memory_p95: float | None,
    cpu_stddev: float | None,
    memory_stddev: float | None,
) -> str:
    """
    Determine utilization trend based on variability.

    - "stable": low stddev relative to p95 (< 15% coefficient of variation)
    - "variable": moderate stddev (15-40% CV)
    - "volatile": high stddev (> 40% CV)
    - "unknown": no stddev data available
    """
    if cpu_stddev is None and memory_stddev is None:
        return "unknown"

    cvs: list[float] = []
    if cpu_p95 and cpu_p95 > 0 and cpu_stddev is not None:
        cvs.append(cpu_stddev / cpu_p95)
    if memory_p95 and memory_p95 > 0 and memory_stddev is not None:
        cvs.append(memory_stddev / memory_p95)

    if not cvs:
        return "unknown"

    avg_cv = sum(cvs) / len(cvs)
    if avg_cv < 0.15:
        return "stable"
    if avg_cv < 0.40:
        return "variable"
    return "volatile"


def _compute_idle_days(
    cpu_p95: float | None,
    memory_p95: float | None,
    window_days: int | None,
) -> int | None:
    """
    Estimate idle days based on very low utilization.

    If CPU p95 < 5% AND memory p95 < 10% over the observation window,
    the resource is considered idle for the entire window.
    Returns None if we can't determine idle status.
    """
    if cpu_p95 is None or memory_p95 is None:
        return None
    if window_days is None or window_days <= 0:
        return None

    # Very conservative: only mark as idle if both CPU and memory are extremely low
    if cpu_p95 < 5.0 and memory_p95 < 10.0:
        return window_days
    return 0


def _compute_aks_pressure(evidence: dict, category: OpportunityCategory) -> str | None:
    """
    Compute AKS node pressure indicator.

    - "low": CPU < 30% AND memory < 40%
    - "moderate": CPU 30-60% OR memory 40-70%
    - "high": CPU > 60% OR memory > 70%
    - None: not an AKS category or no data
    """
    if category not in (
        OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
        OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
    ):
        return None

    cpu_p95 = _safe_float(evidence.get("cpu_p95"))
    memory_p95 = _safe_float(evidence.get("memory_p95"))

    if cpu_p95 is None and memory_p95 is None:
        return None

    cpu = cpu_p95 or 0.0
    mem = memory_p95 or 0.0

    if cpu > 60.0 or mem > 70.0:
        return "high"
    if cpu > 30.0 or mem > 40.0:
        return "moderate"
    return "low"


def _assess_quality(
    *,
    cpu_p95: float | None,
    memory_p95: float | None,
    observation_window_days: int | None,
    has_allocation_data: bool,
    category: OpportunityCategory,
) -> str:
    """
    Assess overall evidence quality.

    - "high": both metrics + 30d+ window + allocation data
    - "medium": both metrics + 14d+ window
    - "low": partial metrics or short window
    - "insufficient": minimal data
    """
    has_both_metrics = cpu_p95 is not None and memory_p95 is not None
    window = observation_window_days or 0

    if has_both_metrics and window >= 30 and has_allocation_data:
        return "high"
    if has_both_metrics and window >= 14:
        return "medium"
    if has_both_metrics or (cpu_p95 is not None and window >= 7):
        return "low"
    return "insufficient"
