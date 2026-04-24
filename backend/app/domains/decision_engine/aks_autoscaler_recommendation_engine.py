from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AksAutoscalerRecommendationDecision:
    recommend: bool
    reason: str
    risk_level: str
    confidence: float
    evidence: dict[str, float | int | str | bool | list[str] | None]


def _variability_score(cpu_p95_stddev: float | None, memory_p95_stddev: float | None) -> float:
    cpu_component = min(1.0, max(0.0, float(cpu_p95_stddev or 0.0) / 20.0))
    memory_component = min(1.0, max(0.0, float(memory_p95_stddev or 0.0) / 25.0))
    score = (cpu_component + memory_component) / 2.0
    return math.floor(score * 100) / 100.0


def decide_aks_autoscaler_recommendation(
    *,
    cluster_name: str | None,
    node_pool: str | None,
    node_sku: str | None,
    current_node_count: int,
    current_monthly_cost: float,
    cpu_p95: float | None,
    memory_p95: float | None,
    history_days: int,
    autoscaler_enabled: bool,
    autoscaler_min_count: int | None,
    autoscaler_max_count: int | None,
    is_system_pool: bool = False,
    has_kube_system_workloads: bool = False,
    has_critical_workloads: bool = False,
    cpu_p95_stddev: float | None = None,
    memory_p95_stddev: float | None = None,
) -> AksAutoscalerRecommendationDecision:
    variability_score = _variability_score(cpu_p95_stddev, memory_p95_stddev)
    blocked_by: list[str] = []
    evidence: dict[str, float | int | str | bool | list[str] | None] = {
        "resource_type": "aks_node_pool",
        "cluster_name": cluster_name,
        "node_pool": node_pool,
        "node_sku": node_sku,
        "current_node_count": int(current_node_count),
        "autoscaler_enabled": bool(autoscaler_enabled),
        "autoscaler_min_count": autoscaler_min_count,
        "autoscaler_max_count": autoscaler_max_count,
        "recommended_min_count": None,
        "recommended_max_count": None,
        "autoscaler_action": "none",
        "cpu_p95": round(float(cpu_p95), 2) if cpu_p95 is not None else None,
        "memory_p95": round(float(memory_p95), 2) if memory_p95 is not None else None,
        "cpu_p95_stddev": cpu_p95_stddev,
        "memory_p95_stddev": memory_p95_stddev,
        "variability_score": variability_score,
        "history_days": int(history_days),
        "is_system_pool": bool(is_system_pool),
        "has_kube_system_workloads": bool(has_kube_system_workloads),
        "has_critical_workloads": bool(has_critical_workloads),
        "current_monthly_cost": round(float(current_monthly_cost), 2),
        "estimated_monthly_cost": None,
        "estimated_savings": 0.0,
        "estimated_savings_pct": 0.0,
        "risk_level": "high",
        "confidence": 0.0,
        "reason": "",
        "blocked_by": blocked_by,
    }

    if cpu_p95 is None or memory_p95 is None or history_days < 7:
        blocked_by.append("insufficient_history")
    if is_system_pool:
        blocked_by.append("system_pool")
    if has_kube_system_workloads:
        blocked_by.append("kube_system_workloads")
    if has_critical_workloads:
        blocked_by.append("critical_workloads")
    if cpu_p95 is not None and cpu_p95 > 70.0:
        blocked_by.append("cpu_p95_above_70")
    if memory_p95 is not None and memory_p95 > 80.0:
        blocked_by.append("memory_p95_above_80")

    if blocked_by:
        reason = f"Bloqueado por seguranca: {', '.join(blocked_by)}."
        evidence["reason"] = reason
        return AksAutoscalerRecommendationDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if autoscaler_enabled:
        reason = "Sem recomendacao: autoscaler ja habilitado."
        evidence["reason"] = reason
        return AksAutoscalerRecommendationDecision(
            recommend=False,
            reason=reason,
            risk_level="low",
            confidence=0.0,
            evidence=evidence,
        )

    if current_node_count < 3:
        reason = "Sem recomendacao: node pool com menos de 3 nodes."
        evidence["reason"] = reason
        return AksAutoscalerRecommendationDecision(
            recommend=False,
            reason=reason,
            risk_level="medium",
            confidence=0.0,
            evidence=evidence,
        )

    assert cpu_p95 is not None
    assert memory_p95 is not None

    low_utilization = cpu_p95 <= 45.0 and memory_p95 <= 60.0
    variable_workload = variability_score >= 0.55
    if not (low_utilization or variable_workload):
        reason = "Sem recomendacao: sem sinal de baixa utilizacao ou variabilidade relevante."
        evidence["reason"] = reason
        return AksAutoscalerRecommendationDecision(
            recommend=False,
            reason=reason,
            risk_level="medium",
            confidence=0.0,
            evidence=evidence,
        )

    recommended_min_count = max(2, min(current_node_count - 1, max(2, round(current_node_count * 0.4))))
    recommended_max_count = max(6, current_node_count + 1)

    savings_rate = 0.15
    if cpu_p95 <= 35.0 and memory_p95 <= 50.0:
        savings_rate = 0.25
    elif cpu_p95 <= 40.0 and memory_p95 <= 55.0:
        savings_rate = 0.20
    elif variable_workload:
        savings_rate = 0.18

    estimated_savings = round(float(current_monthly_cost) * savings_rate, 2)
    estimated_monthly_cost = round(float(current_monthly_cost) - estimated_savings, 2)
    estimated_savings_pct = round(savings_rate * 100.0, 2)

    risk_level = "medium"
    if low_utilization and variability_score <= 0.35:
        risk_level = "low"

    confidence = 0.66
    if history_days >= 30:
        confidence += 0.10
    elif history_days >= 14:
        confidence += 0.07
    else:
        confidence += 0.03
    if low_utilization:
        confidence += 0.05
    if variable_workload:
        confidence += 0.03
    if risk_level == "low":
        confidence += 0.03
    confidence = max(0.0, min(1.0, confidence))
    confidence = math.floor(confidence * 100) / 100.0

    reason = (
        f"Node pool elegivel para autoscaler (CPU p95 {cpu_p95:.1f}% / memoria p95 {memory_p95:.1f}%). "
        f"Recomendado min={recommended_min_count}, max={recommended_max_count}."
    )
    evidence["recommended_min_count"] = recommended_min_count
    evidence["recommended_max_count"] = recommended_max_count
    evidence["autoscaler_action"] = "enable"
    evidence["estimated_monthly_cost"] = estimated_monthly_cost
    evidence["estimated_savings"] = estimated_savings
    evidence["estimated_savings_pct"] = estimated_savings_pct
    evidence["risk_level"] = risk_level
    evidence["confidence"] = confidence
    evidence["reason"] = reason

    return AksAutoscalerRecommendationDecision(
        recommend=True,
        reason=reason,
        risk_level=risk_level,
        confidence=confidence,
        evidence=evidence,
    )
