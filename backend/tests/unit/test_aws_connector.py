from __future__ import annotations

from datetime import date

import pytest

from app.domains.connectors.aws.client import AwsConnectorClient
from app.domains.connectors.base import CanonicalCostRecord


def test_normalize_cost_explorer_page_maps_groups() -> None:
    page = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-04-10", "End": "2026-04-11"},
                "Groups": [
                    {
                        "Keys": ["AmazonEC2"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "12.5", "Unit": "USD"},
                            "UsageQuantity": {"Amount": "3", "Unit": "Hrs"},
                        },
                    }
                ],
            }
        ]
    }

    rows = AwsConnectorClient._normalize_cost_explorer_page(page, "123456789012")
    assert len(rows) == 1
    rec = rows[0]
    assert rec.provider == "aws"
    assert rec.subscription_id == "123456789012"
    assert rec.service == "AmazonEC2"
    assert rec.cost_usd == 12.5
    assert rec.usage_quantity == 3.0
    assert rec.currency == "USD"


def test_normalize_cur_row_maps_resource_level_fields() -> None:
    row = {
        "line_item_usage_start_date": "2026-04-10T00:00:00Z",
        "line_item_unblended_cost": "9.75",
        "line_item_usage_amount": "13",
        "line_item_usage_account_id": "999999999999",
        "product_product_name": "AmazonEC2",
        "line_item_resource_id": "i-abc123",
        "product_region": "us-east-1",
        "resource_tags_user_environment": "prod",
        "resource_tags_user_ownerteam": "platform",
        "pricing_unit": "Hrs",
        "line_item_currency_code": "USD",
    }

    rec = AwsConnectorClient._normalize_cur_row(row, account_id="123456789012")
    assert rec is not None
    assert rec.provider == "aws"
    assert rec.date.isoformat() == "2026-04-10"
    assert rec.subscription_id == "999999999999"
    assert rec.service == "AmazonEC2"
    assert rec.resource_id == "i-abc123"
    assert rec.region == "us-east-1"
    assert rec.environment == "prod"
    assert rec.owner_team == "platform"
    assert rec.cost_usd == 9.75
    assert rec.usage_quantity == 13.0


def test_parse_cur_csv_bytes_filters_by_date_range() -> None:
    csv_body = (
        "line_item_usage_start_date,line_item_unblended_cost,product_product_name\n"
        "2026-04-01T00:00:00Z,5.0,AmazonS3\n"
        "2026-04-10T00:00:00Z,7.0,AmazonEC2\n"
    ).encode("utf-8")

    rows = AwsConnectorClient._parse_cur_csv_bytes(
        csv_body,
        account_id="123456789012",
        start=date(2026, 4, 10),
        end=date(2026, 4, 10),
    )
    assert len(rows) == 1
    assert rows[0].service == "AmazonEC2"


def test_consume_last_cur_checkpoints_clears_state() -> None:
    client = AwsConnectorClient(
        access_key_id="a",
        secret_access_key="b",
        cur_bucket="bucket",
    )
    client._last_cur_checkpoints = [
        {"checkpoint_key": "k1", "object_key": "obj.csv", "object_etag": "etag"}
    ]

    first = client.consume_last_cur_checkpoints()
    second = client.consume_last_cur_checkpoints()

    assert len(first) == 1
    assert first[0]["checkpoint_key"] == "k1"
    assert second == []


@pytest.mark.asyncio
async def test_fetch_carbon_emissions_estimates_from_costs(monkeypatch):
    client = AwsConnectorClient(access_key_id="a", secret_access_key="b")

    async def fake_fetch_costs(subscription_id: str, start: date, end: date):
        return [
            CanonicalCostRecord(
                date=date(2026, 4, 1),
                provider="aws",
                subscription_id=subscription_id,
                service="AmazonEC2",
                resource_id="",
                resource_name="",
                region="us-east-1",
                environment="unknown",
                owner_team="untagged",
                cost_usd=100.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
            CanonicalCostRecord(
                date=date(2026, 4, 2),
                provider="aws",
                subscription_id=subscription_id,
                service="AmazonS3",
                resource_id="",
                resource_name="",
                region="us-east-1",
                environment="unknown",
                owner_team="untagged",
                cost_usd=50.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
        ]

    monkeypatch.setattr(client, "fetch_costs", fake_fetch_costs)
    rows = await client.fetch_carbon_emissions("123456789012", date(2026, 4, 1), date(2026, 4, 30))

    assert len(rows) == 2
    by_service = {row.service: row.kg_co2e for row in rows}
    assert by_service["AmazonEC2"] == 42.0
    assert by_service["AmazonS3"] == 11.0


@pytest.mark.asyncio
async def test_fetch_carbon_emissions_uses_configured_factors(monkeypatch):
    client = AwsConnectorClient(access_key_id="a", secret_access_key="b")

    class _Settings:
        aws_carbon_factors_json = '{"amazonec2": 0.5, "default": 0.25}'

    monkeypatch.setattr("app.domains.connectors.aws.client.get_settings", lambda: _Settings())

    async def fake_fetch_costs(subscription_id: str, start: date, end: date):
        return [
            CanonicalCostRecord(
                date=date(2026, 4, 1),
                provider="aws",
                subscription_id=subscription_id,
                service="AmazonEC2",
                resource_id="",
                resource_name="",
                region="us-east-1",
                environment="unknown",
                owner_team="untagged",
                cost_usd=10.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
            CanonicalCostRecord(
                date=date(2026, 4, 1),
                provider="aws",
                subscription_id=subscription_id,
                service="AmazonCloudFront",
                resource_id="",
                resource_name="",
                region="global",
                environment="unknown",
                owner_team="untagged",
                cost_usd=10.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
        ]

    monkeypatch.setattr(client, "fetch_costs", fake_fetch_costs)
    rows = await client.fetch_carbon_emissions("123456789012", date(2026, 4, 1), date(2026, 4, 30))
    by_service = {row.service: row.kg_co2e for row in rows}
    assert by_service["AmazonEC2"] == 5.0
    assert by_service["AmazonCloudFront"] == 2.5
