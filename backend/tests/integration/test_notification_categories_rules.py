from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_optimization_alert_created_on_opportunity_create(client, auth_headers):
    create = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "Rightsize VM fleet",
            "description": "VMs over-provisioned by 60%",
            "category": "rightsizing",
            "estimated_monthly_savings_usd": 1200.0,
            "current_monthly_cost_usd": 4000.0,
            "service": "Virtual Machines",
            "environment": "production",
            "owner_team": "platform",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201, create.text

    new_resp = await client.get(
        "/api/v1/notifications/new",
        headers=auth_headers,
        params={"category": "optimization"},
    )
    assert new_resp.status_code == 200, new_resp.text
    body = new_resp.json()
    assert body["unread"] >= 1
    assert any("optimization opportunity" in item["title"].lower() for item in body["items"])


@pytest.mark.asyncio
async def test_governance_alert_created_on_risk_budget_create(client, auth_headers):
    create = await client.post(
        "/api/v1/risk-budgets",
        json={
            "name": "Prod Governance Budget",
            "domain": "governance",
            "environment": "production",
            "budget_type": "cost_variance",
            "period": "weekly",
            "limit_value": 1000.0,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201, create.text

    new_resp = await client.get(
        "/api/v1/notifications/new",
        headers=auth_headers,
        params={"category": "governance"},
    )
    assert new_resp.status_code == 200, new_resp.text
    body = new_resp.json()
    assert body["unread"] >= 1
    assert any("risk budget configured" in item["title"].lower() for item in body["items"])


@pytest.mark.asyncio
async def test_financial_alert_created_when_budget_threshold_crossed(client, auth_headers, monkeypatch):
    from app.domains.economics import service as economics_service

    monkeypatch.setattr(economics_service, "_query_cost", lambda org_id, start, end: 8500.0)

    create_budget = await client.put(
        "/api/v1/economics/budget",
        json={
            "amount_usd": 10000.0,
            "period": "monthly",
            "currency": "USD",
            "alert_thresholds": [50, 80, 90],
        },
        headers=auth_headers,
    )
    assert create_budget.status_code == 200, create_budget.text

    get_budget = await client.get("/api/v1/economics/budget", headers=auth_headers)
    assert get_budget.status_code == 200, get_budget.text

    new_resp = await client.get(
        "/api/v1/notifications/new",
        headers=auth_headers,
        params={"category": "financial"},
    )
    assert new_resp.status_code == 200, new_resp.text
    body = new_resp.json()
    assert body["unread"] >= 1
    assert any("budget threshold reached" in item["title"].lower() for item in body["items"])
