from __future__ import annotations

from uuid import uuid4

import pytest

from app.domains.decision_engine.models import OpportunityCategory, OptimizationOpportunity, RiskLevel
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
            "autoscaler_enabled": True,
            "autoscaler_min_count": 3,
            "autoscaler_max_count": 10,
            "has_kube_system_workloads": False,
            "has_critical_workloads": False,
            "cpu_p95_stddev": 4.2,
            "memory_p95_stddev": 5.1,
        }
    ]


@pytest.mark.asyncio
async def test_e2e_aks_nodepool_rightsizing_with_normalized_candidates(monkeypatch):
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

    assert len(out) == 1
    op = out[0]
    assert op.category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING
    assert op.resource_id == (
        "aks:/subscriptions/sub-1/resourcegroups/rg-aks/providers/"
        "microsoft.containerservice/managedclusters/prod-aks:apps"
    )
    assert op.resource_name == "prod-aks/apps"
    assert op.sku_name == "Standard_D4s_v5"
    assert op.estimated_monthly_savings_usd > 0
    assert op.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert op.decision_evidence is not None
    assert op.decision_evidence["resource_type"] == "aks_node_pool"
    assert op.decision_evidence["cluster_name"] == "prod-aks"
    assert op.decision_evidence["node_pool"] == "apps"
    assert op.decision_evidence["current_node_count"] == 5
    assert op.decision_evidence["recommended_node_count"] == 4
    assert op.decision_evidence["node_sku"] == "Standard_D4s_v5"
    assert op.decision_evidence["cpu_p95"] == 32.0
    assert op.decision_evidence["memory_p95"] == 48.0
    assert op.decision_evidence["is_system_pool"] is False
    assert op.decision_evidence["autoscaler_enabled"] is True
    assert op.decision_evidence["autoscaler_min_count"] == 3
    assert op.decision_evidence["has_kube_system_workloads"] is False
    assert op.decision_evidence["estimated_savings"] > 0
    assert op.decision_evidence["estimated_savings_pct"] > 0
    assert op.decision_evidence["confidence"] > 0
    assert op.decision_evidence["recommended_strategy"] == "nodepool_rightsizing"
    assert op.decision_evidence["alternative_strategy"] is None
    assert op.decision_evidence["confidence_boosted"] is False
