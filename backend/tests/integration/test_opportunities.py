import pytest


@pytest.mark.asyncio
async def test_create_opportunity(client, auth_headers):
    resp = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "Rightsize VM fleet",
            "description": "VMs are over-provisioned by 60%",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 1200.0,
            "current_monthly_cost_usd": 4000.0,
            "service": "Virtual Machines",
            "environment": "production",
            "owner_team": "platform",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    op = resp.json()
    assert op["composite_score"] > 0
    assert op["estimated_annual_savings_usd"] == 1200.0 * 12
    assert op["playbook"] is not None
    assert op["score_rationale"] is not None


@pytest.mark.asyncio
async def test_list_and_filter_opportunities(client, auth_headers):
    # Create two
    for cat in ["idle_resources", "storage_optimization"]:
        await client.post(
            "/api/v1/opportunities",
            json={
                "title": f"Test {cat}",
                "description": "desc",
                "category": cat,
                "estimated_monthly_savings_usd": 500.0,
                "environment": "staging",
            },
            headers=auth_headers,
        )

    all_resp = await client.get("/api/v1/opportunities", headers=auth_headers)
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] >= 2

    filtered = await client.get(
        "/api/v1/opportunities?category=idle_resources", headers=auth_headers
    )
    assert filtered.status_code == 200
    assert all(o["category"] == "idle_resources" for o in filtered.json()["items"])


@pytest.mark.asyncio
async def test_update_opportunity_status(client, auth_headers):
    create = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "Status test",
            "description": "desc",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 300.0,
        },
        headers=auth_headers,
    )
    opp_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/opportunities/{opp_id}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_opportunity_summary(client, auth_headers):
    resp = await client.get("/api/v1/opportunities/summary", headers=auth_headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert "total" in summary
    assert "total_potential_savings_usd" in summary


@pytest.mark.asyncio
async def test_update_opportunity_status_writes_audit_events(client, auth_headers):
    async def _create(title: str) -> str:
        resp = await client.post(
            "/api/v1/opportunities",
            json={
                "title": title,
                "description": "desc",
                "category": "rightsizing",
                "estimated_monthly_savings_usd": 210.0,
                "current_monthly_cost_usd": 420.0,
                "resource_name": "vm-test-01",
                "environment": "prod",
                "owner_team": "finops",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    # accepted: resolved
    accepted_id = await _create("Accepted flow")
    accepted_resp = await client.patch(
        f"/api/v1/opportunities/{accepted_id}/status",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert accepted_resp.status_code == 200, accepted_resp.text

    # ignored: open -> dismissed
    ignored_id = await _create("Ignored flow")
    ignored_resp = await client.patch(
        f"/api/v1/opportunities/{ignored_id}/status",
        json={"status": "dismissed"},
        headers=auth_headers,
    )
    assert ignored_resp.status_code == 200, ignored_resp.text

    # dismissed: in_progress -> dismissed
    dismissed_id = await _create("Dismissed flow")
    to_progress = await client.patch(
        f"/api/v1/opportunities/{dismissed_id}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert to_progress.status_code == 200, to_progress.text
    dismissed_resp = await client.patch(
        f"/api/v1/opportunities/{dismissed_id}/status",
        json={"status": "dismissed"},
        headers=auth_headers,
    )
    assert dismissed_resp.status_code == 200, dismissed_resp.text

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_prefix=opportunity.",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    event_types = {e["event_type"] for e in events}

    assert "opportunity.accepted" in event_types
    assert "opportunity.ignored" in event_types
    assert "opportunity.dismissed" in event_types

    accepted_event = next(e for e in events if e["event_type"] == "opportunity.accepted")
    assert accepted_event["payload"]["new_status"] == "accepted"
    assert accepted_event["payload"]["previous_status"] == "detected"
    assert accepted_event["payload"]["recommendation_type"] == "RIGHTSIZING"
