from __future__ import annotations

from uuid import UUID

import pytest


def _totp_now(secret_b32: str) -> str:
    import base64
    import hashlib
    import hmac
    import struct
    import time

    key = base64.b32decode(secret_b32 + ("=" * (-len(secret_b32) % 8)), casefold=True)
    counter = int(time.time() // 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    dbc = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    otp = dbc % 1_000_000
    return f"{otp:06d}"


@pytest.mark.asyncio
async def test_totp_setup_verify_enable_disable_flow(client, auth_headers):
    status_before = await client.get("/api/v1/auth/mfa/totp/status", headers=auth_headers)
    assert status_before.status_code == 200
    assert status_before.json()["enabled"] is False

    setup = await client.post("/api/v1/auth/mfa/totp/setup", headers=auth_headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_url"].startswith("otpauth://totp/")

    code = _totp_now(secret)
    verify = await client.post(
        "/api/v1/auth/mfa/totp/verify",
        json={"code": code},
        headers=auth_headers,
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["valid"] is True

    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": _totp_now(secret)},
        headers=auth_headers,
    )
    assert enable.status_code == 200, enable.text
    assert enable.json()["enabled"] is True

    status_after = await client.get("/api/v1/auth/mfa/totp/status", headers=auth_headers)
    assert status_after.status_code == 200
    assert status_after.json()["enabled"] is True

    disable = await client.post(
        "/api/v1/auth/mfa/totp/disable",
        json={"code": _totp_now(secret)},
        headers=auth_headers,
    )
    assert disable.status_code == 200, disable.text
    assert disable.json()["enabled"] is False


@pytest.mark.asyncio
async def test_login_requires_totp_code_when_enabled(client):
    suffix = "totp-login"
    password = "strongpassword123"
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "TOTP Org",
            "org_slug": f"totp-org-{suffix}",
            "email": f"admin-{suffix}@totp.com",
            "full_name": "TOTP Admin",
            "password": password,
        },
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    setup = await client.post("/api/v1/auth/mfa/totp/setup", headers=headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]

    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": _totp_now(secret)},
        headers=headers,
    )
    assert enable.status_code == 200, enable.text

    login_no_totp = await client.post(
        "/api/v1/auth/login",
        json={"email": f"admin-{suffix}@totp.com", "password": password},
    )
    assert login_no_totp.status_code == 401
    assert "MFA code required" in login_no_totp.json()["detail"]

    login_bad_totp = await client.post(
        "/api/v1/auth/login",
        json={"email": f"admin-{suffix}@totp.com", "password": password, "totp_code": "000000"},
    )
    assert login_bad_totp.status_code == 401

    login_ok = await client.post(
        "/api/v1/auth/login",
        json={
            "email": f"admin-{suffix}@totp.com",
            "password": password,
            "totp_code": _totp_now(secret),
        },
    )
    assert login_ok.status_code == 200, login_ok.text


@pytest.mark.asyncio
async def test_admin_reset_mfa_disables_target_totp(client, db):
    register_admin = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Reset MFA Org",
            "org_slug": "reset-mfa-org-totp",
            "email": "admin-reset-totp@sp.com",
            "full_name": "Admin",
            "password": "adminpassword123",
        },
    )
    assert register_admin.status_code == 201, register_admin.text
    admin_headers = {"Authorization": f"Bearer {register_admin.json()['access_token']}"}

    create_member = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "member-reset-totp@sp.com",
            "full_name": "Member",
            "password": "memberpassword123",
            "role": "engineer",
        },
        headers=admin_headers,
    )
    assert create_member.status_code == 201, create_member.text
    member_id = create_member.json()["id"]

    from app.core.security import encrypt_secret
    from app.domains.auth.models import User

    target = await db.get(User, UUID(member_id))
    target.totp_secret_encrypted = encrypt_secret("JBSWY3DPEHPK3PXP")
    target.totp_enabled = True
    await db.commit()

    reset = await client.post(
        f"/api/v1/auth/users/{member_id}/reset-mfa",
        headers=admin_headers,
    )
    assert reset.status_code == 200, reset.text
    assert reset.json()["totp_disabled"] is True
    assert reset.json()["user"]["totp_enabled"] is False
