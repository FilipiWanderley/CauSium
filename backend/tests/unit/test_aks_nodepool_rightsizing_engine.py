from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domains.decision_engine.aks_nodepool_rightsizing_engine import (
    decide_aks_nodepool_rightsizing,
)


def _build_observations(
    *,
    cpu: float,
    memory: float,
    days: int,
    allocated_cpu: float = 0.0,
    allocated_memory: float = 0.0,
    requested_cpu: float = 0.0,
    requested_memory: float = 0.0,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for d in range(days):
        dt = now - timedelta(days=d)
        rows.append({"metric_name": "Percentage CPU", "p95_value": cpu, "window_start": dt})
        rows.append({"metric_name": "Memory Percentage", "p95_value": memory, "window_start": dt})
        rows.append({"metric_name": "Allocated CPU", "p95_value": allocated_cpu, "window_start": dt})
        rows.append({"metric_name": "Allocated Memory", "p95_value": allocated_memory, "window_start": dt})
        rows.append({"metric_name": "Requested CPU", "p95_value": requested_cpu, "window_start": dt})
        rows.append({"metric_name": "Requested Memory", "p95_value": requested_memory, "window_start": dt})
    return rows


def test_low_usage_reduces_one_node():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=32.0, memory=48.0, days=14),
    )
    assert decision.recommend is True
    assert decision.evidence["resource_type"] == "aks_node_pool"
    assert decision.evidence["recommended_node_count"] == 4
    assert decision.evidence["estimated_monthly_cost"] == 840.0
    assert decision.evidence["estimated_savings"] == 210.0
    assert decision.evidence["estimated_savings_pct"] == 20.0
    assert decision.evidence["risk_level"] in ("low", "medium")


def test_blocks_when_node_count_is_too_low():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=2,
        current_monthly_cost=500.0,
        observations=_build_observations(cpu=25.0, memory=35.0, days=14),
    )
    assert decision.recommend is False
    assert "2 nodes ou menos" in decision.reason


def test_blocks_high_cpu():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=62.0, memory=48.0, days=14),
    )
    assert decision.recommend is False
    assert "CPU p95 acima de 60%" in decision.reason


def test_blocks_high_memory():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=40.0, memory=72.0, days=14),
    )
    assert decision.recommend is False
    assert "memória p95 acima de 70%" in decision.reason


def test_blocks_when_history_is_insufficient():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=32.0, memory=48.0, days=5),
    )
    assert decision.recommend is False
    assert "histórico mínimo de 7 dias" in decision.reason


def test_blocks_system_pool_by_name():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="systempool",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=20.0, memory=30.0, days=14),
        is_system_pool=True,
    )
    assert decision.recommend is False
    assert "node pool de sistema" in decision.reason


def test_blocks_when_autoscaler_at_min_count():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=3,
        current_monthly_cost=900.0,
        observations=_build_observations(cpu=32.0, memory=48.0, days=14),
        autoscaler_enabled=True,
        autoscaler_min_count=3,
        autoscaler_max_count=10,
    )
    assert decision.recommend is False
    assert "limite mínimo do autoscaler" in decision.reason


def test_blocks_when_kube_system_workloads_are_present():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        observations=_build_observations(cpu=32.0, memory=48.0, days=14),
        has_kube_system_workloads=True,
    )
    assert decision.recommend is False
    assert "kube-system" in decision.reason


def test_requested_pressure_sets_high_risk():
    decision = decide_aks_nodepool_rightsizing(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1050.0,
        cpu_p95=32.0,
        memory_p95=48.0,
        history_days=14,
        allocated_cpu=20.0,
        requested_cpu=19.0,
        allocated_memory=40.0,
        requested_memory=35.0,
    )
    assert decision.recommend is True
    assert decision.risk_level == "high"
    assert decision.evidence["requested_pressure"] is True
