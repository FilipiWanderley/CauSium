import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_audit_chain_registers_experiment_events(client, auth_headers):
    created = await client.post(
        "/api/v1/experiments",
        json={
            "title": "Canary rightsizing API cluster",
            "hypothesis": "Reducing VM size keeps SLO and lowers cost",
            "guardrails": {
                "max_blast_radius_pct": 0.15,
                "rollback_on_error_rate": 0.03,
                "max_cost_increase_pct": 0.05,
                "require_approval": True,
            },
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    exp = created.json()
    exp_id = exp["id"]

    for next_status in ["hypothesis", "simulating", "approved", "running"]:
        transitioned = await client.post(
            f"/api/v1/experiments/{exp_id}/transition",
            json={"status": next_status},
            headers=auth_headers,
        )
        assert transitioned.status_code == 200, transitioned.text

    run_created = await client.post(
        f"/api/v1/experiments/{exp_id}/runs",
        json={"run_type": "canary", "notes": "initial canary run"},
        headers=auth_headers,
    )
    assert run_created.status_code == 201, run_created.text
    run_id = run_created.json()["id"]

    run_updated = await client.patch(
        f"/api/v1/experiments/{exp_id}/runs/{run_id}",
        json={
            "status": "completed",
            "impact_usd": 1200.5,
            "metrics_after": {"latency_p95_ms": 340},
            "error_rate_after": 0.004,
        },
        headers=auth_headers,
    )
    assert run_updated.status_code == 200, run_updated.text

    events_resp = await client.get("/api/v1/audit-chain/events", headers=auth_headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 6
    assert any(e["event_type"] == "experiment.created" for e in events)
    assert any(e["event_type"] == "experiment.transitioned" for e in events)
    assert any(e["event_type"] == "experiment.run.created" for e in events)
    assert any(e["event_type"] == "experiment.run.updated" for e in events)

    verify_resp = await client.get("/api/v1/audit-chain/verify", headers=auth_headers)
    assert verify_resp.status_code == 200
    verification = verify_resp.json()
    assert verification["is_valid"] is True
    assert verification["checked_events"] >= 6

    checkpoint_created = await client.post("/api/v1/audit-chain/checkpoints", headers=auth_headers)
    assert checkpoint_created.status_code == 200, checkpoint_created.text
    checkpoint = checkpoint_created.json()
    assert checkpoint["checked_events"] >= 6

    checkpoint_list = await client.get("/api/v1/audit-chain/checkpoints", headers=auth_headers)
    assert checkpoint_list.status_code == 200
    assert len(checkpoint_list.json()) >= 1

    checkpoint_verify = await client.get(
        f"/api/v1/audit-chain/checkpoints/{checkpoint['id']}/verify",
        headers=auth_headers,
    )
    assert checkpoint_verify.status_code == 200, checkpoint_verify.text
    checkpoint_verification = checkpoint_verify.json()
    assert checkpoint_verification["is_signature_valid"] is True
    assert checkpoint_verification["is_chain_valid"] is True

    checkpoint_created_2 = await client.post("/api/v1/audit-chain/checkpoints", headers=auth_headers)
    assert checkpoint_created_2.status_code == 200, checkpoint_created_2.text
    cleanup = await client.delete("/api/v1/audit-chain/checkpoints/retention?keep_last=1", headers=auth_headers)
    assert cleanup.status_code == 200, cleanup.text
    cleanup_body = cleanup.json()
    assert cleanup_body["deleted_count"] >= 1
    assert cleanup_body["kept_count"] == 1

    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    future = (now + timedelta(days=1)).isoformat()
    auth_all = await client.get(f"/api/v1/audit-chain/events/auth?created_after={past}", headers=auth_headers)
    assert auth_all.status_code == 200, auth_all.text
    auth_none = await client.get(f"/api/v1/audit-chain/events/auth?created_after={future}", headers=auth_headers)
    assert auth_none.status_code == 200, auth_none.text
    assert len(auth_all.json()) >= 1
    assert auth_none.json() == []
