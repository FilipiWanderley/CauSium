"""
SP-MT01 — Cross-workspace isolation test suite.

Every test in this file proves that Org A cannot read, modify, or delete
resources that belong to Org B. Zero tolerance for cross-org data leakage.

Domains covered:
  - cloud_accounts
  - risk_budgets
  - workflow (initiatives)
  - change_events
  - audit_chain
  - invites
  - workspace lifecycle
"""
import pytest


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


# ---------------------------------------------------------------------------
# Cloud Accounts isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cloud_account_not_visible_to_other_org(client):
    a = await _register(client, org_name="A1", org_slug="iso-ca-a1", email="iso-ca-a1@test.com")
    b = await _register(client, org_name="B1", org_slug="iso-ca-b1", email="iso-ca-b1@test.com")

    create = await client.post("/api/v1/cloud-accounts", json={
        "provider": "azure",
        "external_id": "sub-iso-001",
        "display_name": "Org A Sub",
    }, headers=a["headers"])
    assert create.status_code == 201
    account_id = create.json()["id"]

    # Org B cannot see Org A's account in the list
    list_b = await client.get("/api/v1/cloud-accounts", headers=b["headers"])
    assert list_b.status_code == 200
    ids = [item["id"] for item in list_b.json()]
    assert account_id not in ids

    # Org B cannot fetch Org A's account by ID
    get_b = await client.get(f"/api/v1/cloud-accounts/{account_id}", headers=b["headers"])
    assert get_b.status_code == 404


@pytest.mark.asyncio
async def test_cloud_account_delete_not_allowed_by_other_org(client):
    a = await _register(client, org_name="A2", org_slug="iso-ca-del-a2", email="iso-ca-del-a2@test.com")
    b = await _register(client, org_name="B2", org_slug="iso-ca-del-b2", email="iso-ca-del-b2@test.com")

    create = await client.post("/api/v1/cloud-accounts", json={
        "provider": "azure",
        "external_id": "sub-iso-002",
        "display_name": "Org A Sub",
    }, headers=a["headers"])
    assert create.status_code == 201
    account_id = create.json()["id"]

    delete = await client.delete(f"/api/v1/cloud-accounts/{account_id}", headers=b["headers"])
    assert delete.status_code == 404


# ---------------------------------------------------------------------------
# Risk Budgets isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_risk_budget_not_visible_to_other_org(client):
    a = await _register(client, org_name="A3", org_slug="iso-rb-a3", email="iso-rb-a3@test.com")
    b = await _register(client, org_name="B3", org_slug="iso-rb-b3", email="iso-rb-b3@test.com")

    create = await client.post("/api/v1/risk-budgets", json={
        "name": "Org A Budget",
        "provider": "azure",
        "environment": "production",
        "monthly_limit_usd": 5000.0,
        "alert_threshold_pct": 80.0,
    }, headers=a["headers"])
    assert create.status_code == 201
    budget_id = create.json()["id"]

    list_b = await client.get("/api/v1/risk-budgets", headers=b["headers"])
    assert list_b.status_code == 200
    ids = [item["id"] for item in list_b.json()["items"]]
    assert budget_id not in ids

    get_b = await client.get(f"/api/v1/risk-budgets/{budget_id}", headers=b["headers"])
    assert get_b.status_code == 404


@pytest.mark.asyncio
async def test_risk_budget_update_not_allowed_by_other_org(client):
    a = await _register(client, org_name="A4", org_slug="iso-rb-upd-a4", email="iso-rb-upd-a4@test.com")
    b = await _register(client, org_name="B4", org_slug="iso-rb-upd-b4", email="iso-rb-upd-b4@test.com")

    create = await client.post("/api/v1/risk-budgets", json={
        "name": "A Budget",
        "provider": "azure",
        "environment": "staging",
        "monthly_limit_usd": 1000.0,
        "alert_threshold_pct": 90.0,
    }, headers=a["headers"])
    assert create.status_code == 201
    budget_id = create.json()["id"]

    patch = await client.patch(
        f"/api/v1/risk-budgets/{budget_id}",
        json={"name": "Hijacked"},
        headers=b["headers"],
    )
    assert patch.status_code == 404


# ---------------------------------------------------------------------------
# Workflow (Initiatives) isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initiative_not_visible_to_other_org(client):
    a = await _register(client, org_name="A5", org_slug="iso-wf-a5", email="iso-wf-a5@test.com")
    b = await _register(client, org_name="B5", org_slug="iso-wf-b5", email="iso-wf-b5@test.com")

    create = await client.post("/api/v1/initiatives", json={
        "title": "Org A Initiative",
        "description": "Secret cost saving",
    }, headers=a["headers"])
    assert create.status_code == 201
    initiative_id = create.json()["id"]

    # GET by ID — Org B must receive 404
    get_b = await client.get(f"/api/v1/initiatives/{initiative_id}", headers=b["headers"])
    assert get_b.status_code == 404

    # List — initiative must not appear for Org B
    list_b = await client.get("/api/v1/initiatives", headers=b["headers"])
    assert list_b.status_code == 200
    ids = [item["id"] for item in list_b.json()["items"]]
    assert initiative_id not in ids


