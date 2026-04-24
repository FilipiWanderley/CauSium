import pytest


async def _create_opportunity(client, headers, payload: dict) -> dict:
    resp = await client.post("/api/v1/opportunities", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_optimization_plan_returns_deterministic_ranking_and_quick_wins(client, auth_headers):
    first = await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Rightsize payments node",
            "description": "CPU and memory are consistently overprovisioned.",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 1000.0,
            "risk_level": "low",
            "effort_level": "low",
            "environment": "production",
        },
    )
    await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "Tune storage class lifecycle",
            "description": "Use colder tier for stale objects.",
            "category": "storage_optimization",
            "estimated_monthly_savings_usd": 700.0,
            "risk_level": "low",
            "effort_level": "medium",
            "environment": "staging",
        },
    )

    resp = await client.get("/api/v1/intel/optimization-plan?language=pt", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["summary_source"] == "deterministic"
    assert data["total_recommendations"] >= 2
    assert data["prioritized"][0]["opportunity_id"] == first["id"]
    assert data["prioritized"][0]["priority_score"] >= data["prioritized"][1]["priority_score"]
    assert any(item["opportunity_id"] == first["id"] for item in data["quick_wins"])


@pytest.mark.asyncio
async def test_optimization_plan_flags_aks_conflicts_and_adjusts_total_savings(client, auth_headers):
    await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS nodepool rightsizing - np-app",
            "description": "Downsize nodepool after sustained low usage.",
            "category": "aks_nodepool_rightsizing",
            "resource_id": "/subscriptions/a/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 500.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )
    await _create_opportunity(
        client,
        auth_headers,
        {
            "title": "AKS autoscaler recommendation - np-app",
            "description": "Tighten autoscaler boundaries to reduce over-allocation.",
            "category": "aks_autoscaler_recommendation",
            "resource_id": "/subscriptions/a/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/c1/agentPools/np-app",
            "estimated_monthly_savings_usd": 420.0,
            "risk_level": "low",
            "effort_level": "low",
        },
    )

    resp = await client.get("/api/v1/intel/optimization-plan?language=pt", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_savings_monthly_raw_usd"] > data["total_savings_monthly_adjusted_usd"]
    assert len(data["conflict_hints"]) >= 1
    assert "simultaneamente sem revisao" in data["conflict_hints"][0]

    aks_items = [
        item
        for item in data["prioritized"]
        if item["category"] in {"aks_nodepool_rightsizing", "aks_autoscaler_recommendation"}
    ]
    assert len(aks_items) == 2
    assert all(item["conflict_hints"] for item in aks_items)
