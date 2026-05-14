from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.domains.connectors.azure.client import AzureConnectorClient
from app.domains.connectors.azure.mock import AzureMockClient


def test_parse_blob_cost_csv_normalizes_and_filters_rows() -> None:
    csv_payload = """Date,SubscriptionId,ServiceName,ResourceId,ResourceGroup,ResourceLocation,PreTaxCost,UsageQuantity,UnitOfMeasure,Currency,Tags
2026-04-10,sub-001,Virtual Machines,/subscriptions/sub-001/resourceGroups/rg-a/providers/Microsoft.Compute/virtualMachines/vm-a,rg-a,eastus,12.50,8,hours,USD,"{""env"":""production"",""team"":""platform""}"
2026-04-10,sub-other,Azure Storage,/subscriptions/sub-other/resourceGroups/rg-b/providers/Microsoft.Storage/storageAccounts/stg1,rg-b,eastus2,2.00,1,GB,USD,"{}"
2026-04-15,sub-001,Azure SQL,/subscriptions/sub-001/resourceGroups/rg-c/providers/Microsoft.Sql/servers/sql1,rg-c,westeurope,4.00,1,hours,USD,"{}"
"""

    rows = AzureConnectorClient._parse_blob_cost_csv(
        csv_payload,
        subscription_id="sub-001",
        start=date(2026, 4, 1),
        end=date(2026, 4, 12),
    )

    assert len(rows) == 1
    rec = rows[0]
    assert rec.subscription_id == "sub-001"
    assert rec.service == "Virtual Machines"
    assert rec.environment == "production"
    assert rec.owner_team == "platform"
    assert rec.cost_usd == 12.5
    assert rec.usage_quantity == 8.0


def test_blob_checkpoint_key_is_stable() -> None:
    key = AzureConnectorClient._build_blob_checkpoint_key("exports/cost.csv", '"etag-1"')
    assert key == 'exports/cost.csv::"etag-1"'


@pytest.mark.asyncio
async def test_fetch_costs_prefers_blob_when_available(monkeypatch) -> None:
    client = AzureConnectorClient(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
        storage_account_url="https://example.blob.core.windows.net",
        cost_export_container="exports",
        cost_export_prefix="cost/",
    )

    async def fake_blob(subscription_id: str, start: date, end: date, *, checkpoint_keys=None):
        row = AzureConnectorClient._normalize_blob_cost_row(
            {
                "Date": "2026-04-10",
                "SubscriptionId": subscription_id,
                "ServiceName": "Azure Storage",
                "PreTaxCost": "3.25",
                "UsageQuantity": "10",
                "UnitOfMeasure": "GB",
                "Currency": "USD",
            },
            fallback_subscription_id=subscription_id,
            start=start,
            end=end,
        )
        return ([row] if row else [], [])

    async def fake_api(subscription_id: str, start: date, end: date):
        raise AssertionError("Cost Management API should not be called when blob data exists")

    monkeypatch.setattr(client, "_fetch_costs_from_blob_exports", fake_blob)
    monkeypatch.setattr(client, "_fetch_costs_from_cost_management_api", fake_api)

    rows = await client.fetch_costs("sub-001", date(2026, 4, 1), date(2026, 4, 30))
    assert len(rows) == 1
    assert rows[0].service == "Azure Storage"


@pytest.mark.asyncio
async def test_fetch_costs_falls_back_to_api_when_blob_is_empty(monkeypatch) -> None:
    client = AzureConnectorClient(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
        storage_account_url="https://example.blob.core.windows.net",
        cost_export_container="exports",
    )

    async def fake_blob(subscription_id: str, start: date, end: date, *, checkpoint_keys=None):
        return [], []

    async def fake_api(subscription_id: str, start: date, end: date):
        row = AzureConnectorClient._normalize_blob_cost_row(
            {
                "Date": "2026-04-10",
                "SubscriptionId": subscription_id,
                "ServiceName": "Compute",
                "PreTaxCost": "9.99",
                "UsageQuantity": "2",
            },
            fallback_subscription_id=subscription_id,
            start=start,
            end=end,
        )
        return [row] if row else []

    monkeypatch.setattr(client, "_fetch_costs_from_blob_exports", fake_blob)
    monkeypatch.setattr(client, "_fetch_costs_from_cost_management_api", fake_api)

    rows = await client.fetch_costs("sub-002", date(2026, 4, 1), date(2026, 4, 30))
    assert len(rows) == 1
    assert rows[0].subscription_id == "sub-002"


