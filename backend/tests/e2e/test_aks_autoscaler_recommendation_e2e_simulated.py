from __future__ import annotations

from uuid import uuid4

import pytest

from app.domains.decision_engine.models import OpportunityCategory, OptimizationOpportunity
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


class _FakeDB:
    def __init__(self):
        self.opportunities: list[OptimizationOpportunity] = []

    async def execute(self, query):
        entity = None
        if getattr(query, "column_descriptions", None):
            entity = query.column_descriptions[0].get("entity")
        if entity is UsageObservation:
            return _ExecuteResult([])
        if entity is OptimizationOpportunity:
            return _ExecuteResult(self.opportunities)
        return _ExecuteResult([])

    def add(self, item):
        if isinstance(item, OptimizationOpportunity):
            self.opportunities.append(item)

    async def flush(self):
        return None


def _mock_aks_candidates():
    return [
        {
            "cluster_id": "/subscriptions/sub-1/resourceGroups/rg-aks/providers/Microsoft.ContainerService/managedClusters/prod-aks",
            "cluster_name": "prod-aks",
            "node_pool_name": "apps",
            "node_count": 5,
            "node_sku": "Standard_D4s_v5",
            "region": "eastus",
            "cpu_p95": 32.0,
            "memory_p95": 48.0,
            "monthly_cost": 1050.0,
            "history_days": 14,
            "owner_team": "platform",
            "environment": "production",
            "allocated_cpu": 18.0,
            "allocated_memory": 30.0,
            "requested_cpu": 12.0,
            "requested_memory": 22.0,
            "is_system_pool": False,
            "autoscaler_enabled": False,
            "autoscaler_min_count": None,
            "autoscaler_max_count": None,
            "has_kube_system_workloads": False,
            "has_critical_workloads": False,
            "cpu_p95_stddev": 8.0,
            "memory_p95_stddev": 10.0,
        }
    ]


@pytest.mark.asyncio
async def test_e2e_aks_rightsizing_and_autoscaler_can_coexist_without_same_category_duplicates(monkeypatch):
    org_id = uuid4()
    account_id = uuid4()
    db = _FakeDB()
    svc = DecisionEngineService(db)  # type: ignore[arg-type]

    import app.core.clickhouse as clickhouse_module

    def _fake_execute_query(query, params):
        if "AKS_NODEPOOL_CANDIDATES" in query:
            return _mock_aks_candidates()
        return []

    monkeypatch.setattr(clickhouse_module, "execute_query", _fake_execute_query)
    out = await svc.generate_opportunities_for_account(org_id=org_id, account_id=account_id)

    assert len(out) == 2
    category_and_resource = {(op.category.value, op.resource_id) for op in out}
    assert len(category_and_resource) == 2
    assert any(op.category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING for op in out)
    assert any(op.category == OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION for op in out)

    autoscaler = next(op for op in out if op.category == OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION)
    assert autoscaler.decision_evidence is not None
    assert autoscaler.decision_evidence["autoscaler_enabled"] is False
    assert autoscaler.decision_evidence["recommended_min_count"] == 2
    assert autoscaler.decision_evidence["recommended_max_count"] == 6
    assert 15.0 <= float(autoscaler.decision_evidence["estimated_savings_pct"]) <= 25.0