@pytest.mark.asyncio
async def test_initiative_transition_not_allowed_by_other_org(client):
    a = await _register(client, org_name="A6", org_slug="iso-wf-tr-a6", email="iso-wf-tr-a6@test.com")
    b = await _register(client, org_name="B6", org_slug="iso-wf-tr-b6", email="iso-wf-tr-b6@test.com")

    create = await client.post("/api/v1/initiatives", json={
        "title": "Transition Target",
    }, headers=a["headers"])
    assert create.status_code == 201
    initiative_id = create.json()["id"]

    patch = await client.patch(
        f"/api/v1/initiatives/{initiative_id}/status",
        json={"status": "in_progress"},
        headers=b["headers"],
    )
    assert patch.status_code == 404


# ---------------------------------------------------------------------------
# Change Events isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_events_not_visible_to_other_org(client):
    a = await _register(client, org_name="A7", org_slug="iso-ce-a7", email="iso-ce-a7@test.com")
    b = await _register(client, org_name="B7", org_slug="iso-ce-b7", email="iso-ce-b7@test.com")

    create = await client.post("/api/v1/change-events", json={
        "event_type": "deployment",
        "title": "Org A Deploy",
        "environment": "production",
        "description": "secret deploy",
    }, headers=a["headers"])
    assert create.status_code == 201
    event_id = create.json()["id"]

    list_b = await client.get("/api/v1/change-events", headers=b["headers"])
    assert list_b.status_code == 200
    ids = [item["id"] for item in list_b.json()["items"]]
    assert event_id not in ids


# ---------------------------------------------------------------------------
# Audit Chain isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_events_not_visible_to_other_org(client):
    a = await _register(client, org_name="A8", org_slug="iso-au-a8", email="iso-au-a8@test.com")
    b = await _register(client, org_name="B8", org_slug="iso-au-b8", email="iso-au-b8@test.com")

    # Trigger at least one audit event for Org A
    await client.post("/api/v1/risk-budgets", json={
        "name": "Audit Trigger Budget",
        "provider": "azure",
        "environment": "dev",
        "monthly_limit_usd": 100.0,
        "alert_threshold_pct": 75.0,
    }, headers=a["headers"])

    list_a = await client.get("/api/v1/audit", headers=a["headers"])
    assert list_a.status_code == 200
    a_ids = {item["id"] for item in list_a.json()["items"]}

    list_b = await client.get("/api/v1/audit", headers=b["headers"])
    assert list_b.status_code == 200
    b_ids = {item["id"] for item in list_b.json()["items"]}

    # There must be zero overlap
    assert a_ids.isdisjoint(b_ids), (
        f"Audit log leakage detected! Shared event IDs: {a_ids & b_ids}"
    )


# ---------------------------------------------------------------------------
# Workspace — Admin cannot mutate another org's lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_lifecycle_scoped_to_own_org(client):
    a = await _register(client, org_name="A9", org_slug="iso-ws-a9", email="iso-ws-a9@test.com")
    b = await _register(client, org_name="B9", org_slug="iso-ws-b9", email="iso-ws-b9@test.com")

    # Org A admin cannot change Org B's lifecycle
    resp = await client.put(
        f"/api/v1/workspaces/{b['org_id']}/status",
        json={"lifecycle_state": "suspended", "reason": "hostile takeover"},
        headers=a["headers"],
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Invite isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invite_list_scoped_to_own_org(client):
    a = await _register(client, org_name="A10", org_slug="iso-inv-a10", email="iso-inv-a10@test.com")
    b = await _register(client, org_name="B10", org_slug="iso-inv-b10", email="iso-inv-b10@test.com")

    create = await client.post("/api/v1/invites", json={
        "email": "guest@secret.com",
        "role": "viewer",
    }, headers=a["headers"])
    assert create.status_code == 201
    invite_id = create.json()["id"]

    list_b = await client.get("/api/v1/invites", headers=b["headers"])
    assert list_b.status_code == 200
    ids = [item["id"] for item in list_b.json()["items"]]
    assert invite_id not in ids


@pytest.mark.asyncio
async def test_invite_revoke_scoped_to_own_org(client):
    a = await _register(client, org_name="A11", org_slug="iso-inv-rev-a11", email="iso-inv-rev-a11@test.com")
    b = await _register(client, org_name="B11", org_slug="iso-inv-rev-b11", email="iso-inv-rev-b11@test.com")

    create = await client.post("/api/v1/invites", json={
        "email": "victim@secret.com",
        "role": "viewer",
    }, headers=a["headers"])
    assert create.status_code == 201
    invite_id = create.json()["id"]

    # Org B tries to revoke Org A's invite
    delete = await client.delete(f"/api/v1/invites/{invite_id}", headers=b["headers"])
    assert delete.status_code == 404


# ---------------------------------------------------------------------------
# Suspended workspace blocks all access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suspended_workspace_blocks_api_access(client, db):
    """
    After a workspace is suspended, its own users must receive 403
    on any protected endpoint.
    """
    from sqlalchemy import update

    from app.domains.auth.models import Organization, WorkspaceLifecycleState

    org_data = await _register(
        client,
        org_name="Suspended Org",
        org_slug="iso-suspended-org",
        email="iso-suspended-user@test.com",
    )
    org_id = org_data["org_id"]
    headers = org_data["headers"]

    # Confirm access works before suspension
    before = await client.get("/api/v1/risk-budgets", headers=headers)
    assert before.status_code == 200

    # Directly suspend the org in DB (bypassing the lifecycle endpoint itself)
    await db.execute(
        update(Organization)
        .where(Organization.id == org_id)
        .values(lifecycle_state=WorkspaceLifecycleState.SUSPENDED)
    )
    await db.commit()

    after = await client.get("/api/v1/risk-budgets", headers=headers)
    assert after.status_code == 403
