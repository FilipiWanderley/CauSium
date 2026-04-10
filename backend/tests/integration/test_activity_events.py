from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_create_and_list_activity_events_with_filters(client, auth_headers):
    base_ts = datetime.now(timezone.utc)

    create_a = await client.post(
        "/api/v1/notifications/activity-events",
        json={
            "provider": "azure",
            "event_type": "vm.power_state.changed",
            "severity": "warning",
            "title": "VM state changed",
            "service": "compute",
            "resource_id": "vm-001",
            "occurred_at": base_ts.isoformat(),
        },
        headers=auth_headers,
    )
    assert create_a.status_code == 201, create_a.text

    create_b = await client.post(
        "/api/v1/notifications/activity-events",
        json={
            "provider": "azure",
            "event_type": "keyvault.secret.expiring",
            "severity": "critical",
            "title": "Secret expiring",
            "service": "security",
            "resource_id": "kv-001",
            "occurred_at": (base_ts + timedelta(minutes=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert create_b.status_code == 201, create_b.text

    list_all = await client.get("/api/v1/notifications/activity-events", headers=auth_headers)
    assert list_all.status_code == 200, list_all.text
    body = list_all.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2

    filtered = await client.get(
        "/api/v1/notifications/activity-events",
        headers=auth_headers,
        params={"event_type": "keyvault.secret.expiring"},
    )
    assert filtered.status_code == 200, filtered.text
    fbody = filtered.json()
    assert fbody["total"] == 1
    assert fbody["items"][0]["event_type"] == "keyvault.secret.expiring"

    windowed = await client.get(
        "/api/v1/notifications/activity-events",
        headers=auth_headers,
        params={
            "occurred_from": (base_ts + timedelta(seconds=30)).isoformat(),
            "occurred_to": (base_ts + timedelta(minutes=2)).isoformat(),
        },
    )
    assert windowed.status_code == 200, windowed.text
    wbody = windowed.json()
    assert wbody["total"] == 1
    assert wbody["items"][0]["resource_id"] == "kv-001"


@pytest.mark.asyncio
async def test_activity_events_are_isolated_per_workspace(client, org_a, org_b):
    create_b = await client.post(
        "/api/v1/notifications/activity-events",
        json={
            "provider": "azure",
            "event_type": "subscription.policy.updated",
            "severity": "info",
            "title": "Policy changed",
            "service": "governance",
            "resource_id": "sub-abc",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=org_b["headers"],
    )
    assert create_b.status_code == 201, create_b.text

    list_a = await client.get("/api/v1/notifications/activity-events", headers=org_a["headers"])
    assert list_a.status_code == 200, list_a.text
    assert list_a.json()["total"] == 0


@pytest.mark.asyncio
async def test_critical_activity_event_generates_notification_alert(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/notifications/activity-events",
        json={
            "provider": "azure",
            "event_type": "security.policy.violation",
            "severity": "critical",
            "title": "Security policy violation",
            "service": "security",
            "resource_id": "policy-001",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text

    new_resp = await client.get(
        "/api/v1/notifications/new",
        headers=auth_headers,
        params={"category": "activity"},
    )
    assert new_resp.status_code == 200, new_resp.text
    data = new_resp.json()
    assert data["unread"] >= 1
    assert any(item["title"].startswith("Critical activity:") for item in data["items"])
