"""SP-U02 + SP-U03: Admin-initiated MFA reset integration tests.

MFA reset is modeled as passkey revocation in the current passkey-first auth.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest


async def _register_get_token_and_id(client, suffix: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Org {suffix}",
            "org_slug": f"org-{suffix}",
            "email": f"admin-{suffix}@mfareset.com",
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
            "email": f"member-{role}-{suffix}@mfareset.com",
            "full_name": f"{role.title()} Member",
            "password": "memberpassword123",
            "role": role,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return {"user_id": resp.json()["id"]}


async def _add_passkeys(db, user_id: str, org_id: str, count: int = 2):
    from app.domains.auth.models import PasskeyCredential, User

    for i in range(count):
        db.add(
            PasskeyCredential(
                org_id=UUID(org_id),
                user_id=UUID(user_id),
                credential_id=f"cred-{user_id[:8]}-{i}",
                public_key_jwk='{"kty":"EC","crv":"P-256","x":"x","y":"y"}',
                sign_count=i,
                transports="internal",
                last_used_at=datetime.now(timezone.utc),
            )
        )

    user = await db.get(User, UUID(user_id))
    user.passkey_enabled = True
    await db.commit()


async def _elevate_to_platform_admin(db, user_id: str) -> None:
    from sqlalchemy import update

    from app.domains.auth.models import User, UserRole

    await db.execute(update(User).where(User.id == user_id).values(role=UserRole.PLATFORM_ADMIN))
    await db.commit()


@pytest.mark.asyncio
async def test_admin_resets_mfa_and_revokes_passkeys(client, db):
    ctx = await _register_get_token_and_id(client, "u02-a")
    member = await _create_member(client, ctx["headers"], "engineer", "u02-a")

    from app.domains.auth.models import User

    target = await db.get(User, UUID(member["user_id"]))
    await _add_passkeys(db, str(target.id), str(target.org_id), count=2)

    resp = await client.post(
        f"/api/v1/auth/users/{member['user_id']}/reset-mfa",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["revoked_passkeys"] == 2
    assert body["user"]["id"] == member["user_id"]
    assert body["user"]["passkey_enabled"] is False


@pytest.mark.asyncio
async def test_admin_cannot_reset_mfa_of_another_admin(client):
    ctx = await _register_get_token_and_id(client, "u02-b")
    second_admin = await _create_member(client, ctx["headers"], "admin", "u02-b")

    resp = await client.post(
        f"/api/v1/auth/users/{second_admin['user_id']}/reset-mfa",
        headers=ctx["headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_reset_mfa_cross_workspace(client, db):
    target_ctx = await _register_get_token_and_id(client, "u02-c-target")
    platform_ctx = await _register_get_token_and_id(client, "u02-c-platform")
    await _elevate_to_platform_admin(db, platform_ctx["user_id"])

    from app.domains.auth.models import User

    target_user = await db.get(User, UUID(target_ctx["user_id"]))
    await _add_passkeys(db, str(target_user.id), str(target_user.org_id), count=1)

    resp = await client.post(
        f"/api/v1/auth/users/{target_ctx['user_id']}/reset-mfa",
        headers=platform_ctx["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["revoked_passkeys"] == 1


@pytest.mark.asyncio
async def test_admin_cannot_reset_mfa_in_different_workspace(client):
    org_a = await _register_get_token_and_id(client, "u02-iso-a")
    org_b = await _register_get_token_and_id(client, "u02-iso-b")

    resp = await client.post(
        f"/api/v1/auth/users/{org_b['user_id']}/reset-mfa",
        headers=org_a["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_engineer_cannot_reset_mfa(client):
    ctx = await _register_get_token_and_id(client, "u02-eng")
    engineer = await _create_member(client, ctx["headers"], "engineer", "u02-eng")
    viewer = await _create_member(client, ctx["headers"], "viewer", "u02-eng-v")

    reset_pwd_resp = await client.post(
        f"/api/v1/auth/users/{engineer['user_id']}/reset-password",
        headers=ctx["headers"],
    )
    assert reset_pwd_resp.status_code == 200
    temp_pwd = reset_pwd_resp.json()["temporary_password"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "member-engineer-u02-eng@mfareset.com", "password": temp_pwd},
    )
    assert login_resp.status_code == 200
    eng_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = await client.post(
        f"/api/v1/auth/users/{viewer['user_id']}/reset-mfa",
        headers=eng_headers,
    )
    assert resp.status_code == 403
