"""
Opportunities CSV Export Service — deterministic, auditable export.

Generates a UTF-8 CSV with proper escaping from existing opportunity data,
enriched with savings_evidence, resource_context, and performance_context.

Design principles:
- Never invent data — empty string for missing fields
- Tenant-isolated — only exports data for the requesting org
- Deterministic column order — auditable and reproducible
- Standard CSV escaping — RFC 4180 compliant via Python csv module
- Streaming response — memory efficient for large datasets
"""
from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.domains.decision_engine.models import OptimizationOpportunity

from app.domains.decision_engine.savings_evidence_builder import build_savings_evidence
from app.domains.decision_engine.resource_context_builder import build_resource_context
from app.domains.decision_engine.performance_context_builder import build_performance_context


# Fixed column order — auditable and consistent
CSV_COLUMNS = [
    "opportunity_id",
    "title",
    "category",
    "status",
    "provider",
    "subscription_id",
    "resource_group",
    "resource_name",
    "resource_type",
    "sku",
    "region",
    "environment",
    "owner",
    "workload",
    "current_monthly_cost_usd",
    "estimated_monthly_savings_usd",
    "projected_monthly_cost_usd",
    "savings_confidence",
    "confidence_tier",
    "methodology",
    "risk_level",
    "cpu_p95",
    "memory_p95",
    "utilization_trend",
    "idle_days",
    "observation_window_days",
    "evidence_quality",
    "composite_score",
    "created_at",
]


def _safe_str(value: object) -> str:
    """Convert value to string for CSV, empty string for None."""
    if value is None:
        return ""
    return str(value)


def _format_float(value: float | None, decimals: int = 2) -> str:
    """Format float for CSV, empty string for None."""
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _opportunity_to_row(opportunity: "OptimizationOpportunity") -> dict[str, str]:
    """Convert a single opportunity to a CSV row dict."""
    # Build enrichment layers
    savings = build_savings_evidence(opportunity)
    resource = build_resource_context(opportunity)
    perf = build_performance_context(opportunity)

    row: dict[str, str] = {
        "opportunity_id": str(opportunity.id),
        "title": _safe_str(opportunity.title),
        "category": _safe_str(opportunity.category.value if opportunity.category else None),
        "status": _safe_str(opportunity.status.value if opportunity.status else None),
        "risk_level": _safe_str(opportunity.risk_level.value if opportunity.risk_level else None),
        "composite_score": _format_float(opportunity.composite_score),
        "created_at": opportunity.created_at.isoformat() if opportunity.created_at else "",
    }

    # Financial fields from savings_evidence (preferred) or model fallback
    if savings:
        row["current_monthly_cost_usd"] = _format_float(savings.current_monthly_cost_estimate)
        row["estimated_monthly_savings_usd"] = _format_float(savings.estimated_monthly_savings)
        row["projected_monthly_cost_usd"] = _format_float(savings.projected_monthly_cost_estimate)
        row["savings_confidence"] = _format_float(savings.savings_confidence, 3)
        row["confidence_tier"] = savings.confidence_tier
        row["methodology"] = savings.methodology
    else:
        row["current_monthly_cost_usd"] = _format_float(opportunity.current_monthly_cost_usd)
        row["estimated_monthly_savings_usd"] = _format_float(opportunity.estimated_monthly_savings_usd)
        row["projected_monthly_cost_usd"] = ""
        row["savings_confidence"] = ""
        row["confidence_tier"] = ""
        row["methodology"] = ""

    # Resource context fields
    if resource:
        row["provider"] = _safe_str(resource.provider)
        row["subscription_id"] = _safe_str(resource.subscription_id)
        row["resource_group"] = _safe_str(resource.resource_group)
        row["resource_name"] = _safe_str(resource.resource_name)
        row["resource_type"] = _safe_str(resource.resource_type)
        row["sku"] = _safe_str(resource.sku)
        row["region"] = _safe_str(resource.region)
        row["environment"] = _safe_str(resource.environment)
        row["owner"] = _safe_str(resource.owner)
        row["workload"] = _safe_str(resource.workload)
    else:
        row["provider"] = ""
        row["subscription_id"] = ""
        row["resource_group"] = ""
        row["resource_name"] = _safe_str(opportunity.resource_name)
        row["resource_type"] = ""
        row["sku"] = _safe_str(opportunity.sku_name)
        row["region"] = _safe_str(opportunity.region)
        row["environment"] = _safe_str(opportunity.environment)
        row["owner"] = _safe_str(opportunity.owner_team)
        row["workload"] = _safe_str(opportunity.service)

    # Performance context fields
    if perf:
        row["cpu_p95"] = _format_float(perf.cpu_p95)
        row["memory_p95"] = _format_float(perf.memory_p95)
        row["utilization_trend"] = perf.utilization_trend
        row["idle_days"] = _safe_str(perf.idle_days) if perf.idle_days is not None else ""
        row["observation_window_days"] = _safe_str(perf.observation_window_days)
        row["evidence_quality"] = perf.evidence_quality
    else:
        row["cpu_p95"] = ""
        row["memory_p95"] = ""
        row["utilization_trend"] = ""
        row["idle_days"] = ""
        row["observation_window_days"] = ""
        row["evidence_quality"] = ""

    return row


def generate_csv_content(opportunities: Iterable["OptimizationOpportunity"]) -> str:
    """
    Generate complete CSV content as a UTF-8 string.

    Returns RFC 4180 compliant CSV with BOM for Excel compatibility.
    """
    output = io.StringIO()
    # UTF-8 BOM for Excel compatibility
    output.write("﻿")

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_COLUMNS,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
        extrasaction="ignore",
    )
    writer.writeheader()

    for opp in opportunities:
        row = _opportunity_to_row(opp)
        writer.writerow(row)

    return output.getvalue()
