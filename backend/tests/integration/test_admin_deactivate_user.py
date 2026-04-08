"""SP-U05: Admin member deactivation integration tests."""

import pytest
from sqlalchemy import update

from app.domains.auth.models import User, UserRole


async def _register(client, suffix: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Org {suffix}",
            "org_slug": f"org-{suffix}",
                "email": f"admin-{suffix}@deactivate.example.com",
            "full_name": "Admin",
            "password": "adminpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user_id": data["user"]["id"],
    }


async def _create_member(client, admin_headers: dict, role: str, suffix: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": f"member-{role}-{suffix}@deactivate.example.com",
            "full_name": f"{role.title()} Member",
            "password": "memberpassword123",
            "role": role,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return {"user_id": resp.json()["id"], "email": resp.json()["email"]}


@pytest.mark.asyncio
async def test_admin_can_deactivate_engineer(client):
    ctx = await _register(client, "u05-a")
    member = await _create_member(client, ctx["headers"], "engineer", "u05-a")

    deactivate_resp = await client.patch(
        f"/api/v1/auth/users/{member['user_id']}/deactivate",
        json={"reason": "Offboarding"},
        headers=ctx["headers"],
    )
    assert deactivate_resp.status_code == 200, deactivate_resp.text
    assert deactivate_resp.json()["is_active"] is False

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": member["email"], "password": "memberpassword123"},
    )
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_admin(client):
    ctx = await _register(client, "u05-b")
    member = await _create_member(client, ctx["headers"], "admin", "u05-b")

    deactivate_resp = await client.patch(
        f"/api/v1/auth/users/{member['user_id']}/deactivate",
        json={"reason": "Policy"},
        headers=ctx["headers"],
    )
    assert deactivate_resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_user_in_other_org(client):
    a = await _register(client, "u05-iso-a")
    b = await _register(client, "u05-iso-b")

    resp = await client.patch(
        f"/api/v1/auth/users/{b['user_id']}/deactivate",
        json={"reason": "Cross org attempt"},
        headers=a["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_platform_admin_can_deactivate_admin_cross_workspace(client, db):
    pa = await _register(client, "u05-pa")
    target = await _register(client, "u05-target")

    await db.execute(
        update(User).where(User.id == pa["user_id"]).values(role=UserRole.PLATFORM_ADMIN)
    )
    await db.commit()

    resp = await client.patch(
        f"/api/v1/auth/users/{target['user_id']}/deactivate",
        json={"reason": "Security incident"},
        headers=pa["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client):
    ctx = await _register(client, "u05-self")

    resp = await client.patch(
        f"/api/v1/auth/users/{ctx['user_id']}/deactivate",
        json={"reason": "Self lockout"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 403
