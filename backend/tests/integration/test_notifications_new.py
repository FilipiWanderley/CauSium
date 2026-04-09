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

    resp = await client.get("/api/v1/notifications/new", headers=org_a["headers"])
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["unread"] == 2
    assert body["critical"] == 1
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

    filtered = await client.get(
        "/api/v1/notifications/new",
        headers=org["headers"],
        params={"category": "financial"},
    )
    assert filtered.status_code == 200, filtered.text
    data = filtered.json()
    assert data["unread"] == 2
    assert data["critical"] == 0
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(item["category"] == "financial" for item in data["items"])

    paged = await client.get(
        "/api/v1/notifications/new",
        headers=org["headers"],
        params={"category": "financial", "page": 1, "page_size": 1},
    )
    assert paged.status_code == 200, paged.text
    page_data = paged.json()
    assert page_data["total"] == 2
    assert len(page_data["items"]) == 1

    paged_ids = {item["id"] for item in page_data["items"]}
    assert str(first.id) in paged_ids or str(second.id) in paged_ids
