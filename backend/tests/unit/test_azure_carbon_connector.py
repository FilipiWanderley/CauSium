from __future__ import annotations

from app.domains.connectors.azure.client import AzureConnectorClient


def test_normalize_carbon_item_accepts_compact_month_and_maps_fields() -> None:
    item = {
        "yearMonth": "202604",
        "subscriptionId": "sub-1",
        "serviceName": "Compute",
        "resourceGroupName": "rg-app",
        "kgCO2e": 12.34,
    }

    rec = AzureConnectorClient._normalize_carbon_item(item, "sub-fallback")

    assert rec is not None
    assert rec.year_month == "2026-04"
    assert rec.subscription_id == "sub-1"
    assert rec.service == "Compute"
    assert rec.resource_group == "rg-app"
    assert rec.kg_co2e == 12.34


def test_normalize_carbon_item_rejects_invalid_payload() -> None:
    rec = AzureConnectorClient._normalize_carbon_item({"yearMonth": "bad", "kgCO2e": "x"}, "sub")
    assert rec is None
