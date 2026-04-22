from __future__ import annotations

from datetime import date

import pytest

from app.domains.connectors.base import CanonicalCostRecord
from app.domains.connectors.gcp.client import GcpConnectorClient


@pytest.mark.asyncio
async def test_fetch_carbon_emissions_estimates_from_costs(monkeypatch):
    client = GcpConnectorClient(
        service_account_json=None,
        project_id="my-project",
        use_workload_identity=True,
        billing_export_table="billing.export_table",
    )

    async def fake_fetch_costs(subscription_id: str, start: date, end: date):
        return [
            CanonicalCostRecord(
                date=date(2026, 4, 1),
                provider="gcp",
                subscription_id=subscription_id,
                service="Compute Engine",
                resource_id="",
                resource_name="",
                region="us-central1",
                environment="unknown",
                owner_team="untagged",
                cost_usd=80.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
            CanonicalCostRecord(
                date=date(2026, 4, 10),
                provider="gcp",
                subscription_id=subscription_id,
                service="Cloud Storage",
                resource_id="",
                resource_name="",
                region="us-central1",
                environment="unknown",
                owner_team="untagged",
                cost_usd=20.0,
                usage_quantity=0.0,
                usage_unit="",
                currency="USD",
                tags={},
            ),
        ]

    monkeypatch.setattr(client, "fetch_costs", fake_fetch_costs)
    rows = await client.fetch_carbon_emissions("my-project", date(2026, 4, 1), date(2026, 4, 30))

    assert len(rows) == 2
    by_service = {row.service: row.kg_co2e for row in rows}
    assert by_service["Compute Engine"] == 32.0
    assert by_service["Cloud Storage"] == 4.0
