"""Integration tests for TOTP backup codes (SP-A06).

Covers:
- enable returns backup_codes list
- GET backup-codes/count reflects remaining count
- POST backup-codes/regenerate replaces codes
- Login with backup code succeeds (one-time use)
- Reusing the same backup code fails
- Admin MFA reset wipes backup codes
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time

import pytest


def _totp_now(secret_b32: str) -> str:
    key = base64.b32decode(secret_b32 + ("=" * (-len(secret_b32) % 8)), casefold=True)
    counter = int(time.time() // 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    dbc = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{dbc % 1_000_000:06d}"


async def _register_and_enable_totp(client) -> tuple[dict, str, list[str]]:
    """Helper: register user, enable TOTP, return (headers, secret, backup_codes)."""
    from uuid import uuid4
    suffix = uuid4().hex[:8]
    password = "BackupPass123!"
    reg = await client.post("/api/v1/auth/register", json={
        "org_name": f"BackupOrg {suffix}",
        "org_slug": f"backup-org-{suffix}",
        "email": f"backup-{suffix}@test.com",
        "full_name": "Backup User",
        "password": password,
    })
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    email = reg.json()["user"]["email"]

    setup = await client.post("/api/v1/auth/mfa/totp/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": _totp_now(secret)},
        headers=headers,
    )
    assert enable.status_code == 200, enable.text
    backup_codes = enable.json()["backup_codes"]
    return headers, secret, backup_codes, email, password


@pytest.mark.asyncio
async def test_enable_totp_returns_backup_codes(client):
    headers, _secret, backup_codes, *_ = await _register_and_enable_totp(client)

    assert len(backup_codes) == 8
    for code in backup_codes:
        assert "-" in code, f"Expected XXXXX-XXXXX format, got {code}"


@pytest.mark.asyncio
async def test_backup_codes_count_reflects_remaining(client):
    headers, _secret, backup_codes, *_ = await _register_and_enable_totp(client)

    resp = await client.get("/api/v1/auth/mfa/totp/backup-codes/count", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["backup_codes_remaining"] == 8


@pytest.mark.asyncio
async def test_login_with_backup_code_succeeds_and_is_one_time(client):
    _headers, _secret, backup_codes, email, password = await _register_and_enable_totp(client)
    code_to_use = backup_codes[0]

    # First use: should succeed
    login1 = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "totp_code": code_to_use,
    })
    assert login1.status_code == 200, login1.text

    # Second use of the same code: must fail
    login2 = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "totp_code": code_to_use,
    })
    assert login2.status_code == 401, login2.text


@pytest.mark.asyncio
async def test_backup_codes_count_decrements_after_use(client):
    _headers, _secret, backup_codes, email, password = await _register_and_enable_totp(client)

    # Use first backup code to login
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "totp_code": backup_codes[0],
    })
    assert login.status_code == 200, login.text
    new_token = login.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    count = await client.get("/api/v1/auth/mfa/totp/backup-codes/count", headers=new_headers)
    assert count.status_code == 200, count.text
    assert count.json()["backup_codes_remaining"] == 7


@pytest.mark.asyncio
async def test_regenerate_backup_codes_replaces_old_ones(client):
    headers, secret, old_codes, email, password = await _register_and_enable_totp(client)

    regen = await client.post(
        "/api/v1/auth/mfa/totp/backup-codes/regenerate",
        json={"code": _totp_now(secret)},
        headers=headers,
    )
    assert regen.status_code == 200, regen.text
    new_codes = regen.json()["backup_codes"]

    assert len(new_codes) == 8
    # New codes must be different from the old ones
    assert set(new_codes) != set(old_codes)

    # Old code must no longer work
    login_old = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "totp_code": old_codes[0],
    })
    assert login_old.status_code == 401, login_old.text

    # New code must work
    login_new = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
        "totp_code": new_codes[0],
    })
    assert login_new.status_code == 200, login_new.text


@pytest.mark.asyncio
async def test_admin_mfa_reset_wipes_backup_codes(client, db):
    from uuid import UUID
    from sqlalchemy import select
    from app.domains.auth.models import TotpBackupCode, User

    headers, _secret, _codes, email, _pw = await _register_and_enable_totp(client)

    # Get user_id from DB
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user_id = str(user.id)

    # Admin resets MFA for this user (admin is the same user — they own the org)
    reset = await client.post(f"/api/v1/auth/users/{user_id}/reset-mfa", headers=headers)
    assert reset.status_code == 200, reset.text
    assert reset.json()["totp_disabled"] is True

    # Backup codes must be gone
    codes = await db.execute(
        select(TotpBackupCode).where(TotpBackupCode.user_id == UUID(user_id))
    )
    assert codes.scalars().all() == []
