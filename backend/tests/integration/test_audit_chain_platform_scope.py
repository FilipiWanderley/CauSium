import pytest
from sqlalchemy import update

from app.domains.auth.models import User, UserRole


@pytest.mark.asyncio
async def test_platform_admin_can_query_audit_events_for_another_workspace(client, db):
    org_a = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org A Scope",
            "org_slug": "org-a-scope-audit",
            "email": "admin-a-scope-audit@example.com",
            "full_name": "Admin A",
            "password": "password12345",
        },
    )
    assert org_a.status_code == 201, org_a.text
    org_a_data = org_a.json()

    org_b = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org B Scope",
            "org_slug": "org-b-scope-audit",
            "email": "admin-b-scope-audit@example.com",
            "full_name": "Admin B",
            "password": "password12345",
        },
    )
    assert org_b.status_code == 201, org_b.text
    org_b_data = org_b.json()

    await db.execute(
        update(User)
        .where(User.id == org_a_data["user"]["id"])
        .values(role=UserRole.PLATFORM_ADMIN)
    )
    await db.commit()

    pa_headers = {"Authorization": f"Bearer {org_a_data['access_token']}"}
    target_org_id = org_b_data["user"]["org_id"]

    resp = await client.get(
        f"/api/v1/audit-chain/events/auth?org_id={target_org_id}",
        headers=pa_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(event["org_id"] == target_org_id for event in body["items"])


@pytest.mark.asyncio
async def test_non_platform_admin_cannot_query_audit_events_for_another_workspace(client):
    org_a = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org A Scope 2",
            "org_slug": "org-a-scope-audit-2",
            "email": "admin-a-scope-audit-2@example.com",
            "full_name": "Admin A2",
            "password": "password12345",
        },
    )
    assert org_a.status_code == 201, org_a.text
    org_a_data = org_a.json()

    org_b = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Org B Scope 2",
            "org_slug": "org-b-scope-audit-2",
            "email": "admin-b-scope-audit-2@example.com",
            "full_name": "Admin B2",
            "password": "password12345",
        },
    )
    assert org_b.status_code == 201, org_b.text
    org_b_data = org_b.json()

    admin_headers = {"Authorization": f"Bearer {org_a_data['access_token']}"}
    target_org_id = org_b_data["user"]["org_id"]

    resp = await client.get(
        f"/api/v1/audit-chain/events/auth?org_id={target_org_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 403
