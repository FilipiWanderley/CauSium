from __future__ import annotations

from app.domains.connectors.aws.client import AwsConnectorClient


def test_normalize_cost_explorer_page_maps_groups() -> None:
    page = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-04-10", "End": "2026-04-11"},
                "Groups": [
                    {
                        "Keys": ["AmazonEC2"],
                        "Metrics": {
                            "UnblendedCost": {"Amount": "12.5", "Unit": "USD"},
                            "UsageQuantity": {"Amount": "3", "Unit": "Hrs"},
                        },
                    }
                ],
            }
        ]
    }

    rows = AwsConnectorClient._normalize_cost_explorer_page(page, "123456789012")
    assert len(rows) == 1
    rec = rows[0]
    assert rec.provider == "aws"
    assert rec.subscription_id == "123456789012"
    assert rec.service == "AmazonEC2"
    assert rec.cost_usd == 12.5
    assert rec.usage_quantity == 3.0
    assert rec.currency == "USD"
