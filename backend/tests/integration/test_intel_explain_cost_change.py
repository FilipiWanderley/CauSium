from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.asyncio
async def test_explain_cost_change_denied_without_ai_plan(client, auth_headers, monkeypatch):
    def fake_execute_query(query: str, parameters: dict | None = None):
        return []

    monkeypatch.setattr("app.domains.intel.cost_explanation_service.execute_query", fake_execute_query)

    resp = await client.post(
        "/api/v1/intel/explain-cost",
        headers=auth_headers,
        json={"start_date": "2026-04-01", "end_date": "2026-04-15"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_explain_cost_change_returns_structured_response(client, org_a, db, monkeypatch):
    from sqlalchemy import update

    from app.domains.auth.models import Organization

    await db.execute(
        update(Organization)
        .where(Organization.id == org_a["org_id"])
        .values(plan="growth_ai")
    )
    await db.commit()

    def fake_execute_query(query: str, parameters: dict | None = None):
        assert parameters is not None
        if "SELECT sum(cost_usd) AS total" in query:
            start: date = parameters["start"]
            if str(start) == "2026-04-01":
                return [{"total": 118.0}]
            return [{"total": 100.0}]
        if "FULL OUTER JOIN" in query and "GROUP BY service" in query:
            return [
                {"service": "Amazon EC2", "current_cost_usd": 60.0, "previous_cost_usd": 40.0, "delta_usd": 20.0},
                {"service": "Amazon RDS", "current_cost_usd": 30.0, "previous_cost_usd": 30.0, "delta_usd": 0.0},
            ]
        if "FROM event_facts" in query:
            return [
                {
                    "timestamp": "2026-04-10T12:00:00Z",
                    "provider": "aws",
                    "event_type": "Deployment",
                    "severity": "medium",
                    "resource_name": "mock-resource-01",
                    "description": "Deploy to production completed",
                }
            ]
        if "FROM recommendation_facts" in query:
            return [
                {
                    "category": "Cost",
                    "impact": "High",
                    "service": "Amazon EC2",
                    "short_description": "Purchase reserved instances",
                    "estimated_savings_usd": 450.0,
                }
            ]
        return []

    monkeypatch.setattr("app.domains.intel.cost_explanation_service.execute_query", fake_execute_query)

    resp = await client.post(
        "/api/v1/intel/explain-cost",
        headers=org_a["headers"],
        json={"start_date": "2026-04-01", "end_date": "2026-04-15"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "summary" in data
    assert "causes" in data
    assert "impact" in data
    assert "recommendation" in data
    assert "confidence" in data

