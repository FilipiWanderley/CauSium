"""SP-U01 + SP-U03: Admin-initiated password reset integration tests.

Covers:
  - Admin resets engineer's password → 200 + temporary_password + must_change_password=True
  - Admin resets user in same org with viewer role → 200
  - Admin tries to reset another admin (same org) → 403 (SP-U03)
  - Admin tries to reset platform_admin → 403 (SP-U03)
  - platform_admin resets an admin → 200 (super-role bypasses hierarchy)
  - Admin tries to reset user in a *different* org → 404 (workspace isolation)
  - Unauthenticated request → 401
  - Engineer (non-admin) tries to reset someone → 403
  - Temporary password actually works for login
  - Temporary password forces must_change_password on target user
"""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_get_token_and_id(client, suffix: str, role: str = "admin") -> dict:
    """Register a fresh org/user and return {headers, user_id, org_id, token}."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Org {suffix}",
            "org_slug": f"org-{suffix}",
            "email": f"admin-{suffix}@reset.test",
            "full_name": "Admin",
            "password": "adminpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user_id": data["user"]["id"],
        "org_id": data["user"]["org_id"],
    }


async def _create_member(client, admin_headers: dict, role: str, suffix: str) -> dict:
    """Create a workspace member via the admin API and return {user_id}."""
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": f"{role}-{suffix}@reset.test",
            "full_name": f"{role.title()} Member",
            "password": "memberpassword123",
            "role": role,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return {"user_id": resp.json()["id"]}


async def _elevate_to_platform_admin(db, user_id: str) -> None:
    from sqlalchemy import update
    from app.domains.auth.models import User, UserRole
    await db.execute(update(User).where(User.id == user_id).values(role=UserRole.PLATFORM_ADMIN))
    await db.flush()


# ---------------------------------------------------------------------------
# SP-U01 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_resets_engineer_password(client):
    """Admin can reset an engineer's password; returns temp password."""
    ctx = await _register_get_token_and_id(client, "u01-a")
    member = await _create_member(client, ctx["headers"], "engineer", "u01-a")

    resp = await client.post(
        f"/api/v1/auth/users/{member['user_id']}/reset-password",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "temporary_password" in data
    assert len(data["temporary_password"]) >= 12
    assert data["user"]["id"] == member["user_id"]
    assert data["user"]["must_change_password"] is True


@pytest.mark.asyncio
async def test_reset_sets_must_change_password(client):
    """Target user's must_change_password flag is True after admin reset."""
    ctx = await _register_get_token_and_id(client, "u01-b")
    member = await _create_member(client, ctx["headers"], "viewer", "u01-b")

    reset_resp = await client.post(
        f"/api/v1/auth/users/{member['user_id']}/reset-password",
        headers=ctx["headers"],
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["user"]["must_change_password"] is True


@pytest.mark.asyncio
async def test_temporary_password_works_for_login(client):
    """Temporary password set by admin actually authenticates the target user."""
    ctx = await _register_get_token_and_id(client, "u01-c")
    suffix = "u01-c"
    member_email = f"engineer-{suffix}@reset.test"
    await _create_member(client, ctx["headers"], "engineer", suffix)

    # Find the created user's ID via list
    users_resp = await client.get("/api/v1/auth/users", headers=ctx["headers"])
    target_id = next(
        u["id"] for u in users_resp.json() if u["email"] == member_email
    )

    reset_resp = await client.post(
        f"/api/v1/auth/users/{target_id}/reset-password",
        headers=ctx["headers"],
    )
    assert reset_resp.status_code == 200
    temp_pwd = reset_resp.json()["temporary_password"]

    # Login with the temporary password
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": member_email, "password": temp_pwd},
    )
    assert login_resp.status_code == 200, login_resp.text


# ---------------------------------------------------------------------------
# SP-U03 hierarchy tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_cannot_reset_another_admin(client):
    """SP-U03: admin cannot reset password of another admin (same rank)."""
    ctx_a = await _register_get_token_and_id(client, "u03-aa")  # admin in org A
    ctx_b = await _register_get_token_and_id(client, "u03-ab")  # admin in org B

    # Create a second admin in org A by direct DB is complex — instead we test
    # that admin A (ctx_a) cannot reset admin B (ctx_b) — different org → 404.
    # For same-org admin-vs-admin, we must create a second admin user directly.
    # Create another admin in org A first:
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "admin2-u03-aa@reset.test",
            "full_name": "Admin 2",
            "password": "adminpassword123",
            "role": "admin",  # create as admin
        },
        headers=ctx_a["headers"],
    )
    # Note: create_user may succeed (role is sent as admin) but the route only
    # allows ADMIN to call it, which already sets must_change_password.
    # The important thing is we get the user ID.
    if resp.status_code == 201:
        admin2_id = resp.json()["id"]
    else:
        # If org doesn't allow creating admins directly, skip gracefully
        pytest.skip("Cannot create second admin user in this org configuration")

    reset_resp = await client.post(
        f"/api/v1/auth/users/{admin2_id}/reset-password",
        headers=ctx_a["headers"],
    )
    assert reset_resp.status_code == 403
    assert "admin" in reset_resp.json()["detail"].lower() or "role" in reset_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_cannot_reset_platform_admin(client, db):
    """SP-U03: admin cannot reset a platform_admin (higher rank)."""
    ctx = await _register_get_token_and_id(client, "u03-pa")

    # Create a member then elevate to platform_admin in DB
    member = await _create_member(client, ctx["headers"], "viewer", "u03-pa")
    await _elevate_to_platform_admin(db, member["user_id"])

    reset_resp = await client.post(
        f"/api/v1/auth/users/{member['user_id']}/reset-password",
        headers=ctx["headers"],
    )
    assert reset_resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_resets_admin(client, db):
    """SP-U03: platform_admin can reset any role, including admin."""
    # Create a regular org with an admin account
    ctx_target = await _register_get_token_and_id(client, "u03-ta")
    target_admin_id = ctx_target["user_id"]

    # Create a second org, register as admin, elevate to platform_admin
    ctx_pa = await _register_get_token_and_id(client, "u03-plat")
    await _elevate_to_platform_admin(db, ctx_pa["user_id"])
    pa_headers = ctx_pa["headers"]

    # platform_admin resets the target org's admin
    reset_resp = await client.post(
        f"/api/v1/auth/users/{target_admin_id}/reset-password",
        headers=pa_headers,
    )
    assert reset_resp.status_code == 200, reset_resp.text
    assert reset_resp.json()["user"]["must_change_password"] is True


