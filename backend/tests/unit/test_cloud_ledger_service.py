from __future__ import annotations

from uuid import uuid4

from app.domains.cloud_ledger.service import CloudLedgerService


def test_get_detailed_costs_applies_combined_filters_and_paginates(monkeypatch):
    org_id = uuid4()

    def fake_execute_query(query: str, parameters: dict | None = None):
        assert parameters is not None
        assert parameters["org_id"] == str(org_id)
        assert parameters["service"] == "Compute"
        assert parameters["provider"] == "azure"
        assert parameters["owner_team"] == "platform"
        assert parameters["limit"] == 20
        assert parameters["offset"] == 20
        if "count() AS total" in query:
            return [{"total": 21}]
        return [
            {
                "date": "2026-04-10",
                "account_id": "acc-1",
                "provider": "azure",
                "subscription_id": "sub-1",
                "service": "Compute",
                "resource_id": "vm-1",
                "resource_name": "vm-prod-1",
                "region": "eastus",
                "environment": "prod",
                "owner_team": "platform",
                "cost_usd": 41.25,
                "usage_quantity": 12.0,
                "usage_unit": "hours",
                "currency": "USD",
            }
        ]

    monkeypatch.setattr("app.domains.cloud_ledger.service.execute_query", fake_execute_query)

    service = CloudLedgerService(db=None)
    rows, total = service.get_detailed_costs(
        org_id,
        days=30,
        service="Compute",
        provider="azure",
        owner_team="platform",
        limit=20,
        offset=20,
    )

    assert total == 21
    assert len(rows) == 1
    assert rows[0].resource_id == "vm-1"
    assert rows[0].cost_usd == 41.25


def test_get_detailed_costs_returns_empty_when_query_fails(monkeypatch):
    def fake_execute_query(query: str, parameters: dict | None = None):
        raise RuntimeError("clickhouse unavailable")

    monkeypatch.setattr("app.domains.cloud_ledger.service.execute_query", fake_execute_query)

    service = CloudLedgerService(db=None)
    rows, total = service.get_detailed_costs(uuid4(), limit=20, offset=0)

    assert rows == []
    assert total == 0


def test_get_reservation_efficiency_recommends_exchange_for_low_utilization(monkeypatch):
    org_id = uuid4()

    def fake_execute_query(query: str, parameters: dict | None = None):
        if "FROM cost_facts" in query:
            return [
                {
                    "service": "Virtual Machines",
                    "resource_name": "Standard_B2s",
                    "tags": {"family": "Standard_B2s"},
                    "compute_cost_usd": 30.0,
                    "reserved_cost_usd": 100.0,
                }
            ]
        if "FROM resource_inventory" in query:
            return [{"sku_name": "Standard_B2s", "resource_count": 3}]
        return []

    monkeypatch.setattr("app.domains.cloud_ledger.service.execute_query", fake_execute_query)

    service = CloudLedgerService(db=None)
    result = service.get_reservation_efficiency(org_id, days=30)

    assert result.total_families == 1
    assert result.avg_utilization_pct == 30.0
    assert result.families[0].recommended_action == "exchange_reservation"
    assert result.families[0].exchange_candidate is True


def test_get_reservation_efficiency_recommends_schedule_stop_for_tiny_workload(monkeypatch):
    org_id = uuid4()

    def fake_execute_query(query: str, parameters: dict | None = None):
        if "FROM cost_facts" in query:
            return [
                {
                    "service": "Virtual Machines",
                    "resource_name": "B2s",
                    "tags": {"vm_size": "Standard_B2s"},
                    "compute_cost_usd": 15.0,
                    "reserved_cost_usd": 100.0,
                }
            ]
        if "FROM resource_inventory" in query:
            return [{"sku_name": "Standard_B2s", "resource_count": 1}]
        return []

    monkeypatch.setattr("app.domains.cloud_ledger.service.execute_query", fake_execute_query)

    service = CloudLedgerService(db=None)
    result = service.get_reservation_efficiency(org_id, days=30)

    assert result.total_families == 1
    assert result.families[0].recommended_action == "schedule_stop"
    assert result.total_waste_cost_usd == 85.0
