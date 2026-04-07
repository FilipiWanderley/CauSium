import pytest


@pytest.mark.asyncio
async def test_validate_scope_success_for_mocked_azure_credentials(client, auth_headers):
    """SP-CL03 happy path: /{id}/validate returns validated scopes and timestamp."""
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-scope-001",
            "display_name": "Scope Test",
            "tenant_id": "tenant-test",
            "azure_credentials": {
                "tenant_id": "tenant-test",
                "client_id": "client-test",
                "client_secret": "secret-test",
                "subscription_id": "sub-scope-001",
            },
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

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
    create_resp = await client.post(
        "/api/v1/cloud-accounts",
        json={
            "provider": "azure",
            "external_id": "sub-scope-iso",
            "display_name": "Scope ISO",
            "tenant_id": "tenant-iso",
            "azure_credentials": {
                "tenant_id": "tenant-iso",
                "client_id": "client-iso",
                "client_secret": "secret-iso",
                "subscription_id": "sub-scope-iso",
            },
        },
        headers=org_b["headers"],
    )
    assert create_resp.status_code == 201, create_resp.text
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/cloud-accounts/{account_id}/validate",
        headers=org_a["headers"],
    )
    assert resp.status_code == 404
