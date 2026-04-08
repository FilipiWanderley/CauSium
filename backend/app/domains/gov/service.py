from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from app.core.clickhouse import execute_query
from app.core.logging import get_logger

log = get_logger(__name__)

_DAYS = 30


@dataclass
class UnownedCostRow:
    service: str
    resource_id: str
    region: str
    environment: str
    cost_usd: float
    days_active: int


@dataclass
class LabelComplianceRow:
    team: str
    total_cost_usd: float
    untagged_cost_usd: float
    compliance_pct: float


@dataclass
class GovSummary:
    total_resources: int
    unowned_resources: int
    unowned_cost_usd: float
    unowned_pct: float
    teams_evaluated: int
    avg_compliance_pct: float


def _safe_query(query: str, params: dict) -> list[dict]:
    try:
        return execute_query(query, params) or []
    except Exception as exc:
        log.warning("gov.query.failed", error=str(exc))
        return []


class GovService:
    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self, org_id: UUID, days: int = _DAYS) -> GovSummary:
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        total_rows = _safe_query(
            """
            SELECT uniqExact(resource_id) AS total
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND resource_id != ''
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        total = int(total_rows[0]["total"]) if total_rows else 0

        unowned_rows = _safe_query(
            """
            SELECT
                uniqExact(resource_id) AS cnt,
                sum(cost_usd)          AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date  >= {cutoff:String}
              AND resource_id != ''
              AND (owner_team = '' OR owner_team IS NULL)
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        unowned_cnt = int(unowned_rows[0]["cnt"]) if unowned_rows else 0
        unowned_cost = float(unowned_rows[0]["cost"] or 0) if unowned_rows else 0.0

        teams_rows = _safe_query(
            """
            SELECT uniqExact(owner_team) AS cnt
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND owner_team != ''
              AND owner_team IS NOT NULL
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        teams = int(teams_rows[0]["cnt"]) if teams_rows else 0

        compliance = _safe_query(
            """
            SELECT
                owner_team,
                sum(cost_usd)                                           AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL) AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY owner_team
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        pcts = [
            100.0 * (1.0 - float(r.get("untagged", 0) or 0) / max(float(r.get("total", 1) or 1), 0.01))
            for r in compliance
            if float(r.get("total", 0) or 0) > 0
        ]
        avg_pct = sum(pcts) / len(pcts) if pcts else 100.0

        return GovSummary(
            total_resources=total,
            unowned_resources=unowned_cnt,
            unowned_cost_usd=round(unowned_cost, 2),
            unowned_pct=round(100.0 * unowned_cnt / max(total, 1), 1),
            teams_evaluated=teams,
            avg_compliance_pct=round(avg_pct, 1),
        )

    # ------------------------------------------------------------------
    # Unowned costs
    # ------------------------------------------------------------------

    def get_unowned_costs(
        self, org_id: UUID, days: int = _DAYS, limit: int = 50
    ) -> list[UnownedCostRow]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = _safe_query(
            """
            SELECT
                service,
                resource_id,
                region,
                environment,
                sum(cost_usd)         AS cost_usd,
                uniqExact(date)       AS days_active
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date  >= {cutoff:String}
              AND resource_id != ''
              AND (owner_team = '' OR owner_team IS NULL)
            GROUP BY service, resource_id, region, environment
            ORDER BY cost_usd DESC
            LIMIT {limit:UInt32}
            """,
            {"org_id": str(org_id), "cutoff": cutoff, "limit": limit},
        )
        return [
            UnownedCostRow(
                service=r.get("service") or "unknown",
                resource_id=r.get("resource_id") or "—",
                region=r.get("region") or "—",
                environment=r.get("environment") or "—",
                cost_usd=round(float(r.get("cost_usd") or 0), 2),
                days_active=int(r.get("days_active") or 0),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Label compliance
    # ------------------------------------------------------------------

    def get_label_compliance(
        self, org_id: UUID, days: int = _DAYS
    ) -> list[LabelComplianceRow]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = _safe_query(
            """
            SELECT
                if(owner_team = '' OR owner_team IS NULL, '(untagged)', owner_team) AS team,
                sum(cost_usd)                                                        AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL)              AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY team
            ORDER BY total DESC
            LIMIT 100
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        result = []
        for r in rows:
            total = float(r.get("total") or 0)
            untagged = float(r.get("untagged") or 0)
            pct = round(100.0 * (1.0 - untagged / max(total, 0.01)), 1) if total > 0 else 100.0
            result.append(
                LabelComplianceRow(
                    team=r.get("team") or "(untagged)",
                    total_cost_usd=round(total, 2),
                    untagged_cost_usd=round(untagged, 2),
                    compliance_pct=pct,
                )
            )
        return result
