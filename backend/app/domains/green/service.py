from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.core.clickhouse import execute_query
from app.core.logging import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Carbon intensity estimates (gCO2e per USD spent)
# Source: approximations based on IEA regional grid intensity + cloud provider
# transparency reports. Replace with Azure Carbon Optimization API when available.
# ---------------------------------------------------------------------------
_REGION_INTENSITY: dict[str, float] = {
    # Low-carbon regions (heavy renewables)
    "westeurope": 85.0,
    "northeurope": 50.0,
    "swedencentral": 30.0,
    "norwayeast": 25.0,
    "westus2": 90.0,
    "canadacentral": 55.0,
    # Medium
    "eastus": 150.0,
    "eastus2": 140.0,
    "centralus": 135.0,
    "southcentralus": 160.0,
    "uksouth": 100.0,
    "ukwest": 95.0,
    "francecentral": 60.0,
    "germanywestcentral": 200.0,
    "australiaeast": 220.0,
    # High-carbon regions
    "southeastasia": 280.0,
    "eastasia": 320.0,
    "centralindia": 380.0,
    "southindia": 350.0,
    "brazilsouth": 230.0,
    "japaneast": 450.0,
    "koreacentral": 430.0,
}
_DEFAULT_INTENSITY = 200.0  # gCO2e per USD (global weighted average)


def _intensity(region: str) -> float:
    return _REGION_INTENSITY.get((region or "").lower(), _DEFAULT_INTENSITY)


def _safe_query(query: str, params: dict) -> list[dict]:
    try:
        return execute_query(query, params) or []
    except Exception as exc:
        log.warning("green.query.failed", error=str(exc))
        return []


@dataclass
class EmissionsMonthRow:
    month: str       # YYYY-MM
    kg_co2e: float
    cost_usd: float
    delta_pct: float | None  # vs previous month


@dataclass
class EmissionsBreakdownRow:
    dimension: str
    kg_co2e: float
    cost_usd: float
    share_pct: float


@dataclass
class GreenSummary:
    total_kg_co2e: float
    total_cost_usd: float
    intensity_avg: float         # gCO2e / USD
    mom_delta_pct: float | None  # month-over-month change
    months_available: int
    note: str


