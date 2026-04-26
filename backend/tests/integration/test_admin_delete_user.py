"""Admin delete user anonymization integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.auth.models import User


async def _register(client, suffix: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Org {suffix}",
            "org_slug": f"org-del-{suffix}",
            "email": f"admin-{suffix}@delete.example.com",
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


async def _create_member(client, admin_headers: dict, suffix: str) -> dict:
    email = f"member-{suffix}@delete.example.com"
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": email,
            "full_name": "Member To Delete",
            "password": "memberpassword123",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return {"user_id": resp.json()["id"], "email": email}


@pytest.mark.asyncio
async def test_admin_delete_user_anonymizes_email(client, db):
    ctx = await _register(client, "anon-a")
    member = await _create_member(client, ctx["headers"], "anon-a")

    delete_resp = await client.request(
        "DELETE",
        f"/api/v1/auth/users/{member['user_id']}",
        json={"reason": "LGPD delete"},
        headers=ctx["headers"],
    )
    assert delete_resp.status_code == 200, delete_resp.text
    payload = delete_resp.json()
    assert payload["is_active"] is False
    assert payload["email"] != member["email"]
    assert payload["email"].endswith("@deleted.invalid")
    assert payload["full_name"] == "Deleted User"

    result = await db.execute(select(User).where(User.id == member["user_id"]))
    deleted_user = result.scalar_one()
    assert deleted_user.email != member["email"]

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=auth.user.deleted",
        headers=ctx["headers"],
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    matching = [e for e in events if e["entity_id"] == member["user_id"]]
    assert len(matching) == 1
    event_payload = matching[0]["payload"]
    assert event_payload["target_user_id"] == member["user_id"]
    assert "target_email" not in event_payload
