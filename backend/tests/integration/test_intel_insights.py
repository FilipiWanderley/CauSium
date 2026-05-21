from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.asyncio
async def test_intel_insights_denied_without_ai_plan(client, auth_headers, monkeypatch):
    def fake_execute_query(query: str, parameters: dict | None = None):
        return [{"total": 0.0}]

    monkeypatch.setattr("app.domains.intel.insights_service.execute_query", fake_execute_query)

    resp = await client.get("/api/v1/intel/insights", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "top_saving_opportunity" in data
    assert "main_risk" in data


@pytest.mark.asyncio
async def test_intel_insights_returns_actionable_payload(client, org_a, db, monkeypatch):
    from sqlalchemy import update

    from app.domains.auth.models import Organization
    from app.domains.decision_engine.models import (
        EffortLevel,
        OpportunityCategory,
        OpportunityStatus,
        OptimizationOpportunity,
        RiskLevel,
    )
    from app.domains.intel.models import CostAnomaly, CostAnomalySeverity

    await db.execute(
        update(Organization)
        .where(Organization.id == org_a["org_id"])
        .values(plan="growth_ai")
    )

    db.add(
        OptimizationOpportunity(
            org_id=org_a["org_id"],
            title="Rightsize EC2 fleet",
            description="Downsize instances with low utilization.",
            category=OpportunityCategory.RIGHTSIZING,
            financial_impact_score=90.0,
            risk_score=30.0,
            effort_score=20.0,
            criticality_score=80.0,
            composite_score=86.0,
            estimated_monthly_savings_usd=1200.0,
            estimated_annual_savings_usd=14400.0,
            current_monthly_cost_usd=4000.0,
            risk_level=RiskLevel.LOW,
            effort_level=EffortLevel.MEDIUM,
            status=OpportunityStatus.OPEN,
            service="Amazon EC2",
            owner_team="FinOps",
        )
    )
    db.add(
        CostAnomaly(
            org_id=org_a["org_id"],
            provider="aws",
            service="Amazon RDS",
            observed_date=date.today(),
            current_cost_usd=300.0,
            historical_mean_usd=180.0,
            historical_stddev_usd=20.0,
            z_score=6.0,
            deviation_pct=66.67,
            severity=CostAnomalySeverity.HIGH,
            window_days=14,
            z_threshold=2.5,
        )
    )
    await db.commit()

    calls = {"count": 0}

    def fake_execute_query(query: str, parameters: dict | None = None):
        assert parameters is not None
        if "SELECT sum(cost_usd) AS total" in query:
            calls["count"] += 1
            return [{"total": 1400.0}] if calls["count"] == 1 else [{"total": 1000.0}]
        return []

    monkeypatch.setattr("app.domains.intel.insights_service.execute_query", fake_execute_query)

    resp = await client.get("/api/v1/intel/insights?language=en", headers=org_a["headers"])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "top_saving_opportunity" in data
    assert "main_risk" in data
    assert "cost_trend_summary" in data
    assert "recommended_action" in data
    assert data["confidence"] >= 0.5
    assert "EC2" in data["top_saving_opportunity"]
    assert "RDS" in data["main_risk"]
