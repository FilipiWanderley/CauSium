import pytest
from uuid import UUID
from unittest.mock import AsyncMock, patch

from app.domains.admin.models import DlqMessage, DlqStatus


@pytest.mark.asyncio
async def test_create_and_list_account(client, auth_headers):
    resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-12345",
            "display_name": "Test Azure Sub",
            "tenant_id": "tenant-abc",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    account = resp.json()
    assert account["provider"] == "azure"
    assert account["external_id"] == "sub-12345"
    assert account["status"] == "pending"

    list_resp = await client.get("/api/v1/cloud-accounts", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_account(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-get-test",
            "display_name": "Get Test Sub",
        },
        headers=auth_headers,
    )
    account_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/cloud-accounts/{account_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == account_id


@pytest.mark.asyncio
async def test_get_nonexistent_account(client, auth_headers):
    resp = await client.get(
        "/api/v1/cloud-accounts/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_check_uses_mock(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-health-test",
            "display_name": "Health Test Sub",
        },
        headers=auth_headers,
    )
    account_id = create_resp.json()["id"]

    health_resp = await client.post(
        f"/api/v1/cloud-accounts/{account_id}/health-check",
        headers=auth_headers,
    )
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] in ("active", "error")


@pytest.mark.asyncio
async def test_sync_status_returns_operational_fields(client, auth_headers, db):
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-sync-status",
            "display_name": "Sync Status Sub",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    account = create_resp.json()
    account_id = account["id"]

    db.add(
        DlqMessage(
            queue_name="ingestion:queue",
            org_id=UUID(account["org_id"]),
            account_id=UUID(account_id),
            original_payload='{"account_id": "sub-sync-status"}',
            error_message="boom",
            retry_count=3,
            status=DlqStatus.OPEN,
        )
    )
    await db.commit()

    resp = await client.get("/api/v1/cloud-accounts/sync-status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()

    target = next(item for item in items if item["account_id"] == account_id)
    assert target["display_name"] == "Sync Status Sub"
    assert target["provider"] == "azure"
    assert target["connector_status"] == "pending"
    assert target["open_dlq_count"] == 1
    assert target["needs_attention"] is True


@pytest.mark.asyncio
async def test_sync_status_respects_workspace_isolation(client, org_a, org_b):
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-iso-sync",
            "display_name": "Org B Sync Sub",
        },
        headers=org_b["headers"],
    )
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]

    resp_a = await client.get("/api/v1/cloud-accounts/sync-status", headers=org_a["headers"])
    assert resp_a.status_code == 200
    assert all(item["account_id"] != account_id for item in resp_a.json())


@pytest.mark.asyncio
async def test_create_aws_account_with_credentials(client, auth_headers):
    with (
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "aws",
                "external_id": "123456789012",
                "display_name": "AWS Payer",
                "aws_credentials": {
                    "access_key_id": "AKIA_TEST",
                    "secret_access_key": "test-secret",
                    "region": "us-east-1",
                },
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["provider"] == "aws"
    assert payload["external_id"] == "123456789012"


@pytest.mark.asyncio
async def test_create_gcp_account_with_credentials(client, auth_headers):
    with (
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "gcp",
                "external_id": "my-gcp-project",
                "display_name": "GCP Billing Project",
                "gcp_credentials": {
                    "service_account_json": "{}",
                    "project_id": "my-gcp-project",
                    "billing_export_table": "billing.gcp_export",
                },
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["provider"] == "gcp"
    assert payload["external_id"] == "my-gcp-project"


@pytest.mark.asyncio
async def test_create_gcp_account_with_workload_identity(client, auth_headers):
    with (
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "gcp",
                "external_id": "my-gcp-project-wi",
                "display_name": "GCP Workload Identity Project",
                "gcp_credentials": {
                    "project_id": "my-gcp-project-wi",
                    "use_workload_identity": True,
                    "billing_export_table": "billing.gcp_export",
                },
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["provider"] == "gcp"
    assert payload["external_id"] == "my-gcp-project-wi"
