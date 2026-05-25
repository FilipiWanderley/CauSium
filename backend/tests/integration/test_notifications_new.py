from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.domains.notifications.models import AlertCategory, AlertSeverity, AlertStatus
from app.domains.notifications.service import NotificationsService


async def _register(client, suffix: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Org {suffix}",
            "org_slug": f"org-{suffix}-{uuid4().hex[:6]}",
            "email": f"admin-{suffix}@notifications.com",
            "full_name": "Admin",
            "password": "adminpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "org_id": data["user"]["org_id"],
        "user_id": data["user"]["id"],
    }


@pytest.mark.asyncio
async def test_notifications_new_returns_unread_count_and_items(client, db):
    org_a = await _register(client, "nt04-a")
    org_b = await _register(client, "nt04-b")

    svc = NotificationsService(db)

    workspace_unread = await svc.create(
        org_id=UUID(org_a["org_id"]),
        category=AlertCategory.FINANCIAL,
        severity=AlertSeverity.WARNING,
        title="Workspace unread",
    )
    user_unread_critical = await svc.create(
        org_id=UUID(org_a["org_id"]),
        user_id=UUID(org_a["user_id"]),
        category=AlertCategory.SECURITY,
        severity=AlertSeverity.CRITICAL,
        title="User unread critical",
    )
    read_item = await svc.create(
        org_id=UUID(org_a["org_id"]),
        category=AlertCategory.ACTIVITY,
        severity=AlertSeverity.INFO,
        title="Should not be unread",
    )
    await svc.set_status(UUID(org_a["org_id"]), read_item.id, AlertStatus.READ)

    await svc.create(
        org_id=UUID(org_b["org_id"]),
        category=AlertCategory.FINANCIAL,
        severity=AlertSeverity.CRITICAL,
        title="Other org unread",
    )
    await db.commit()

    counts_resp = await client.get("/api/v1/notifications/unread-count", headers=org_a["headers"])
    assert counts_resp.status_code == 200, counts_resp.text

    resp = await client.get(
        "/api/v1/notifications",
        headers=org_a["headers"],
        params={"status": "unread"},
    )
    assert resp.status_code == 200, resp.text

    counts = counts_resp.json()
    assert counts["unread"] == 2
    assert counts["critical"] == 1

    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2

    ids = {item["id"] for item in body["items"]}
    assert str(workspace_unread.id) in ids
    assert str(user_unread_critical.id) in ids
    assert str(read_item.id) not in ids
    assert all(item["status"] == "unread" for item in body["items"])


@pytest.mark.asyncio
async def test_notifications_new_supports_category_and_pagination(client, db):
    org = await _register(client, "nt04-category")

    svc = NotificationsService(db)

    first = await svc.create(
        org_id=UUID(org["org_id"]),
        category=AlertCategory.FINANCIAL,
        severity=AlertSeverity.WARNING,
        title="Financial 1",
    )
    second = await svc.create(
        org_id=UUID(org["org_id"]),
        category=AlertCategory.FINANCIAL,
        severity=AlertSeverity.INFO,
        title="Financial 2",
    )
    await svc.create(
        org_id=UUID(org["org_id"]),
        category=AlertCategory.GOVERNANCE,
        severity=AlertSeverity.INFO,
        title="Governance",
    )
    await db.commit()

    counts_filtered = await client.get(
        "/api/v1/notifications/unread-count",
        headers=org["headers"],
        params={"category": "financial"},
    )
    assert counts_filtered.status_code == 200, counts_filtered.text
    counts_data = counts_filtered.json()
    assert counts_data["unread"] == 2
    assert counts_data["critical"] == 0

    paged = await client.get(
        "/api/v1/notifications",
        headers=org["headers"],
        params={"category": "financial", "status": "unread", "page": 1, "page_size": 1},
    )
    assert paged.status_code == 200, paged.text
    page_data = paged.json()
    assert page_data["total"] == 2
    assert len(page_data["items"]) == 1

    paged_ids = {item["id"] for item in page_data["items"]}
    assert str(first.id) in paged_ids or str(second.id) in paged_ids


@pytest.mark.asyncio
async def test_risk_budget_creation_does_not_create_audit_duplicate_notification(client):
    org = await _register(client, "nt04-risk-budget")

    initial = await client.get(
        "/api/v1/notifications",
        headers=org["headers"],
        params={"status": "unread"},
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["total"] == 0

    created = await client.post(
        "/api/v1/risk-budgets",
        headers=org["headers"],
        json={
            "name": "Production blast radius",
            "domain": "payments",
            "environment": "production",
            "budget_type": "blast_radius",
            "period": "weekly",
            "limit_value": 20,
        },
    )
    assert created.status_code == 201, created.text

    notifications = await client.get(
        "/api/v1/notifications",
        headers=org["headers"],
        params={"status": "unread"},
    )
    assert notifications.status_code == 200, notifications.text
    body = notifications.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["category"] == "governance"
    assert item["source_type"] == "risk_budget"
    assert item["title"].startswith("Risk budget configured:")


@pytest.mark.asyncio
async def test_change_event_creation_generates_audit_notification(client):
    org = await _register(client, "nt04-change-event")

    initial = await client.get(
        "/api/v1/notifications",
        headers=org["headers"],
        params={"status": "unread"},
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["total"] == 0

    created = await client.post(
        "/api/v1/change-events",
        headers=org["headers"],
        json={
            "event_type": "deploy",
            "title": "Payments deployment",
            "description": "Release 2026.05.25",
            "environment": "production",
            "owner_team": "payments",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert created.status_code == 201, created.text

    notifications = await client.get(
        "/api/v1/notifications",
        headers=org["headers"],
        params={"status": "unread"},
    )
    assert notifications.status_code == 200, notifications.text
    body = notifications.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["category"] == "activity"
    assert item["source_type"] == "audit_event"
    assert item["title"] == "Activity: change_event.created"