@pytest.mark.asyncio
async def test_fetch_costs_passes_checkpoint_keys_to_blob_fetch(monkeypatch) -> None:
    client = AzureConnectorClient(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
        storage_account_url="https://example.blob.core.windows.net",
        cost_export_container="exports",
    )

    observed: dict[str, set[str] | None] = {"keys": None}

    async def fake_blob(subscription_id: str, start: date, end: date, *, checkpoint_keys=None):
        observed["keys"] = checkpoint_keys
        return [], []

    async def fake_api(subscription_id: str, start: date, end: date):
        return []

    monkeypatch.setattr(client, "_fetch_costs_from_blob_exports", fake_blob)
    monkeypatch.setattr(client, "_fetch_costs_from_cost_management_api", fake_api)

    keys = {"exports/cost-1.csv::etag-1"}
    await client.fetch_costs("sub-003", date(2026, 4, 1), date(2026, 4, 30), checkpoint_keys=keys)
    assert observed["keys"] == keys


def test_from_account_uses_mock_in_development_without_credentials(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        connector = AzureConnectorClient.from_account(SimpleNamespace(id="acc-dev"), creds=None)
    finally:
        get_settings.cache_clear()
    assert isinstance(connector, AzureMockClient)


def test_from_account_rejects_mock_fallback_in_production_without_credentials(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="Azure credentials are required in production"):
            AzureConnectorClient.from_account(SimpleNamespace(id="acc-prod"), creds=None)
    finally:
        get_settings.cache_clear()


def test_parse_blob_cost_parquet_normalizes_and_filters_rows() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    pa = pyarrow
    table = pa.table(
        {
            "Date": ["2026-04-10", "2026-04-10", "2026-04-20"],
            "SubscriptionId": ["sub-001", "sub-001", "sub-001"],
            "ServiceName": ["Virtual Machines", "Azure Storage", "Azure SQL"],
            "ResourceId": ["/subs/sub-001/rg/vm-a", "/subs/sub-001/rg/stg1", "/subs/sub-001/rg/sql1"],
            "ResourceGroup": ["rg-a", "rg-b", "rg-c"],
            "ResourceLocation": ["eastus", "eastus2", "westeurope"],
            "PreTaxCost": ["12.50", "2.00", "4.00"],
            "UsageQuantity": ["8", "1", "1"],
            "UnitOfMeasure": ["hours", "GB", "hours"],
            "Currency": ["USD", "USD", "USD"],
            "Tags": ['{"env":"production","team":"platform"}', "{}", "{}"],
        }
    )

    import io
    buf = io.BytesIO()
    pq.write_table(table, buf)
    raw_bytes = buf.getvalue()

    rows = AzureConnectorClient._parse_blob_cost_parquet(
        raw_bytes,
        subscription_id="sub-001",
        start=date(2026, 4, 1),
        end=date(2026, 4, 12),
    )

    assert len(rows) == 2
    rec = rows[0]
    assert rec.subscription_id == "sub-001"
    assert rec.service == "Virtual Machines"
    assert rec.environment == "production"
    assert rec.owner_team == "platform"
    assert rec.cost_usd == 12.5
    assert rec.usage_quantity == 8.0


def test_parse_blob_cost_parquet_handles_date_typed_columns() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    pa = pyarrow
    table = pa.table(
        {
            "Date": pa.array([date(2026, 4, 10)], type=pa.date32()),
            "SubscriptionId": ["sub-001"],
            "ServiceName": ["Compute"],
            "PreTaxCost": [7.25],
            "UsageQuantity": [3.0],
            "Currency": ["USD"],
        }
    )

    import io
    buf = io.BytesIO()
    pq.write_table(table, buf)
    raw_bytes = buf.getvalue()

    rows = AzureConnectorClient._parse_blob_cost_parquet(
        raw_bytes,
        subscription_id="sub-001",
        start=date(2026, 4, 1),
        end=date(2026, 4, 30),
    )

    assert len(rows) == 1
    assert rows[0].cost_usd == 7.25
    assert rows[0].date == date(2026, 4, 10)


def test_parse_blob_cost_parquet_returns_empty_on_invalid_bytes() -> None:
    rows = AzureConnectorClient._parse_blob_cost_parquet(
        b"not a parquet file",
        subscription_id="sub-001",
        start=date(2026, 4, 1),
        end=date(2026, 4, 30),
    )
    assert rows == []
