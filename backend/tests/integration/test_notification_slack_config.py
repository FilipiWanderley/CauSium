import pytest


@pytest.mark.asyncio
async def test_get_slack_config_defaults(client, auth_headers):
    resp = await client.get("/api/v1/notifications/slack-config", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["enabled"] is False
    assert data["webhook_configured"] is False


@pytest.mark.asyncio
async def test_put_slack_config_persists(client, auth_headers):
    payload = {
        "enabled": True,
        "webhook_url": "https://hooks.slack.com/services/T000/B000/abc123",
    }
    put_resp = await client.put("/api/v1/notifications/slack-config", json=payload, headers=auth_headers)
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["enabled"] is True
    assert put_resp.json()["webhook_configured"] is True

    get_resp = await client.get("/api/v1/notifications/slack-config", headers=auth_headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["enabled"] is True
    assert get_resp.json()["webhook_configured"] is True


@pytest.mark.asyncio
async def test_put_slack_config_rejects_invalid_url(client, auth_headers):
    resp = await client.put(
        "/api/v1/notifications/slack-config",
        json={"enabled": True, "webhook_url": "https://example.com/not-slack"},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_slack_config_isolated_per_workspace(client, org_a, org_b):
    resp_b = await client.put(
        "/api/v1/notifications/slack-config",
        json={"enabled": True, "webhook_url": "https://hooks.slack.com/services/T111/B222/xyz"},
        headers=org_b["headers"],
    )
    assert resp_b.status_code == 200, resp_b.text

    get_a = await client.get("/api/v1/notifications/slack-config", headers=org_a["headers"])
    assert get_a.status_code == 200, get_a.text
    data_a = get_a.json()
    assert data_a["enabled"] is False
    assert data_a["webhook_configured"] is False
