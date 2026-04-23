from __future__ import annotations

from datetime import date, timedelta

import pytest


@pytest.mark.asyncio
async def test_detect_and_list_cost_anomalies(client, auth_headers, monkeypatch):
    target_date = date(2026, 4, 15)
    start_date = target_date - timedelta(days=14)

    def fake_execute_query(query: str, parameters: dict | None = None):
        assert parameters is not None
        if "SELECT max(date) AS max_date" in query:
            return [{"max_date": target_date.isoformat()}]

        if "GROUP BY provider, service, date" in query:
            rows: list[dict] = []
            for i in range(15):
                day = start_date + timedelta(days=i)
                ec2_cost = 127.0 if day == target_date else 100.0
                rows.append(
                    {
                        "provider": "aws",
                        "service": "Amazon EC2",
                        "date": day.isoformat(),
                        "total_cost_usd": ec2_cost,
                    }
                )
                rows.append(
                    {
                        "provider": "aws",
                        "service": "Amazon S3",
                        "date": day.isoformat(),
                        "total_cost_usd": 10.0 if day != target_date else 11.0,
                    }
                )
            return rows

        return []

    monkeypatch.setattr("app.domains.intel.anomaly_detection_service.execute_query", fake_execute_query)

    detect_resp = await client.post(
        "/api/v1/intel/cost-anomalies/detect",
        headers=auth_headers,
        json={
            "lookback_days": 14,
            "z_threshold": 2.5,
            "min_history_days": 7,
            "min_delta_usd": 10.0,
        },
    )
    assert detect_resp.status_code == 200, detect_resp.text
    detect_data = detect_resp.json()
    assert detect_data["observed_date"] == target_date.isoformat()
    assert detect_data["detected"] >= 1
    assert detect_data["created"] >= 1
    assert len(detect_data["anomalies"]) >= 1

    list_resp = await client.get(
        "/api/v1/intel/cost-anomalies?page=1&page_size=20",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    first = list_data["items"][0]
    assert first["provider"] == "aws"
    assert first["service"] == "Amazon EC2"
    assert first["observed_date"] == target_date.isoformat()
    assert first["deviation_pct"] == 27.0
