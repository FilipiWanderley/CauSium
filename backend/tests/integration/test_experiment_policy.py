import uuid

import pytest


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_high_risk_experiment_requires_dual_approval_and_contextual_policy(client, auth_headers):
    create_exp = await client.post(
        "/api/v1/experiments",
        json={
            "title": "High risk production canary",
            "target_environment": "production",
            "target_criticality": "critical",
            "guardrails": {
                "max_blast_radius_pct": 0.3,
                "rollback_on_error_rate": 0.02,
                "max_cost_increase_pct": 0.1,
                "require_approval": True,
            },
        },
        headers=auth_headers,
    )
    assert create_exp.status_code == 201, create_exp.text
    exp_id = create_exp.json()["id"]

    for next_status in ["hypothesis", "simulating", "approved"]:
        moved = await client.post(
            f"/api/v1/experiments/{exp_id}/transition",
            json={"status": next_status},
            headers=auth_headers | {"X-Session-Risk": "low"},
        )
        assert moved.status_code == 200, moved.text

    no_context_run = await client.post(
        f"/api/v1/experiments/{exp_id}/transition",
        json={"status": "running"},
        headers=auth_headers,
    )
    assert no_context_run.status_code == 403
    assert "policy_decision_id" in no_context_run.json()["detail"]

    created_emails = []
    for suffix in ["eng1", "eng2"]:
        email = f"{suffix}-{uuid.uuid4().hex[:8]}@example.com"
        created = await client.post(
            "/api/v1/auth/users",
            json={
                "email": email,
                "full_name": f"Engineer {suffix}",
                "password": "securepass123",
                "role": "engineer",
            },
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text
        created_emails.append(email)

    eng1_email, eng2_email = created_emails
    eng1_headers = await _login(client, eng1_email, "securepass123")
    eng2_headers = await _login(client, eng2_email, "securepass123")

    owner_approval = await client.post(
        f"/api/v1/experiments/{exp_id}/approvals",
        json={"note": "owner attempting approval"},
        headers=auth_headers | {"X-Session-Risk": "low"},
    )
    assert owner_approval.status_code == 400

    approved_1 = await client.post(
        f"/api/v1/experiments/{exp_id}/approvals",
        json={"note": "risk reviewed"},
        headers=eng1_headers | {"X-Session-Risk": "low", "X-Device-Trusted": "true"},
    )
    assert approved_1.status_code == 201, approved_1.text
    assert approved_1.headers.get("X-Policy-Decision-Id")

    approved_2 = await client.post(
        f"/api/v1/experiments/{exp_id}/approvals",
        json={"note": "sre approval"},
        headers=eng2_headers | {"X-Session-Risk": "low", "X-Device-Trusted": "true"},
    )
    assert approved_2.status_code == 201, approved_2.text
    assert approved_2.headers.get("X-Policy-Decision-Id")

    without_maintenance = await client.post(
        f"/api/v1/experiments/{exp_id}/transition",
        json={"status": "running"},
        headers=auth_headers | {"X-Session-Risk": "low", "X-Maintenance-Window": "false"},
    )
    assert without_maintenance.status_code == 403
    assert "policy_decision_id" in without_maintenance.json()["detail"]

    with_maintenance = await client.post(
        f"/api/v1/experiments/{exp_id}/transition",
        json={"status": "running"},
        headers=auth_headers | {"X-Session-Risk": "low", "X-Maintenance-Window": "true"},
    )
    assert with_maintenance.status_code == 200, with_maintenance.text
    assert with_maintenance.headers.get("X-Policy-Decision-Id")

    audit_events = await client.get("/api/v1/audit-chain/events?event_type=policy.decision.recorded", headers=auth_headers)
    assert audit_events.status_code == 200, audit_events.text
    assert len(audit_events.json()) >= 1
