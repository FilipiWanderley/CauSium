from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domains.decision_engine.vm_rightsizing_engine import decide_vm_rightsizing


def _build_observations(*, cpu: float, memory: float, days: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for d in range(days):
        dt = now - timedelta(days=d)
        rows.append({"metric_name": "Percentage CPU", "p95_value": cpu, "window_start": dt})
        rows.append({"metric_name": "Memory Percentage", "p95_value": memory, "window_start": dt})
    return rows


def test_low_usage_generates_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=1000.0,
        observations=_build_observations(cpu=28.0, memory=45.0, days=14),
    )
    assert decision.recommend is True
    assert decision.evidence["recommended_sku"] == "Standard_D2s_v5"
    assert decision.evidence["estimated_monthly_cost"] == 500.0
    assert decision.evidence["estimated_savings"] == 500.0
    assert decision.evidence["estimated_savings_pct"] == 50.0
    assert decision.evidence["window_days"] == 14
    assert decision.evidence["confidence"] > 0.7


def test_high_cpu_blocks_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=1000.0,
        observations=_build_observations(cpu=65.0, memory=45.0, days=14),
    )
    assert decision.recommend is False
    assert "CPU p95 acima de 60%" in decision.reason


def test_high_memory_blocks_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=1000.0,
        observations=_build_observations(cpu=30.0, memory=75.0, days=14),
    )
    assert decision.recommend is False
    assert "memória p95 acima de 70%" in decision.reason


def test_insufficient_history_blocks_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=1000.0,
        observations=_build_observations(cpu=30.0, memory=40.0, days=5),
    )
    assert decision.recommend is False
    assert "histórico mínimo de 7 dias" in decision.reason


def test_no_smaller_sku_blocks_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D1s_v5",
        current_monthly_cost=1000.0,
        observations=_build_observations(cpu=30.0, memory=40.0, days=14),
    )
    assert decision.recommend is False
    assert "SKU alvo não encontrado" in decision.reason


def test_negative_or_zero_savings_blocks_recommendation():
    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=0.0,
        observations=_build_observations(cpu=30.0, memory=40.0, days=14),
    )
    assert decision.recommend is False
    assert "Economia estimada não positiva" in decision.reason
