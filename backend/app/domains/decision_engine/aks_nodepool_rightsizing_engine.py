from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable


@dataclass(frozen=True)
class AksNodePoolRightsizingDecision:
    recommend: bool
    reason: str
    risk_level: str
    confidence: float
    evidence: dict[str, float | int | str | bool | None]


def _metric_kind(metric_name: str) -> str | None:
    name = (metric_name or "").strip().lower()
    if not name:
        return None
    if "allocated" in name and "cpu" in name:
        return "allocated_cpu"
    if "allocated" in name and ("memory" in name or "mem" in name):
        return "allocated_memory"
    if "requested" in name and "cpu" in name:
        return "requested_cpu"
    if "requested" in name and ("memory" in name or "mem" in name):
        return "requested_memory"
    if "node_count" in name or "node count" in name:
        return "node_count"
    if "cpu" in name:
        return "cpu"
    if "memory" in name or "mem" in name:
        return "memory"
    return None


def _compute_window_stats(
    *,
    observations: Iterable[dict],
    now_utc: datetime,
    window_days: int,
) -> tuple[dict[str, float | None], int]:
    start = now_utc - timedelta(days=window_days)
    values: dict[str, list[float]] = {
        "cpu": [],
        "memory": [],
        "allocated_cpu": [],
        "allocated_memory": [],
        "requested_cpu": [],
        "requested_memory": [],
        "node_count": [],
    }
    distinct_dates: set[str] = set()

    for item in observations:
        window_start = item.get("window_start")
        if not isinstance(window_start, datetime):
            continue
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)
        if window_start < start:
            continue

        metric_kind = _metric_kind(str(item.get("metric_name") or ""))
        if metric_kind is None:
            continue

        metric_value = item.get("p95_value")
        if metric_value is None:
            continue
        try:
            metric_f = float(metric_value)
        except Exception:
            continue

        distinct_dates.add(window_start.date().isoformat())
        values[metric_kind].append(metric_f)

    out: dict[str, float | None] = {}
    for key in values:
        out[key] = max(values[key]) if values[key] else None
    return out, len(distinct_dates)


