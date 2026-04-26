from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.domains.admin.models import SupportAccessSession
from app.domains.auth.models import User, UserRole


async def _register(client, *, org_name, org_slug, email, name="User", pw="password12345"):
    resp = await client.post("/api/v1/auth/register", json={
        "org_name": org_name,
        "org_slug": org_slug,
        "email": email,
        "full_name": name,
        "password": pw,
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "org_id": data["user"]["org_id"],
        "user_id": data["user"]["id"],
    }


async def _make_platform_admin(db, user_id: str) -> None:
    await db.execute(
        update(User).where(User.id == user_id).values(role=UserRole.PLATFORM_ADMIN)
    )
    await db.commit()


@pytest.mark.asyncio
async def test_platform_admin_creates_support_access_session(client, db):
    pa = await _register(client, org_name="PA SA", org_slug="pa-sa", email="pa-sa@test.com")
    target = await _register(client, org_name="Target SA", org_slug="target-sa", email="target-sa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    resp = await client.post(
        "/api/v1/admin/support-access",
        json={
            "target_org_id": target["org_id"],
            "reason": "Investigating support ticket #123",
            "duration_minutes": 30,
        },
        headers=pa["headers"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["actor_user_id"] == pa["user_id"]
    assert body["target_org_id"] == target["org_id"]
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_regular_user_cannot_create_support_access_session(client):
    user = await _register(client, org_name="Regular SA", org_slug="regular-sa", email="regular-sa@test.com")
    target = await _register(client, org_name="Target SA2", org_slug="target-sa2", email="target-sa2@test.com")
    resp = await client.post(
        "/api/v1/admin/support-access",
        json={
            "target_org_id": target["org_id"],
            "reason": "Trying unauthorized support access",
            "duration_minutes": 10,
        },
        headers=user["headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_expired_support_session_is_invalid(client, db):
    pa = await _register(client, org_name="PA Exp", org_slug="pa-exp", email="pa-exp@test.com")
    target = await _register(client, org_name="Target Exp", org_slug="target-exp", email="target-exp@test.com")
    await _make_platform_admin(db, pa["user_id"])

    create = await client.post(
        "/api/v1/admin/support-access",
        json={
            "target_org_id": target["org_id"],
            "reason": "Short support access",
            "duration_minutes": 5,
        },
        headers=pa["headers"],
    )
    assert create.status_code == 201, create.text
    session_id = create.json()["id"]

    await db.execute(
        update(SupportAccessSession)
        .where(SupportAccessSession.id == session_id)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    await db.commit()

    resp = await client.get(
        "/api/v1/audit-chain/events",
        headers={
            **pa["headers"],
            "X-Support-Access-Session-Id": session_id,
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_end_support_access_registers_audit_event(client, db):
    pa = await _register(client, org_name="PA End", org_slug="pa-end", email="pa-end@test.com")
    target = await _register(client, org_name="Target End", org_slug="target-end", email="target-end@test.com")
    await _make_platform_admin(db, pa["user_id"])

    create = await client.post(
        "/api/v1/admin/support-access",
        json={
            "target_org_id": target["org_id"],
            "reason": "Investigating issue",
            "duration_minutes": 20,
        },
        headers=pa["headers"],
    )
    assert create.status_code == 201, create.text
    session_id = create.json()["id"]

    end = await client.post(
        f"/api/v1/admin/support-access/{session_id}/end",
        json={"reason": "Issue solved"},
        headers=pa["headers"],
    )
    assert end.status_code == 200, end.text
    assert end.json()["status"] == "ended"

    events = await client.get(
        f"/api/v1/audit-chain/events?org_id={target['org_id']}&event_type=support_access.ended",
        headers=pa["headers"],
    )
    assert events.status_code == 200, events.text
    assert events.json()["total"] >= 1


@pytest.mark.asyncio
async def test_effective_org_resolves_target_org_during_support_session(client, db):
    pa = await _register(client, org_name="PA Ctx", org_slug="pa-ctx", email="pa-ctx@test.com")
    target = await _register(client, org_name="Target Ctx", org_slug="target-ctx", email="target-ctx@test.com")
    await _make_platform_admin(db, pa["user_id"])

    # Create an auditable event in target org.
    create_budget = await client.post("/api/v1/risk-budgets", json={
        "name": "Target Budget",
        "domain": "finops",
        "environment": "production",
        "budget_type": "cost_variance",
        "period": "weekly",
        "limit_value": 1000.0,
    }, headers=target["headers"])
    assert create_budget.status_code == 201, create_budget.text

    create = await client.post(
        "/api/v1/admin/support-access",
        json={
            "target_org_id": target["org_id"],
            "reason": "Validate workspace data for support",
            "duration_minutes": 15,
        },
        headers=pa["headers"],
    )
    assert create.status_code == 201, create.text
    session_id = create.json()["id"]

    events = await client.get(
        "/api/v1/audit-chain/events",
        headers={
            **pa["headers"],
            "X-Support-Access-Session-Id": session_id,
        },
    )
    assert events.status_code == 200, events.text
    body = events.json()
    assert body["total"] >= 1
    assert any(item["org_id"] == target["org_id"] for item in body["items"])
