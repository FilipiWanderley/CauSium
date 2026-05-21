import pytest
from uuid import UUID
from unittest.mock import AsyncMock, patch

from app.domains.admin.models import DlqMessage, DlqStatus


def _azure_account_payload(external_id: str, display_name: str, tenant_id: str = "tenant-abc") -> dict:
    return {
        "provider": "azure",
        "external_id": external_id,
        "display_name": display_name,
        "tenant_id": tenant_id,
        "azure_credentials": {
            "tenant_id": tenant_id,
            "client_id": f"client-{external_id}",
            "client_secret": "secret-test",
            "subscription_id": external_id,
            "storage_account_url": "https://example.blob.core.windows.net",
            "cost_export_container": "exports",
            "cost_export_prefix": "daily/",
        },
    }


@pytest.mark.asyncio
async def test_create_and_list_account(client, auth_headers):
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_account_payload("sub-12345", "Test Azure Sub"),
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
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_account_payload("sub-get-test", "Get Test Sub"),
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
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_account_payload("sub-health-test", "Health Test Sub"),
            headers=auth_headers,
        )
    account_id = create_resp.json()["id"]

    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        health_resp = await client.post(
            f"/api/v1/cloud-accounts/{account_id}/health-check",
            headers=auth_headers,
        )
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] in ("active", "error")


@pytest.mark.asyncio
async def test_azure_health_check_returns_warning_for_excessive_permissions(client, auth_headers):
    warning_msg = (
        "Detected elevated Azure role assignment (Owner/Contributor). "
        "For least privilege in CauSium read-only mode, prefer Reader + "
        "Cost Management Reader."
    )
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "azure",
                "external_id": "sub-warning-test",
                "display_name": "Warning Test Sub",
                "tenant_id": "tenant-warning",
                "azure_credentials": {
                    "tenant_id": "tenant-warning",
                    "client_id": "client-warning",
                    "client_secret": "secret-warning",
                    "subscription_id": "sub-warning-test",
                    "storage_account_url": "https://example.blob.core.windows.net",
                    "cost_export_container": "exports",
                    "cost_export_prefix": "daily/",
                },
            },
            headers=auth_headers,
        )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.get_last_scope_warnings", return_value=[warning_msg]),
    ):
        health_resp = await client.post(
            f"/api/v1/cloud-accounts/{account_id}/health-check",
            headers=auth_headers,
        )

    assert health_resp.status_code == 200, health_resp.text
    health = health_resp.json()
    assert health["status"] == "active"
    assert "Reader + Cost Management Reader" in (health.get("message") or "")


@pytest.mark.asyncio
async def test_sync_status_returns_operational_fields(client, auth_headers, db):
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_account_payload("sub-sync-status", "Sync Status Sub"),
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
    with (
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_account_payload("sub-iso-sync", "Org B Sync Sub", tenant_id="tenant-org-b"),
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


@pytest.mark.asyncio
async def test_validate_aws_account_scopes(client, auth_headers):
    with (
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "aws",
                "external_id": "123456789012",
                "display_name": "AWS Scope Validation",
                "aws_credentials": {
                    "access_key_id": "AKIA_TEST",
                    "secret_access_key": "test-secret",
                    "region": "us-east-1",
                    "cur_bucket": "my-cur-bucket",
                },
            },
            headers=auth_headers,
        )

    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    with (
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.aws.client.AwsConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        validate_resp = await client.post(
            f"/api/v1/cloud-accounts/{account_id}/validate",
            headers=auth_headers,
        )

    assert validate_resp.status_code == 200, validate_resp.text
    payload = validate_resp.json()
    assert payload["ok"] is True
    assert "CredentialsValid" in payload["validated_scopes"]
    assert "CostExplorerRead" in payload["validated_scopes"]
    assert "CurBucketRead" in payload["validated_scopes"]


@pytest.mark.asyncio
async def test_validate_gcp_account_scopes(client, auth_headers):
    with (
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json={
                "provider": "gcp",
                "external_id": "my-gcp-project",
                "display_name": "GCP Scope Validation",
                "gcp_credentials": {
                    "service_account_json": "{}",
                    "project_id": "my-gcp-project",
                    "billing_export_table": "billing.gcp_export",
                },
            },
            headers=auth_headers,
        )

    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    with (
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_connection", new=AsyncMock(return_value=None)),
        patch("app.domains.connectors.gcp.client.GcpConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)),
    ):
        validate_resp = await client.post(
            f"/api/v1/cloud-accounts/{account_id}/validate",
            headers=auth_headers,
        )

    assert validate_resp.status_code == 200, validate_resp.text
    payload = validate_resp.json()
    assert payload["ok"] is True
    assert "CredentialsValid" in payload["validated_scopes"]
    assert "BillingExportRead" in payload["validated_scopes"]
    assert "LoggingRead" in payload["validated_scopes"]
