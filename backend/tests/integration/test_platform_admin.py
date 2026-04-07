"""
SP-MT05 — PLATFORM_ADMIN role test suite.

Verifies that:
  - PLATFORM_ADMIN can access all orgs
  - PLATFORM_ADMIN can force lifecycle transitions on any workspace
  - Regular ADMIN cannot access /admin/* endpoints
  - PLATFORM_ADMIN is not blocked by a suspended workspace lifecycle gate
  - Every force transition is reflected in workspace state
"""
import pytest
from sqlalchemy import update


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    from app.domains.auth.models import User, UserRole

    await db.execute(
        update(User).where(User.id == user_id).values(role=UserRole.PLATFORM_ADMIN)
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Access control — who may call /admin/*
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regular_admin_cannot_access_admin_endpoints(client):
    org = await _register(client, org_name="RegAdmin", org_slug="pa-reg-admin", email="pa-reg@test.com")

    resp = await client.get("/api/v1/admin/orgs", headers=org["headers"])
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_admin_endpoints(client):
    resp = await client.get("/api/v1/admin/orgs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_platform_admin_can_list_all_orgs(client, db):
    pa = await _register(client, org_name="PA List", org_slug="pa-list", email="pa-list@test.com")
    await _make_platform_admin(db, pa["user_id"])

    # Create a second org so the list is non-trivial
    await _register(client, org_name="PA Target", org_slug="pa-list-target", email="pa-list-target@test.com")

    resp = await client.get("/api/v1/admin/orgs", headers=pa["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_platform_admin_can_get_any_org_detail(client, db):
    pa = await _register(client, org_name="PA Detail", org_slug="pa-detail-pa", email="pa-detail-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Detail Target", org_slug="pa-detail-target", email="pa-detail-target@test.com")

    resp = await client.get(f"/api/v1/admin/orgs/{target['org_id']}", headers=pa["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == target["org_id"]


@pytest.mark.asyncio
async def test_platform_admin_can_list_users_of_any_org(client, db):
    pa = await _register(client, org_name="PA Users", org_slug="pa-users-pa", email="pa-users-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="User Target", org_slug="pa-users-target", email="pa-users-target@test.com")

    resp = await client.get(f"/api/v1/admin/orgs/{target['org_id']}/users", headers=pa["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    emails = [u["email"] for u in data["items"]]
    assert "pa-users-target@test.com" in emails


# ---------------------------------------------------------------------------
# Force lifecycle transitions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_platform_admin_can_force_suspend_any_org(client, db):
    pa = await _register(client, org_name="PA Suspend", org_slug="pa-sus-pa", email="pa-sus-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Suspend Target", org_slug="pa-sus-target", email="pa-sus-target@test.com")

    resp = await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/suspend",
        json={"reason": "Compliance violation detected"},
        headers=pa["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycle_state"] == "suspended"
    assert data["suspended_reason"] == "Compliance violation detected"


@pytest.mark.asyncio
async def test_platform_admin_can_force_restore_suspended_org(client, db):
    pa = await _register(client, org_name="PA Restore", org_slug="pa-res-pa", email="pa-res-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Restore Target", org_slug="pa-res-target", email="pa-res-target@test.com")

    await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/suspend",
        json={"reason": "Temporary suspension"},
        headers=pa["headers"],
    )

    resp = await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/restore",
        json={"reason": "Issue resolved"},
        headers=pa["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "active"


@pytest.mark.asyncio
async def test_platform_admin_can_force_archive_org(client, db):
    pa = await _register(client, org_name="PA Archive", org_slug="pa-arc-pa", email="pa-arc-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Archive Target", org_slug="pa-arc-target", email="pa-arc-target@test.com")

    resp = await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/archive",
        json={"reason": "Trial expired, no conversion"},
        headers=pa["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "archived"


@pytest.mark.asyncio
async def test_force_archive_already_archived_returns_409(client, db):
    pa = await _register(client, org_name="PA Arc409", org_slug="pa-arc409-pa", email="pa-arc409-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Arc409 Target", org_slug="pa-arc409-target", email="pa-arc409-target@test.com")

    await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/archive",
        json={"reason": "First archive"},
        headers=pa["headers"],
    )
    resp = await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/archive",
        json={"reason": "Duplicate archive"},
        headers=pa["headers"],
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_force_restore_active_org_returns_409(client, db):
    pa = await _register(client, org_name="PA Res409", org_slug="pa-res409-pa", email="pa-res409-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    target = await _register(client, org_name="Res409 Target", org_slug="pa-res409-target", email="pa-res409-target@test.com")

    resp = await client.post(
        f"/api/v1/admin/orgs/{target['org_id']}/restore",
        json={"reason": "Nothing to restore"},
        headers=pa["headers"],
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PLATFORM_ADMIN bypasses lifecycle gate on their own token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_platform_admin_not_blocked_by_suspended_own_org(client, db):
    """
    Even if the PLATFORM_ADMIN's own org gets suspended, they must still be
    able to call platform endpoints (lifecycle gate is bypassed for this role).
    """
    from app.domains.auth.models import Organization, WorkspaceLifecycleState

    pa = await _register(client, org_name="PA SelfSus", org_slug="pa-selfsu-pa", email="pa-selfsu-pa@test.com")
    await _make_platform_admin(db, pa["user_id"])

    # Suspend the PLATFORM_ADMIN's own org
    await db.execute(
        update(Organization)
        .where(Organization.id == pa["org_id"])
        .values(lifecycle_state=WorkspaceLifecycleState.SUSPENDED)
    )
    await db.flush()

    # Must still be able to list orgs
    resp = await client.get("/api/v1/admin/orgs", headers=pa["headers"])
    assert resp.status_code == 200
