from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domains.decision_engine.explanation_service import OpportunityExplanationService
from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    OptimizationOpportunity,
    RiskLevel,
)
from app.domains.decision_engine.service import DecisionEngineService
from app.domains.intel.models import UsageObservation


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _ExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _ScalarResult(self._items)


@dataclass
class _UsageRow:
    metric_name: str
    p95_value: float
    window_start: datetime


class _FakeDB:
    def __init__(self, usage_rows: list[_UsageRow]):
        self.usage_rows = usage_rows
        self.opportunities: list[OptimizationOpportunity] = []

    async def execute(self, query):
        entity = None
        if getattr(query, "column_descriptions", None):
            entity = query.column_descriptions[0].get("entity")
        if entity is UsageObservation:
            return _ExecuteResult(self.usage_rows)
        if entity is OptimizationOpportunity:
            return _ExecuteResult(self.opportunities)
        return _ExecuteResult([])

    def add(self, item):
        if isinstance(item, OptimizationOpportunity):
            self.opportunities.append(item)

    async def flush(self):
        return None


def _build_usage_rows(*, cpu: float, memory: float, days: int) -> list[_UsageRow]:
    now = datetime.now(timezone.utc)
    rows: list[_UsageRow] = []
    for d in range(days):
        dt = now - timedelta(days=d)
        rows.append(_UsageRow(metric_name="Percentage CPU", p95_value=cpu, window_start=dt))
        rows.append(_UsageRow(metric_name="Memory Percentage", p95_value=memory, window_start=dt))
    return rows


def _mock_cost_rows():
    return [
        {
            "service": "Virtual Machines",
            "owner_team": "platform",
            "environment": "production",
            "region": "eastus",
            "monthly_cost": 1000.0,
            "resource_id": "vm-test-01",
            "resource_name": "vm-test-01",
            "sku_name": "Standard_D4s_v5",
            "data_points": 14,
        }
    ]


@pytest.mark.asyncio
async def test_e2e_rightsizing_positive_flow(monkeypatch):
    org_id = uuid4()
    account_id = uuid4()
    db = _FakeDB(_build_usage_rows(cpu=28.0, memory=45.0, days=14))
    svc = DecisionEngineService(db)  # type: ignore[arg-type]

    import app.core.clickhouse as clickhouse_module

    monkeypatch.setattr(clickhouse_module, "execute_query", lambda query, params: _mock_cost_rows())
    out = await svc.generate_opportunities_for_account(org_id=org_id, account_id=account_id)

    assert len(out) == 1
    op = out[0]
    assert op.category == OpportunityCategory.RIGHTSIZING
    assert op.resource_id == "vm-test-01"
    assert op.sku_name == "Standard_D4s_v5"
    assert op.estimated_monthly_savings_usd > 0
    assert op.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert op.decision_evidence is not None
    assert op.decision_evidence["recommended_sku"] == "Standard_D2s_v5"
    assert op.decision_evidence["cpu_p95"] == 28.0
    assert op.decision_evidence["memory_p95"] == 45.0
    assert op.decision_evidence["window_days"] == 14
    assert op.decision_evidence["estimated_savings"] > 0
    assert op.decision_evidence["estimated_savings_pct"] > 0
    assert op.decision_evidence["confidence"] > 0.7


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cpu,memory,days,reason_part",
    [
        (75.0, 45.0, 14, "CPU p95 acima de 60%"),
        (30.0, 80.0, 14, "memória p95 acima de 70%"),
        (30.0, 45.0, 5, "histórico mínimo de 7 dias"),
    ],
)
async def test_e2e_rightsizing_negative_blocks(monkeypatch, cpu, memory, days, reason_part):
    org_id = uuid4()
    account_id = uuid4()
    db = _FakeDB(_build_usage_rows(cpu=cpu, memory=memory, days=days))
    svc = DecisionEngineService(db)  # type: ignore[arg-type]

    import app.core.clickhouse as clickhouse_module

    monkeypatch.setattr(clickhouse_module, "execute_query", lambda query, params: _mock_cost_rows())
    out = await svc.generate_opportunities_for_account(org_id=org_id, account_id=account_id)

    assert out == []

    # Validate exact decision behavior from the engine to guarantee block reason.
    from app.domains.decision_engine.vm_rightsizing_engine import decide_vm_rightsizing

    decision = decide_vm_rightsizing(
        current_sku="Standard_D4s_v5",
        current_monthly_cost=1000.0,
        observations=[
            {"metric_name": row.metric_name, "p95_value": row.p95_value, "window_start": row.window_start}
            for row in db.usage_rows
        ],
    )
    assert decision.recommend is False
    assert reason_part in decision.reason


class _FakeOpportunity:
    def __init__(self):
        self.id = uuid4()
        self.title = "Rightsize VM"
        self.description = "desc"
        self.category = OpportunityCategory.RIGHTSIZING
        self.status = OpportunityStatus.OPEN
        self.estimated_monthly_savings_usd = 420.0
        self.estimated_annual_savings_usd = 5040.0
        self.composite_score = 82.0
        self.risk_level = RiskLevel.MEDIUM
        self.effort_level = EffortLevel.MEDIUM
        self.resource_id = "vm-test-01"
        self.resource_name = "vm-test-01"
        self.sku_name = "Standard_D4s_v5"
        self.machine_family = "D4s"
        self.service = "Virtual Machines"
        self.region = "eastus"
        self.environment = "production"
        self.owner_team = "platform"
        self.account_id = uuid4()
        self.decision_evidence = {}


@pytest.mark.asyncio
async def test_e2e_explain_fallback(monkeypatch):
    svc = OpportunityExplanationService(db=None)  # type: ignore[arg-type]
    fake_opportunity = _FakeOpportunity()

    async def _allow_ai(_org_id):
        return None

    async def _fake_get_org_plan(_org_id):
        return "enterprise"

    async def _get_opportunity(*, org_id, opportunity_id):
        return fake_opportunity

    async def _get_usage_observations(*, org_id, account_id, resource_id):
        return [
            {"metric_name": "Percentage CPU", "p95_value": 28.0},
            {"metric_name": "Memory Percentage", "p95_value": 45.0},
        ]

    def _get_recent_events(*, org_id, account_id, resource_id):
        return []

    async def _broken_llm(context):
        raise RuntimeError("llm down")

    monkeypatch.setattr(svc, "_require_ai_feature", _allow_ai)
    monkeypatch.setattr(svc, "_get_org_plan", _fake_get_org_plan)
    monkeypatch.setattr(svc, "_get_opportunity", _get_opportunity)
    monkeypatch.setattr(svc, "_get_usage_observations", _get_usage_observations)
    monkeypatch.setattr(svc, "_get_recent_events", _get_recent_events)
    monkeypatch.setattr(svc.llm, "explain_recommendation", _broken_llm)

    out = await svc.explain_opportunity(
        org_id=uuid4(),
        opportunity_id=fake_opportunity.id,
        language="pt",
    )
    assert out.summary
    assert out.debug is not None
    assert out.debug.get("llm_error") == "llm down"
