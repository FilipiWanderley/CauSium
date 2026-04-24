import pytest


async def _create_opportunity(client, headers, payload: dict) -> dict:
    resp = await client.post("/api/v1/opportunities", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_execution_plan_requires_review_and_returns_checklist(client, auth_headers):
    first = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Rightsize VM batch workers",
            "description": "Low sustained usage on workers.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 900.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    second = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Lifecycle optimization for backups",
            "description": "Move cold backups to lower storage tier.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 420.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [first["id"], second["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "review_required"
    assert data["mode"] == "manual_review"
    assert data["total_savings_monthly"] > 0
    assert data["risk_level"] in {"low", "medium", "high"}
    assert len(data["checklist"]) >= 3
    assert any("sem automacao" in step.lower() for step in data["steps"])


@pytest.mark.asyncio
async def test_create_execution_plan_flags_aks_conflict_gate(client, auth_headers):
    op1 = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS nodepool rightsizing np-app",
            "description": "Reduce baseline node count.",
            "category": "aks_nodepool_rightsizing",
            "resource_id": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 510.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )
    op2 = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS autoscaler recommendation np-app",
            "description": "Tune min/max autoscaler range.",
            "category": "aks_autoscaler_recommendation",
            "resource_id": "/subscriptions/x/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 370.0,
            "risk_level": "medium",
            "effort_level": "medium",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [op1["id"], op2["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "review_required"
    assert "aks_conflict_same_nodepool" in data["gates_triggered"]
    assert len(data["conflicts"]) == 1


@pytest.mark.asyncio
async def test_create_execution_plan_blocks_non_positive_savings(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Low value recommendation",
            "description": "No actual savings expected.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 0.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={
            "opportunity_ids": [op["id"]],
            "mode": "manual_review",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "blocked"
    assert "non_positive_savings" in data["gates_triggered"]


@pytest.mark.asyncio
async def test_create_execution_plan_persists_and_is_queryable(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Persisted execution plan candidate",
            "description": "Recommendation to validate persistence artifact.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 215.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    create_resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={"opportunity_ids": [op["id"]], "mode": "manual_review"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()

    get_resp = await client.get(
        f"/api/v1/intel/execution-plan/{created['execution_plan_id']}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()

    assert fetched["execution_plan_id"] == created["execution_plan_id"]
    assert fetched["selected_opportunity_ids"] == [op["id"]]
    assert fetched["status"] == created["status"]
    assert fetched["risk_level"] == created["risk_level"]
    assert fetched["total_savings_monthly"] == created["total_savings_monthly"]


@pytest.mark.asyncio
async def test_create_execution_plan_emits_audit_event(client, auth_headers):
    op = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Audited execution plan candidate",
            "description": "Should register audit chain event on plan creation.",
            "category": "idle_resources",
            "estimated_monthly_savings_usd": 180.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    create_resp = await client.post(
        "/api/v1/intel/execution-plan",
        json={"opportunity_ids": [op["id"]], "mode": "manual_review"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()

    events_resp = await client.get(
        "/api/v1/audit-chain/events?event_type=execution_plan.created",
        headers=auth_headers,
    )
    assert events_resp.status_code == 200, events_resp.text
    events = events_resp.json()["items"]
    assert len(events) >= 1

    matching = [e for e in events if e["entity_id"] == created["execution_plan_id"]]
    assert len(matching) == 1
    payload = matching[0]["payload"]
    assert payload["execution_plan_id"] == created["execution_plan_id"]
    assert payload["selected_opportunity_ids"] == created["selected_opportunity_ids"]
    assert payload["risk_level"] == created["risk_level"]
    assert payload["status"] == created["status"]
    assert payload["total_savings_monthly"] == created["total_savings_monthly"]
