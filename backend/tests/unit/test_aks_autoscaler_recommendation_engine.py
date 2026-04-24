from __future__ import annotations

from app.domains.decision_engine.aks_autoscaler_recommendation_engine import (
    decide_aks_autoscaler_recommendation,
)


def test_recommends_enable_autoscaler_with_conservative_savings():
    decision = decide_aks_autoscaler_recommendation(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1000.0,
        cpu_p95=34.0,
        memory_p95=49.0,
        history_days=14,
        autoscaler_enabled=False,
        autoscaler_min_count=None,
        autoscaler_max_count=None,
        cpu_p95_stddev=5.0,
        memory_p95_stddev=6.0,
    )
    assert decision.recommend is True
    assert decision.evidence["autoscaler_action"] == "enable"
    assert decision.evidence["recommended_min_count"] == 2
    assert decision.evidence["recommended_max_count"] == 6
    assert 15.0 <= float(decision.evidence["estimated_savings_pct"] or 0.0) <= 25.0


def test_blocks_on_cpu_hard_stop_above_70():
    decision = decide_aks_autoscaler_recommendation(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1000.0,
        cpu_p95=71.0,
        memory_p95=40.0,
        history_days=14,
        autoscaler_enabled=False,
        autoscaler_min_count=None,
        autoscaler_max_count=None,
    )
    assert decision.recommend is False
    assert "cpu_p95_above_70" in (decision.evidence.get("blocked_by") or [])


def test_blocks_on_memory_hard_stop_above_80():
    decision = decide_aks_autoscaler_recommendation(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1000.0,
        cpu_p95=40.0,
        memory_p95=81.0,
        history_days=14,
        autoscaler_enabled=False,
        autoscaler_min_count=None,
        autoscaler_max_count=None,
    )
    assert decision.recommend is False
    assert "memory_p95_above_80" in (decision.evidence.get("blocked_by") or [])


def test_blocks_on_security_and_history_constraints():
    decision = decide_aks_autoscaler_recommendation(
        cluster_name="prod-aks",
        node_pool="systempool",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1000.0,
        cpu_p95=35.0,
        memory_p95=45.0,
        history_days=3,
        autoscaler_enabled=False,
        autoscaler_min_count=None,
        autoscaler_max_count=None,
        is_system_pool=True,
        has_kube_system_workloads=True,
        has_critical_workloads=True,
    )
    assert decision.recommend is False
    blocked = set(decision.evidence.get("blocked_by") or [])
    assert "insufficient_history" in blocked
    assert "system_pool" in blocked
    assert "kube_system_workloads" in blocked
    assert "critical_workloads" in blocked


def test_skips_when_autoscaler_is_already_enabled():
    decision = decide_aks_autoscaler_recommendation(
        cluster_name="prod-aks",
        node_pool="apps",
        node_sku="Standard_D4s_v5",
        current_node_count=5,
        current_monthly_cost=1000.0,
        cpu_p95=35.0,
        memory_p95=45.0,
        history_days=14,
        autoscaler_enabled=True,
        autoscaler_min_count=2,
        autoscaler_max_count=6,
    )
    assert decision.recommend is False
    assert "ja habilitado" in decision.reason
