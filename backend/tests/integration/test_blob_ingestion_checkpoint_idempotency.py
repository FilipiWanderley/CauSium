from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from app.core.security import encrypt_secret_for_org
from app.domains.auth.models import Organization
from app.domains.cloud_accounts.models import BlobIngestionCheckpoint, CloudAccount, CloudProvider, ConnectorStatus
from app.domains.cloud_ledger.service import CloudLedgerService
from app.domains.connectors.base import CanonicalCostRecord


@pytest.mark.asyncio
async def test_blob_checkpoint_prevents_reprocessing_across_runs(db, monkeypatch):
    org = Organization(name="Org Blob", slug=f"org-blob-{uuid4().hex[:8]}")
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
                "subscription_id": "sub-blob-001",
                "storage_account_url": "https://example.blob.core.windows.net",
                "cost_export_container": "exports",
                "cost_export_prefix": "cost/",
            }
        ),
    )

    account = CloudAccount(
        org_id=org.id,
        provider=CloudProvider.AZURE,
        external_id="sub-blob-001",
        display_name="Blob Account",
        credentials_encrypted=encrypted_creds,
        status=ConnectorStatus.ACTIVE,
    )
    db.add(account)
    await db.flush()

    calls = {"count": 0}

    async def fake_fetch_costs(self, subscription_id, start, end, *, checkpoint_keys=None):
        calls["count"] += 1
        key = "exports/cost-2026-04-10.csv::etag-1"
        if checkpoint_keys and key in checkpoint_keys:
            self._last_blob_checkpoints = []
            return []

        self._last_blob_checkpoints = [
            {
                "checkpoint_key": key,
                "blob_name": "exports/cost-2026-04-10.csv",
                "blob_etag": "etag-1",
            }
        ]
        return [
            CanonicalCostRecord(
                date=date(2026, 4, 10),
                provider="azure",
                subscription_id=subscription_id,
                service="Azure Storage",
                resource_id="/subscriptions/sub-blob-001/resourceGroups/rg-a/providers/Microsoft.Storage/storageAccounts/stg-a",
                resource_name="stg-a",
                region="eastus",
                environment="production",
                owner_team="platform",
                cost_usd=7.5,
                usage_quantity=10.0,
                usage_unit="GB",
                currency="USD",
                tags={"env": "production", "team": "platform"},
            )
        ]

    async def fake_fetch_events(self, subscription_id, start, end):
        return []

    inserted_cost_batches: list[int] = []

    def fake_insert_rows(table: str, rows: list[dict]):
        if table == "cost_facts":
            inserted_cost_batches.append(len(rows))

    monkeypatch.setattr("app.domains.connectors.azure.client.AzureConnectorClient.fetch_costs", fake_fetch_costs)
    monkeypatch.setattr("app.domains.connectors.azure.client.AzureConnectorClient.fetch_events", fake_fetch_events)
    monkeypatch.setattr("app.domains.cloud_ledger.service.insert_rows", fake_insert_rows)

    service = CloudLedgerService(db)

    first = await service.ingest_account(org.id, account.id, date(2026, 4, 1), date(2026, 4, 30))
    second = await service.ingest_account(org.id, account.id, date(2026, 4, 1), date(2026, 4, 30))

    assert calls["count"] == 2
    assert first.status == "ok"
    assert first.cost_records == 1
    assert second.status == "ok"
    assert second.cost_records == 0
    assert inserted_cost_batches == [1]

    checkpoints = await db.execute(
        BlobIngestionCheckpoint.__table__.select().where(BlobIngestionCheckpoint.account_id == account.id)
    )
    rows = checkpoints.fetchall()
    assert len(rows) == 1
    assert rows[0].checkpoint_key == "exports/cost-2026-04-10.csv::etag-1"
