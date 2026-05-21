"""Integration tests for LGPD endpoints (SP-LGPD).

Covers:
- GET /auth/me/export returns user profile data
- DELETE /auth/me/data anonymises the account and blocks future access
- Invite accept requires terms_accepted=True
- Invite accept without terms returns 422
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_export_my_data_returns_profile(client, auth_headers):
    resp = await client.get("/api/v1/auth/me/export", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "profile" in data
    assert "email" in data["profile"]
    assert "mfa" in data
    assert "passkeys" in data


@pytest.mark.asyncio
async def test_purge_my_data_anonymises_and_blocks_access(client):
    from uuid import uuid4
    suffix = uuid4().hex[:8]
    password = "PurgePass123!"

    reg = await client.post("/api/v1/auth/register", json={
        "org_name": f"PurgeOrg {suffix}",
        "org_slug": f"purge-org-{suffix}",
        "email": f"purge-{suffix}@test.com",
        "full_name": "Purge User",
        "password": password,
    })
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    email = reg.json()["user"]["email"]

    purge = await client.delete("/api/v1/auth/me/data", headers=headers)
    assert purge.status_code == 204, purge.text

    # Access with old token must now fail (user anonymised/inactive)
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code in (401, 403)

    # Login with original credentials must fail
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert login.status_code in (401, 403, 404)


@pytest.mark.asyncio
async def test_invite_accept_requires_terms_accepted(client, auth_headers):
    create = await client.post(
        "/api/v1/invites",
        headers=auth_headers,
        json={"email": "lgpd-terms@example.com", "role": "viewer", "expires_in_days": 7},
    )
    assert create.status_code == 201, create.text
    token = create.json()["token"]

    # Accept without terms_accepted — must be rejected
    no_terms = await client.post(f"/api/v1/invites/{token}/accept", json={
        "full_name": "LGPD User",
        "password": "LGPDPass123!",
        "terms_accepted": False,
    })
    assert no_terms.status_code == 422, no_terms.text

    # Accept without the field at all — must also be rejected
    missing_terms = await client.post(f"/api/v1/invites/{token}/accept", json={
        "full_name": "LGPD User",
        "password": "LGPDPass123!",
    })
    assert missing_terms.status_code == 422, missing_terms.text


@pytest.mark.asyncio
async def test_invite_accept_with_terms_records_consent(client, auth_headers, db):
    from sqlalchemy import select
    from app.domains.auth.models import User

    create = await client.post(
        "/api/v1/invites",
        headers=auth_headers,
        json={"email": "lgpd-consent@example.com", "role": "viewer", "expires_in_days": 7},
    )
    assert create.status_code == 201, create.text
    token = create.json()["token"]

    accept = await client.post(f"/api/v1/invites/{token}/accept", json={
        "full_name": "Consent User",
        "password": "ConsentPass123!",
        "terms_accepted": True,
    })
    assert accept.status_code == 201, accept.text

    result = await db.execute(select(User).where(User.email == "lgpd-consent@example.com"))
    user = result.scalar_one()
    assert user.terms_accepted_at is not None
    assert user.terms_version is not None
