from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.domains.cloud_ledger.service import CloudLedgerService
from app.domains.connectors.base import (
    CanonicalRecommendationRecord,
    CanonicalResourceRecord,
    CanonicalUsageRecord,
)


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


def test_get_reservation_efficiency_uses_advisor_signals_for_exchange_and_renewal(monkeypatch):
    org_id = uuid4()

    def fake_execute_query(query: str, parameters: dict | None = None):
        if "FROM cost_facts" in query:
            return [
                {
                    "service": "Virtual Machines",
                    "resource_name": "Standard_D4s_v5",
                    "tags": {"family": "Standard_D4s_v5"},
                    "compute_cost_usd": 40.0,
                    "reserved_cost_usd": 100.0,
                }
            ]
        if "FROM resource_inventory" in query:
            return [{"sku_name": "Standard_D4s_v5", "resource_count": 2}]
        if "FROM recommendation_facts" in query:
            return [
                {
                    "short_description": "Reservation expires in 30 days. Consider exchange for better utilization.",
                    "recommendation_type_id": "reservation-exchange",
                    "service": "Virtual Machines D4s_v5",
                    "estimated_savings_usd": 120.0,
                }
            ]
        return []

    monkeypatch.setattr("app.domains.cloud_ledger.service.execute_query", fake_execute_query)

    service = CloudLedgerService(db=None)
    result = service.get_reservation_efficiency(org_id, days=30)

    assert result.total_families == 1
    assert result.families[0].family == "D4s"
    assert result.families[0].exchange_eligible is True
    assert result.families[0].renewal_window_days == 30
    assert result.families[0].recommended_action == "do_not_renew"
    assert result.families[0].action_priority >= 4


@pytest.mark.asyncio
async def test_provider_advanced_ingestion_works_for_non_azure_clients(monkeypatch):
    inserted_tables: list[str] = []

    def fake_insert_rows(table: str, rows: list[dict]):
        assert rows
        inserted_tables.append(table)

    monkeypatch.setattr("app.domains.cloud_ledger.service.insert_rows", fake_insert_rows)

    class DummyClient:
        async def fetch_recommendations(self, subscription_id: str):
            return [
                CanonicalRecommendationRecord(
                    recommendation_id="r-1",
                    provider="aws",
                    subscription_id=subscription_id,
                    category="Cost",
                    impact="High",
                    resource_id="i-123",
                    resource_name="i-123",
                    resource_group="",
                    service="EC2",
                    short_description="Right size instance",
                    recommendation_type_id="rightsize",
                    estimated_savings_usd=25.0,
                    fetched_at=datetime.now(timezone.utc),
                )
            ]

        async def fetch_inventory(self, subscription_id: str):
            return [
                CanonicalResourceRecord(
                    resource_id="arn:aws:ec2:us-east-1:123:instance/i-123",
                    provider="aws",
                    subscription_id=subscription_id,
                    name="i-123",
                    resource_type="ec2:instance",
                    resource_group="",
                    location="us-east-1",
                    environment="production",
                    owner_team="platform",
                    sku_name="t3.medium",
                    sku_tier="",
                    provisioning_state="running",
                    tags={"team": "platform"},
                    fetched_at=datetime.now(timezone.utc),
                )
            ]

        async def fetch_usage_metrics(self, subscription_id: str, start: date, end: date):
            return [
                CanonicalUsageRecord(
                    date=start,
                    provider="aws",
                    subscription_id=subscription_id,
                    service="AmazonEC2",
                    resource_id="i-123",
                    metric_name="CPUUtilization",
                    metric_value=12.5,
                    metric_unit="Percent",
                    region="us-east-1",
                    environment="production",
                )
            ]

    service = CloudLedgerService(db=None)
    org_id = uuid4()
    account_id = uuid4()
    subscription_id = "123456789012"

    recs = await service._ingest_provider_recommendations(DummyClient(), org_id, account_id, subscription_id)
    inv = await service._ingest_provider_inventory(DummyClient(), org_id, account_id, subscription_id)
    usage = await service._ingest_provider_usage_metrics(
        DummyClient(), org_id, account_id, subscription_id, date(2026, 1, 1), date(2026, 1, 2)
    )

    assert recs == 1
    assert inv == 1
    assert usage == 1
    assert inserted_tables == ["recommendation_facts", "resource_inventory", "usage_facts"]
