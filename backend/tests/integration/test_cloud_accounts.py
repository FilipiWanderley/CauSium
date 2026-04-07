import pytest


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
