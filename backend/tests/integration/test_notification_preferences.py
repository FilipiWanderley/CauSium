import pytest


@pytest.mark.asyncio
async def test_get_preferences_returns_defaults(client, auth_headers):
    resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["in_app_enabled"] is True
    assert data["email_enabled"] is True
    assert data["slack_enabled"] is False
    assert data["frequency"] == "instant"
    assert data["categories"]["financial"] is True


@pytest.mark.asyncio
async def test_put_preferences_persists_changes(client, auth_headers):
    update = {
        "in_app_enabled": True,
        "email_enabled": False,
        "slack_enabled": True,
        "frequency": "daily",
        "categories": {
            "financial": True,
            "optimization": False,
            "governance": True,
            "activity": False,
            "security": True,
        },
    }

    put_resp = await client.put("/api/v1/notifications/preferences", json=update, headers=auth_headers)
    assert put_resp.status_code == 200, put_resp.text
    data = put_resp.json()
    assert data["email_enabled"] is False
    assert data["slack_enabled"] is True
    assert data["frequency"] == "daily"
    assert data["categories"]["optimization"] is False

    get_resp = await client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert get_resp.status_code == 200, get_resp.text
    persisted = get_resp.json()
    assert persisted["email_enabled"] is False
    assert persisted["frequency"] == "daily"
    assert persisted["categories"]["activity"] is False


@pytest.mark.asyncio
async def test_preferences_isolated_per_workspace(client, org_a, org_b):
    update_b = {
        "email_enabled": False,
        "frequency": "weekly",
        "categories": {
            "financial": False,
            "optimization": False,
            "governance": True,
            "activity": True,
            "security": True,
        },
    }

    put_b = await client.put(
        "/api/v1/notifications/preferences",
        json=update_b,
        headers=org_b["headers"],
    )
    assert put_b.status_code == 200, put_b.text

    get_a = await client.get("/api/v1/notifications/preferences", headers=org_a["headers"])
    assert get_a.status_code == 200, get_a.text
    data_a = get_a.json()

    assert data_a["frequency"] == "instant"
    assert data_a["email_enabled"] is True
    assert data_a["categories"]["financial"] is True
