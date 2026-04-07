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