def _to_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def decide_aks_nodepool_rightsizing(
    *,
    cluster_name: str | None,
    node_pool: str | None,
    node_sku: str | None,
    current_node_count: int,
    current_monthly_cost: float,
    observations: Iterable[dict] | None = None,
    cpu_p95: float | None = None,
    memory_p95: float | None = None,
    history_days: int | None = None,
    allocated_cpu: float | None = None,
    allocated_memory: float | None = None,
    requested_cpu: float | None = None,
    requested_memory: float | None = None,
    is_system_pool: bool = False,
    autoscaler_enabled: bool = False,
    autoscaler_min_count: int | None = None,
    autoscaler_max_count: int | None = None,
    has_kube_system_workloads: bool = False,
    has_critical_workloads: bool = False,
    cpu_p95_stddev: float | None = None,
    memory_p95_stddev: float | None = None,
) -> AksNodePoolRightsizingDecision:
    selected_days: int | None = None
    selected_stats: dict[str, float | None] = {}
    computed_history_days = 0
    if cpu_p95 is not None and memory_p95 is not None and history_days is not None:
        computed_history_days = max(0, int(history_days))
        selected_days = min(30, computed_history_days) if computed_history_days > 0 else None
        selected_stats = {
            "cpu": float(cpu_p95),
            "memory": float(memory_p95),
            "allocated_cpu": allocated_cpu,
            "allocated_memory": allocated_memory,
            "requested_cpu": requested_cpu,
            "requested_memory": requested_memory,
            "node_count": float(current_node_count),
        }
    else:
        now_utc = datetime.now(timezone.utc)
        windows = [30, 14, 7]
        all_window_stats: dict[int, tuple[dict[str, float | None], int]] = {}
        for w in windows:
            all_window_stats[w] = _compute_window_stats(
                observations=observations or [],
                now_utc=now_utc,
                window_days=w,
            )

        for w in windows:
            w_stats, w_history = all_window_stats[w]
            if w_history >= w and w_stats.get("cpu") is not None and w_stats.get("memory") is not None:
                selected_days = w
                selected_stats = w_stats
                computed_history_days = w_history
                break
        if selected_days is None:
            for w in windows:
                w_stats, w_history = all_window_stats[w]
                if w_history >= 7 and w_stats.get("cpu") is not None and w_stats.get("memory") is not None:
                    selected_days = min(w, w_history)
                    selected_stats = w_stats
                    computed_history_days = w_history
                    break

        cpu_p95 = selected_stats.get("cpu")
        memory_p95 = selected_stats.get("memory")

    evidence = {
        "resource_type": "aks_node_pool",
        "cluster_name": cluster_name,
        "node_pool": node_pool,
        "current_node_count": int(current_node_count),
        "recommended_node_count": None,
        "node_sku": node_sku,
        "cpu_p95": round(float(cpu_p95), 2) if cpu_p95 is not None else None,
        "memory_p95": round(float(memory_p95), 2) if memory_p95 is not None else None,
        "window_days": selected_days or 0,
        "history_days": computed_history_days,
        "allocated_cpu": selected_stats.get("allocated_cpu"),
        "allocated_memory": selected_stats.get("allocated_memory"),
        "requested_cpu": selected_stats.get("requested_cpu"),
        "requested_memory": selected_stats.get("requested_memory"),
        "is_system_pool": bool(is_system_pool),
        "autoscaler_enabled": bool(autoscaler_enabled),
        "autoscaler_min_count": autoscaler_min_count,
        "autoscaler_max_count": autoscaler_max_count,
        "has_kube_system_workloads": bool(has_kube_system_workloads),
        "has_critical_workloads": bool(has_critical_workloads),
        "cpu_p95_stddev": cpu_p95_stddev,
        "memory_p95_stddev": memory_p95_stddev,
        "current_monthly_cost": round(float(current_monthly_cost), 2),
        "estimated_monthly_cost": None,
        "estimated_savings": 0.0,
        "estimated_savings_pct": 0.0,
        "confidence": 0.0,
        "risk_level": "high",
        "reason": "",
    }

    if selected_days is None:
        reason = "Dados insuficientes: histórico mínimo de 7 dias com CPU e memória p95."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if current_node_count <= 2:
        reason = "Bloqueado por segurança: node pool com 2 nodes ou menos."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if is_system_pool:
        reason = "Bloqueado por segurança: node pool de sistema (crítico)."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if has_kube_system_workloads:
        reason = "Bloqueado por segurança: workloads do namespace kube-system detectados."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if autoscaler_enabled and autoscaler_min_count is not None and current_node_count <= autoscaler_min_count:
        reason = "Bloqueado por segurança: node count atual no limite mínimo do autoscaler."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    assert cpu_p95 is not None
    assert memory_p95 is not None

    if cpu_p95 > 60.0:
        reason = "Bloqueado por segurança: CPU p95 acima de 60%."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if memory_p95 > 70.0:
        reason = "Bloqueado por segurança: memória p95 acima de 70%."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if not (cpu_p95 < 45.0 and memory_p95 < 60.0):
        reason = "Sem recomendação: utilização ainda não está abaixo do limite conservador."
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="medium",
            confidence=0.0,
            evidence=evidence,
        )

    recommended_node_count = current_node_count - 1
    cost_per_node = float(current_monthly_cost) / float(current_node_count)
    estimated_monthly_cost = round(cost_per_node * float(recommended_node_count), 2)
    estimated_savings = round(float(current_monthly_cost) - estimated_monthly_cost, 2)
    estimated_savings_pct = round(
        (estimated_savings / float(current_monthly_cost) * 100.0) if current_monthly_cost > 0 else 0.0,
        2,
    )
    if estimated_savings <= 0:
        reason = "Economia estimada não positiva."
        evidence["recommended_node_count"] = int(recommended_node_count)
        evidence["estimated_monthly_cost"] = estimated_monthly_cost
        evidence["estimated_savings"] = estimated_savings
        evidence["estimated_savings_pct"] = estimated_savings_pct
        evidence["reason"] = reason
        return AksNodePoolRightsizingDecision(
            recommend=False,
            reason=reason,
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    risk_level = "medium"
    if cpu_p95 < 40.0 and memory_p95 < 50.0:
        risk_level = "low"
    elif not (cpu_p95 < 50.0 and memory_p95 < 60.0):
        risk_level = "high"

    requested_pressure = False
    req_cpu = _to_float_or_none(selected_stats.get("requested_cpu"))
    req_mem = _to_float_or_none(selected_stats.get("requested_memory"))
    alloc_cpu = _to_float_or_none(selected_stats.get("allocated_cpu"))
    alloc_mem = _to_float_or_none(selected_stats.get("allocated_memory"))
    cpu_ratio = (req_cpu / alloc_cpu) if req_cpu is not None and alloc_cpu and alloc_cpu > 0 else None
    mem_ratio = (req_mem / alloc_mem) if req_mem is not None and alloc_mem and alloc_mem > 0 else None
    if (cpu_ratio is not None and cpu_ratio >= 0.85) or (mem_ratio is not None and mem_ratio >= 0.85):
        requested_pressure = True
        risk_level = "high"
        evidence["requested_pressure"] = True
    else:
        evidence["requested_pressure"] = False

    if has_critical_workloads and risk_level != "high":
        risk_level = "high"

    confidence = 0.62
    if selected_days >= 30:
        confidence += 0.16
    elif selected_days >= 14:
        confidence += 0.12
    else:
        confidence += 0.06
    if cpu_p95 <= 35.0 and memory_p95 <= 50.0:
        confidence += 0.05
    if requested_pressure:
        confidence -= 0.10
    if has_critical_workloads:
        confidence -= 0.06
    if cpu_p95_stddev is not None and memory_p95_stddev is not None:
        if cpu_p95_stddev <= 6.0 and memory_p95_stddev <= 8.0:
            confidence += 0.04
        elif cpu_p95_stddev >= 15.0 or memory_p95_stddev >= 18.0:
            confidence -= 0.08
    if risk_level == "medium":
        confidence -= 0.01
    if risk_level == "high":
        confidence -= 0.08
    confidence = max(0.0, min(1.0, confidence))
    confidence = math.floor(confidence * 100) / 100.0

    reason = (
        f"Node pool com baixa utilização sustentada por {selected_days} dias "
        f"(CPU p95 {cpu_p95:.1f}% / memória p95 {memory_p95:.1f}%)."
    )
    if requested_pressure:
        reason += " Pressão de requests próxima da capacidade alocada."
    if has_critical_workloads:
        reason += " Workloads críticos detectados."
    evidence["recommended_node_count"] = int(recommended_node_count)
    evidence["estimated_monthly_cost"] = estimated_monthly_cost
    evidence["estimated_savings"] = estimated_savings
    evidence["estimated_savings_pct"] = estimated_savings_pct
    evidence["confidence"] = confidence
    evidence["risk_level"] = risk_level
    evidence["reason"] = reason

    return AksNodePoolRightsizingDecision(
        recommend=True,
        reason=reason,
        risk_level=risk_level,
        confidence=confidence,
        evidence=evidence,
    )