class GreenService:
    def _has_real_carbon_data(self, org_id: UUID, months: int) -> bool:
        cutoff = (date.today() - timedelta(days=months * 30)).strftime("%Y-%m")
        rows = _safe_query(
            """
            SELECT count() AS total
            FROM carbon_facts
            WHERE org_id = {org_id:String}
              AND year_month >= {cutoff:String}
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        return bool(rows and int(rows[0].get("total") or 0) > 0)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self, org_id: UUID, months: int = 6) -> GreenSummary:
        if self._has_real_carbon_data(org_id, months):
            return self._get_summary_real(org_id, months)

        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
        rows = _safe_query(
            """
            SELECT
                region,
                sum(cost_usd) AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY region
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        total_cost = sum(float(r.get("cost") or 0) for r in rows)
        total_kg = sum(
            float(r.get("cost") or 0) * _intensity(r.get("region") or "") / 1000.0
            for r in rows
        )
        intensity_avg = (total_kg * 1000.0 / max(total_cost, 0.01)) if total_cost else _DEFAULT_INTENSITY

        # MoM delta: compare last 30 days vs prior 30 days
        now = date.today()
        last30 = _safe_query(
            """
            SELECT sum(cost_usd) AS cost, region
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:String} AND date < {end:String}
            GROUP BY region
            """,
            {
                "org_id": str(org_id),
                "start": (now - timedelta(days=30)).isoformat(),
                "end": now.isoformat(),
            },
        )
        prior30 = _safe_query(
            """
            SELECT sum(cost_usd) AS cost, region
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:String} AND date < {end:String}
            GROUP BY region
            """,
            {
                "org_id": str(org_id),
                "start": (now - timedelta(days=60)).isoformat(),
                "end": (now - timedelta(days=30)).isoformat(),
            },
        )
        kg_last = sum(float(r.get("cost") or 0) * _intensity(r.get("region") or "") / 1000.0 for r in last30)
        kg_prior = sum(float(r.get("cost") or 0) * _intensity(r.get("region") or "") / 1000.0 for r in prior30)
        mom = round((kg_last - kg_prior) / max(kg_prior, 0.01) * 100.0, 1) if kg_prior > 0 else None

        return GreenSummary(
            total_kg_co2e=round(total_kg, 1),
            total_cost_usd=round(total_cost, 2),
            intensity_avg=round(intensity_avg, 1),
            mom_delta_pct=mom,
            months_available=months,
            note="Estimates based on regional grid carbon intensity. Connect Azure Carbon Optimization API for certified data.",
        )

    def _get_summary_real(self, org_id: UUID, months: int = 6) -> GreenSummary:
        cutoff = (date.today() - timedelta(days=months * 30)).strftime("%Y-%m")
        rows = _safe_query(
            """
            SELECT year_month, sum(kg_co2e) AS kg
            FROM carbon_facts
            WHERE org_id = {org_id:String}
              AND year_month >= {cutoff:String}
            GROUP BY year_month
            ORDER BY year_month ASC
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        total_kg = sum(float(r.get("kg") or 0) for r in rows)

        cost_rows = _safe_query(
            """
            SELECT sum(cost_usd) AS total
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff_date:String}
            """,
            {"org_id": str(org_id), "cutoff_date": (date.today() - timedelta(days=months * 30)).isoformat()},
        )
        total_cost = float(cost_rows[0].get("total") or 0) if cost_rows else 0.0

        mom = None
        if len(rows) >= 2:
            prev = float(rows[-2].get("kg") or 0)
            curr = float(rows[-1].get("kg") or 0)
            if prev > 0:
                mom = round((curr - prev) / prev * 100.0, 1)

        intensity_avg = (total_kg * 1000.0 / max(total_cost, 0.01)) if total_cost else _DEFAULT_INTENSITY

        return GreenSummary(
            total_kg_co2e=round(total_kg, 1),
            total_cost_usd=round(total_cost, 2),
            intensity_avg=round(intensity_avg, 1),
            mom_delta_pct=mom,
            months_available=months,
            note="Real emissions data from Azure Carbon API.",
        )

    # ------------------------------------------------------------------
    # Monthly series
    # ------------------------------------------------------------------

    def get_emissions_monthly(self, org_id: UUID, months: int = 12) -> list[EmissionsMonthRow]:
        if self._has_real_carbon_data(org_id, months):
            return self._get_emissions_monthly_real(org_id, months)

        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
        rows = _safe_query(
            """
            SELECT
                toYYYYMM(date) AS ym,
                region,
                sum(cost_usd) AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY ym, region
            ORDER BY ym ASC
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        # Aggregate by month
        monthly: dict[str, dict] = {}
        for r in rows:
            ym = str(r.get("ym") or "")
            cost = float(r.get("cost") or 0)
            kg = cost * _intensity(r.get("region") or "") / 1000.0
            if ym not in monthly:
                monthly[ym] = {"cost": 0.0, "kg": 0.0}
            monthly[ym]["cost"] += cost
            monthly[ym]["kg"] += kg

        result: list[EmissionsMonthRow] = []
        keys = sorted(monthly.keys())
        for i, ym in enumerate(keys):
            prev_kg = monthly[keys[i - 1]]["kg"] if i > 0 else None
            curr_kg = monthly[ym]["kg"]
            delta = round((curr_kg - prev_kg) / max(prev_kg, 0.01) * 100.0, 1) if prev_kg else None
            # Format YYYYMM → YYYY-MM
            label = f"{ym[:4]}-{ym[4:6]}" if len(ym) == 6 else ym
            result.append(
                EmissionsMonthRow(
                    month=label,
                    kg_co2e=round(curr_kg, 1),
                    cost_usd=round(monthly[ym]["cost"], 2),
                    delta_pct=delta,
                )
            )
        return result

    def _get_emissions_monthly_real(self, org_id: UUID, months: int = 12) -> list[EmissionsMonthRow]:
        cutoff = (date.today() - timedelta(days=months * 30)).strftime("%Y-%m")
        rows = _safe_query(
            """
            SELECT year_month AS ym, sum(kg_co2e) AS kg
            FROM carbon_facts
            WHERE org_id = {org_id:String}
              AND year_month >= {cutoff:String}
            GROUP BY ym
            ORDER BY ym ASC
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        cost_rows = _safe_query(
            """
            SELECT toYYYYMM(date) AS ym, sum(cost_usd) AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff_date:String}
            GROUP BY ym
            """,
            {"org_id": str(org_id), "cutoff_date": (date.today() - timedelta(days=months * 30)).isoformat()},
        )
        cost_map = {str(r.get("ym")): float(r.get("cost") or 0) for r in cost_rows}

        result: list[EmissionsMonthRow] = []
        for i, row in enumerate(rows):
            ym = str(row.get("ym") or "")
            kg = float(row.get("kg") or 0)
            prev_kg = float(rows[i - 1].get("kg") or 0) if i > 0 else 0
            delta = round((kg - prev_kg) / prev_kg * 100.0, 1) if i > 0 and prev_kg > 0 else None
            ym_compact = ym.replace("-", "")
            result.append(
                EmissionsMonthRow(
                    month=ym,
                    kg_co2e=round(kg, 1),
                    cost_usd=round(cost_map.get(ym_compact, 0.0), 2),
                    delta_pct=delta,
                )
            )
        return result

    # ------------------------------------------------------------------
    # Breakdown
    # ------------------------------------------------------------------

    def get_breakdown(
        self, org_id: UUID, by: str = "service", days: int = 30
    ) -> list[EmissionsBreakdownRow]:
        months = max(1, min(24, days // 30))
        if self._has_real_carbon_data(org_id, months) and by == "service":
            return self._get_breakdown_real(org_id, by=by, days=days)

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        allowed = {"service", "region", "environment", "owner_team"}
        dimension = by if by in allowed else "service"

        rows = _safe_query(
            f"""
            SELECT
                {dimension} AS dim,
                region,
                sum(cost_usd) AS cost
            FROM cost_facts
            WHERE org_id = {{org_id:String}}
              AND date >= {{cutoff:String}}
            GROUP BY dim, region
            ORDER BY cost DESC
            LIMIT 200
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        # Reduce to dimension level
        agg: dict[str, dict] = {}
        for r in rows:
            dim = r.get("dim") or "(unknown)"
            cost = float(r.get("cost") or 0)
            kg = cost * _intensity(r.get("region") or "") / 1000.0
            if dim not in agg:
                agg[dim] = {"cost": 0.0, "kg": 0.0}
            agg[dim]["cost"] += cost
            agg[dim]["kg"] += kg

        total_kg = sum(v["kg"] for v in agg.values()) or 1.0
        result = [
            EmissionsBreakdownRow(
                dimension=dim,
                kg_co2e=round(v["kg"], 1),
                cost_usd=round(v["cost"], 2),
                share_pct=round(v["kg"] / total_kg * 100.0, 1),
            )
            for dim, v in sorted(agg.items(), key=lambda x: -x[1]["kg"])
        ]
        return result[:50]

    def _get_breakdown_real(
        self, org_id: UUID, by: str = "service", days: int = 30
    ) -> list[EmissionsBreakdownRow]:
        cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m")
        allowed = {"service", "region", "environment", "owner_team"}
        dimension = by if by in allowed else "service"

        if dimension != "service":
            return []

        rows = _safe_query(
            """
            SELECT service AS dim, sum(kg_co2e) AS kg
            FROM carbon_facts
            WHERE org_id = {org_id:String}
              AND year_month >= {cutoff:String}
            GROUP BY dim
            ORDER BY kg DESC
            LIMIT 200
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        total_kg = sum(float(r.get("kg") or 0) for r in rows) or 1.0
        return [
            EmissionsBreakdownRow(
                dimension=str(r.get("dim") or "(unknown)"),
                kg_co2e=round(float(r.get("kg") or 0), 1),
                cost_usd=0.0,
                share_pct=round(float(r.get("kg") or 0) / total_kg * 100.0, 1),
            )
            for r in rows[:50]
        ]
