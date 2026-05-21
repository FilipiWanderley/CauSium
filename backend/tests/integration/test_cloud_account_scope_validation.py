import pytest
from unittest.mock import AsyncMock, patch


def _azure_payload(external_id: str, tenant_id: str) -> dict:
    return {
        "provider": "azure",
        "external_id": external_id,
        "display_name": "Scope Test" if external_id == "sub-scope-001" else "Scope ISO",
        "tenant_id": tenant_id,
        "azure_credentials": {
            "tenant_id": tenant_id,
            "client_id": f"client-{external_id}",
            "client_secret": "secret-test",
            "subscription_id": external_id,
            "storage_account_url": "https://example.blob.core.windows.net",
            "cost_export_container": "exports",
            "cost_export_prefix": "scope/",
        },
    }


@pytest.mark.asyncio
async def test_validate_scope_success_for_mocked_azure_credentials(client, auth_headers):
    """SP-CL03 happy path: /{id}/validate returns validated scopes and timestamp."""
    with patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_payload("sub-scope-001", "tenant-test"),
            headers=auth_headers,
        )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    with patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)):
        validate_resp = await client.post(
            f"/api/v1/cloud-accounts/{account_id}/validate",
            headers=auth_headers,
        )
    assert validate_resp.status_code == 200, validate_resp.text
    data = validate_resp.json()
    assert data["ok"] is True
    assert data["provider"] == "azure"
    assert data["validated_scopes"] == ["CostManagementReaderOrHigher"]
    assert data["scopes_validated_at"] is not None


@pytest.mark.asyncio
async def test_validate_scope_not_found(client, auth_headers):
    resp = await client.post(
        "/api/v1/cloud-accounts/00000000-0000-0000-0000-000000000000/validate",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_validate_scope_requires_auth(client):
    resp = await client.post(
        "/api/v1/cloud-accounts/00000000-0000-0000-0000-000000000000/validate"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_validate_scope_org_isolation(client, org_a, org_b):
    """Admin from workspace A cannot validate account from workspace B."""
    with patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_connection", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_cost_management_scope", new=AsyncMock(return_value=None)), \
         patch("app.domains.connectors.azure.client.AzureConnectorClient.validate_storage_access", new=AsyncMock(return_value=None)):
        create_resp = await client.post(
            "/api/v1/cloud-accounts",
            json=_azure_payload("sub-scope-iso", "tenant-iso"),
            headers=org_b["headers"],
        )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/cloud-accounts/{account_id}/validate",
        headers=org_a["headers"],
    )
    assert resp.status_code == 404