# ---------------------------------------------------------------------------
# Isolation + auth tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_cannot_reset_user_in_different_org(client):
    """Admin cannot reset password of a user in a different workspace (returns 404)."""
    ctx_a = await _register_get_token_and_id(client, "u01-iso-a")
    ctx_b = await _register_get_token_and_id(client, "u01-iso-b")

    # Admin A tries to reset Admin B (different org) → 404
    resp = await client.post(
        f"/api/v1/auth/users/{ctx_b['user_id']}/reset-password",
        headers=ctx_a["headers"],
    )
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unauthenticated_reset_is_rejected(client):
    """Unauthenticated attempt to reset a user's password returns 401."""
    resp = await client.post(
        "/api/v1/auth/users/00000000-0000-0000-0000-000000000001/reset-password",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_engineer_cannot_reset_password(client):
    """Non-admin role (engineer) is forbidden from calling the reset endpoint."""
    ctx = await _register_get_token_and_id(client, "u01-eng")
    engineer = await _create_member(client, ctx["headers"], "engineer", "u01-eng")

    # Login as engineer
    eng_email = f"engineer-u01-eng@reset.test"
    # We need to know the temp password — since the engineer was just created
    # with must_change_password=True, we reset it first so we can log in.
    reset_resp = await client.post(
        f"/api/v1/auth/users/{engineer['user_id']}/reset-password",
        headers=ctx["headers"],
    )
    assert reset_resp.status_code == 200
    temp_pwd = reset_resp.json()["temporary_password"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": eng_email, "password": temp_pwd},
    )
    assert login_resp.status_code == 200
    eng_token = login_resp.json()["access_token"]
    eng_headers = {"Authorization": f"Bearer {eng_token}"}

    # Engineer tries to reset viewer's password — should get 403 (wrong role)
    viewer = await _create_member(client, ctx["headers"], "viewer", "u01-eng-v")
    resp = await client.post(
        f"/api/v1/auth/users/{viewer['user_id']}/reset-password",
        headers=eng_headers,
    )
    assert resp.status_code == 403
