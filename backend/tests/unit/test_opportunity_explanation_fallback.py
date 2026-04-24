from __future__ import annotations

from uuid import uuid4

import pytest

from app.domains.decision_engine.explanation_service import OpportunityExplanationService
from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    RiskLevel,
)


class _FakeOpportunity:
    def __init__(self) -> None:
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
        self.resource_id = "/subscriptions/x/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm-a"
        self.resource_name = "vm-a"
        self.sku_name = "Standard_D4s_v5"
        self.machine_family = "D4s"
        self.service = "Virtual Machines"
        self.region = "brazilsouth"
        self.environment = "production"
        self.owner_team = "platform"
        self.account_id = uuid4()


@pytest.mark.asyncio
async def test_explain_opportunity_falls_back_when_llm_fails(monkeypatch):
    svc = OpportunityExplanationService(db=None)  # type: ignore[arg-type]
    fake_opportunity = _FakeOpportunity()

    async def _allow_ai(_org_id):
        return None

    async def _get_opportunity(*, org_id, opportunity_id):
        return fake_opportunity

    async def _get_usage_observations(*, org_id, account_id, resource_id):
        return [{"metric_name": "Percentage CPU", "p95_value": 28.0}]

    def _get_recent_events(*, org_id, account_id, resource_id):
        return []

    async def _broken_llm(context):
        raise RuntimeError("llm down")

    monkeypatch.setattr(svc, "_require_ai_feature", _allow_ai)
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
    assert out.confidence >= 0.0
    assert out.debug is not None
    assert out.debug.get("llm_error") == "llm down"
