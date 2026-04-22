from __future__ import annotations

from uuid import uuid4

from app.domains.green.service import GreenService


def test_summary_prefers_real_carbon_data(monkeypatch) -> None:
    org_id = uuid4()

    def fake_safe_query(query: str, params: dict):
        if "FROM carbon_facts" in query and "count() AS total" in query:
            return [{"total": 2}]
        if "FROM carbon_facts" in query and "GROUP BY provider" in query:
            return [{"provider": "azure", "total": 2}]
        if "FROM carbon_facts" in query and "sum(kg_co2e) AS kg" in query:
            return [{"year_month": "2026-03", "kg": 100.0}, {"year_month": "2026-04", "kg": 120.0}]
        if "FROM cost_facts" in query:
            return [{"total": 500.0}]
        return []

    monkeypatch.setattr("app.domains.green.service._safe_query", fake_safe_query)

    summary = GreenService().get_summary(org_id, months=6)

    assert summary.total_kg_co2e == 220.0
    assert summary.total_cost_usd == 500.0
    assert summary.mom_delta_pct == 20.0
    assert summary.data_source == "official"
    assert "Real emissions data" in summary.note


def test_breakdown_uses_real_data_only_for_service_dimension(monkeypatch) -> None:
    org_id = uuid4()

    def fake_safe_query(query: str, params: dict):
        if "FROM carbon_facts" in query and "count() AS total" in query:
            return [{"total": 1}]
        if "FROM carbon_facts" in query and "GROUP BY dim" in query:
            return [{"dim": "Compute", "kg": 75.0}, {"dim": "Storage", "kg": 25.0}]
        if "FROM cost_facts" in query and "GROUP BY dim, region" in query:
            return [{"dim": "eastus", "region": "eastus", "cost": 10.0}]
        return []

    monkeypatch.setattr("app.domains.green.service._safe_query", fake_safe_query)

    service_rows = GreenService().get_breakdown(org_id, by="service", days=60)
    region_rows = GreenService().get_breakdown(org_id, by="region", days=60)

    assert len(service_rows) == 2
    assert service_rows[0].dimension == "Compute"
    assert len(region_rows) == 1


def test_summary_marks_mixed_source_when_aws_and_azure_present(monkeypatch) -> None:
    org_id = uuid4()

    def fake_safe_query(query: str, params: dict):
        if "FROM carbon_facts" in query and "count() AS total" in query:
            return [{"total": 3}]
        if "FROM carbon_facts" in query and "GROUP BY provider" in query:
            return [{"provider": "azure", "total": 2}, {"provider": "aws", "total": 1}]
        if "FROM carbon_facts" in query and "sum(kg_co2e) AS kg" in query:
            return [{"year_month": "2026-04", "kg": 80.0}]
        if "FROM cost_facts" in query:
            return [{"total": 400.0}]
        return []

    monkeypatch.setattr("app.domains.green.service._safe_query", fake_safe_query)
    summary = GreenService().get_summary(org_id, months=6)

    assert summary.data_source == "mixed"
    assert "Mixed emissions dataset" in summary.note
