from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from app.core.security import encrypt_secret_for_org
from app.domains.auth.models import Organization
from app.domains.cloud_accounts.models import CloudAccount, CloudProvider, ConnectorStatus
from app.domains.cloud_ledger.service import CloudLedgerService
from app.domains.connectors.base import CanonicalCarbonRecord


@pytest.mark.asyncio
async def test_ingest_carbon_account_persists_rows(db, monkeypatch):
    org = Organization(name="Org Carbon", slug=f"org-carbon-{uuid4().hex[:8]}")
    db.add(org)
    await db.flush()

    encrypted_creds = await encrypt_secret_for_org(
        db,
        org.id,
        json.dumps(
            {
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
                "subscription_id": "sub-carbon-001",
                "storage_account_url": "https://example.blob.core.windows.net",
                "cost_export_container": "exports",
                "cost_export_prefix": "carbon/",
            }
        ),
    )

    account = CloudAccount(
        org_id=org.id,
        provider=CloudProvider.AZURE,
        external_id="sub-carbon-001",
        display_name="Carbon Account",
        credentials_encrypted=encrypted_creds,
        status=ConnectorStatus.ACTIVE,
    )
    db.add(account)
    await db.flush()

    async def fake_fetch_carbon(self, subscription_id, start, end):
        return [
            CanonicalCarbonRecord(
                year_month="2026-04",
                provider="azure",
                subscription_id=subscription_id,
                service="Compute",
                resource_group="rg-core",
                kg_co2e=42.0,
            )
        ]

    captured = {"table": None, "rows": []}

    def fake_insert_rows(table: str, rows: list[dict]):
        captured["table"] = table
        captured["rows"] = rows

    monkeypatch.setattr("app.domains.connectors.azure.client.AzureConnectorClient.fetch_carbon_emissions", fake_fetch_carbon)
    monkeypatch.setattr("app.domains.cloud_ledger.service.insert_rows", fake_insert_rows)

    svc = CloudLedgerService(db)
    count = await svc.ingest_carbon_account(org.id, account.id, date(2026, 4, 1), date(2026, 4, 30))

    assert count == 1
    assert captured["table"] == "carbon_facts"
    assert len(captured["rows"]) == 1
    assert captured["rows"][0]["kg_co2e"] == 42.0
