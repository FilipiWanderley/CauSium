from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.core.clickhouse import execute_query
from app.core.logging import get_logger
from app.domains.economics.team_inference import (
    infer_team_from_resource,
)

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


@dataclass
class RecommendationRow:
    recommendation_id: str
    category: str
    impact: str
    resource_id: str
    resource_name: str
    resource_group: str
    service: str
    short_description: str
    estimated_savings_usd: float | None


@dataclass
class RecommendationsSummary:
    total: int
    high_impact: int
    total_estimated_savings_usd: float
    by_category: dict[str, int]


@dataclass
class ResourceRow:
    resource_id: str
    name: str
    resource_type: str
    resource_group: str
    location: str
    environment: str
    owner_team: str
    sku_name: str
    provisioning_state: str


@dataclass
class InventorySummary:
    total_resources: int
    resource_types: int
    resource_groups: int
    unowned_resources: int


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

        # Count "unowned" with inference: only truly unclassified resources
        # Uses same logic as team_inference to determine which are truly without team
        unowned_rows = _safe_query(
            """
            SELECT
                uniqExact(resource_id) AS cnt,
                sum(cost_usd)          AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date  >= {cutoff:String}
              AND resource_id != ''
              AND (
                  (owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged')
                  AND (
                      resource_name = '' OR resource_name IS NULL
                      OR resource_name LIKE 'networkwatcherrg%'
                      OR resource_name LIKE 'azurebackuprg%'
                      OR resource_name LIKE '$system%'
                      OR resource_name LIKE 'defaultresourcegroup%'
                      OR resource_name LIKE 'cloud%'
                      OR resource_name LIKE 'veeam-linux-helper%'
                      OR resource_name LIKE 'causiumcost%'
                  )
              )
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        unowned_cnt = int(unowned_rows[0]["cnt"]) if unowned_rows else 0
        unowned_cost = float(unowned_rows[0]["cost"] or 0) if unowned_rows else 0.0

        # Count distinct inferred teams (using same logic as label compliance)
        teams_rows = _safe_query(
            """
            SELECT count(DISTINCT team_label) AS cnt
            FROM (
                SELECT
                    multiIf(
                        owner_team != '' AND owner_team IS NOT NULL AND owner_team != 'untagged', owner_team,
                        resource_name != '' AND resource_name IS NOT NULL
                            AND resource_name NOT LIKE 'networkwatcherrg%'
                            AND resource_name NOT LIKE 'azurebackuprg%'
                            AND resource_name NOT LIKE '$system%'
                            AND resource_name NOT LIKE 'defaultresourcegroup%'
                            AND resource_name NOT LIKE 'cloud%'
                            AND resource_name NOT LIKE 'veeam-linux-helper%'
                            AND resource_name NOT LIKE 'causiumcost%'
                            AND resource_name NOT LIKE 'projeto%',
                        multiIf(
                            startsWith(lower(resource_name), 'csc'), 'CSC',
                            startsWith(lower(resource_name), 'cqg'), 'CQG',
                            startsWith(lower(resource_name), 'engetec'), 'Engetec',
                            startsWith(lower(resource_name), 'vital'), 'Vital',
                            startsWith(lower(resource_name), 'qgi'), 'QGI',
                            startsWith(lower(resource_name), 'qggn'), 'QGGN',
                            startsWith(lower(resource_name), 'qgsa'), 'QGSA',
                            startsWith(lower(resource_name), 'frontis'), 'Frontis',
                            startsWith(lower(resource_name), 'projeto'), 'Datalake',
                            ''
                        ),
                        ''
                    ) AS team_label
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND date >= {cutoff:String}
            )
            WHERE team_label != ''
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        teams = int(teams_rows[0]["cnt"]) if teams_rows else 0

        # Calculate avg compliance with inference
        compliance = _safe_query(
            """
            SELECT
                owner_team,
                resource_name,
                sum(cost_usd) AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged') AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY owner_team, resource_name
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        # Apply inference and aggregate by inferred team
        team_data: dict[str, dict] = {}
        for r in compliance:
            owner_team = str(r.get("owner_team") or "")
            resource_name = str(r.get("resource_name") or "")
            total = float(r.get("total") or 0)
            untagged = float(r.get("untagged") or 0)

            result = infer_team_from_resource(resource_name, owner_team)
            team_label = result.team_label

            if team_label not in team_data:
                team_data[team_label] = {"total": 0.0, "untagged": 0.0}
            team_data[team_label]["total"] += total
            team_data[team_label]["untagged"] += untagged

        pcts = [
            100.0 * (1.0 - data["untagged"] / max(data["total"], 0.01))
            for data in team_data.values()
            if data["total"] > 0
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
        # Only truly unclassified resources (no tag AND no inference pattern)
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
              AND (owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged')
              AND (
                  resource_name = '' OR resource_name IS NULL
                  OR resource_name LIKE 'networkwatcherrg%'
                  OR resource_name LIKE 'azurebackuprg%'
                  OR resource_name LIKE '$system%'
                  OR resource_name LIKE 'defaultresourcegroup%'
                  OR resource_name LIKE 'cloud%'
                  OR resource_name LIKE 'veeam-linux-helper%'
                  OR resource_name LIKE 'causiumcost%'
              )
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
        # Query includes resource_name to enable team inference fallback
        rows = _safe_query(
            """
            SELECT
                owner_team,
                resource_name,
                sum(cost_usd) AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged') AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY owner_team, resource_name
            ORDER BY total DESC
            LIMIT 500
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )

        # Apply inference and aggregate by inferred team
        team_data: dict[str, dict] = {}
        for r in rows:
            owner_team = str(r.get("owner_team") or "")
            resource_name = str(r.get("resource_name") or "")
            total = float(r.get("total") or 0)
            untagged = float(r.get("untagged") or 0)

            result = infer_team_from_resource(resource_name, owner_team)
            team_label = result.team_label

            if team_label not in team_data:
                team_data[team_label] = {"total": 0.0, "untagged": 0.0}
            team_data[team_label]["total"] += total
            team_data[team_label]["untagged"] += untagged

        # Sort by total cost and build result
        sorted_teams = sorted(team_data.items(), key=lambda x: -x[1]["total"])
        result = []
        for team_label, data in sorted_teams:
            total = data["total"]
            untagged = data["untagged"]
            pct = round(100.0 * (1.0 - untagged / max(total, 0.01)), 1) if total > 0 else 100.0
            result.append(
                LabelComplianceRow(
                    team=team_label,
                    total_cost_usd=round(total, 2),
                    untagged_cost_usd=round(untagged, 2),
                    compliance_pct=pct,
                )
            )
        return result

    # ------------------------------------------------------------------
    # Advisor recommendations
    # ------------------------------------------------------------------

    def get_recommendations(
        self,
        org_id: UUID,
        *,
        category: str | None = None,
        impact: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRow]:
        params: dict = {"org_id": str(org_id), "limit": limit}
        extra_filters: list[str] = []

        if category:
            extra_filters.append("AND category = {category:String}")
            params["category"] = category
        if impact:
            extra_filters.append("AND impact = {impact:String}")
            params["impact"] = impact

        extra = " ".join(extra_filters)

        rows = _safe_query(
            f"""
            SELECT
                recommendation_id,
                category,
                impact,
                resource_id,
                resource_name,
                resource_group,
                service,
                short_description,
                estimated_savings_usd
            FROM recommendation_facts
            WHERE org_id = {{org_id:String}}
            {extra}
            ORDER BY
                multiIf(impact = 'High', 0, impact = 'Medium', 1, 2) ASC,
                estimated_savings_usd DESC NULLS LAST
            LIMIT {{limit:UInt32}}
            """,
            params,
        )
        return [
            RecommendationRow(
                recommendation_id=r.get("recommendation_id") or "",
                category=r.get("category") or "",
                impact=r.get("impact") or "",
                resource_id=r.get("resource_id") or "",
                resource_name=r.get("resource_name") or "",
                resource_group=r.get("resource_group") or "",
                service=r.get("service") or "",
                short_description=r.get("short_description") or "",
                estimated_savings_usd=(
                    float(r["estimated_savings_usd"])
                    if r.get("estimated_savings_usd") is not None
                    else None
                ),
            )
            for r in rows
        ]

    def get_recommendations_summary(self, org_id: UUID) -> RecommendationsSummary:
        rows = _safe_query(
            """
            SELECT
                category,
                impact,
                count()                          AS cnt,
                sum(estimated_savings_usd)        AS savings
            FROM recommendation_facts
            WHERE org_id = {org_id:String}
            GROUP BY category, impact
            """,
            {"org_id": str(org_id)},
        )

        total = 0
        high_impact = 0
        total_savings = 0.0
        by_category: dict[str, int] = {}

        for r in rows:
            cnt = int(r.get("cnt") or 0)
            total += cnt
            if str(r.get("impact") or "").lower() == "high":
                high_impact += cnt
            total_savings += float(r.get("savings") or 0)
            cat = str(r.get("category") or "Other")
            by_category[cat] = by_category.get(cat, 0) + cnt

        return RecommendationsSummary(
            total=total,
            high_impact=high_impact,
            total_estimated_savings_usd=round(total_savings, 2),
            by_category=by_category,
        )

    # ------------------------------------------------------------------
    # Resource inventory
    # ------------------------------------------------------------------

    def get_inventory(
        self,
        org_id: UUID,
        *,
        resource_type: str | None = None,
        owner_team: str | None = None,
        environment: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ResourceRow], int]:
        params: dict = {"org_id": str(org_id), "limit": limit, "offset": offset}
        extra_filters: list[str] = []

        if resource_type:
            extra_filters.append("AND resource_type = {resource_type:String}")
            params["resource_type"] = resource_type
        if owner_team:
            extra_filters.append("AND owner_team = {owner_team:String}")
            params["owner_team"] = owner_team
        if environment:
            extra_filters.append("AND environment = {environment:String}")
            params["environment"] = environment

        extra = " ".join(extra_filters)

        count_rows = _safe_query(
            f"""
            SELECT count() AS total
            FROM resource_inventory
            WHERE org_id = {{org_id:String}}
            {extra}
            """,
            params,
        )
        total = int(count_rows[0]["total"]) if count_rows else 0

        rows = _safe_query(
            f"""
            SELECT
                resource_id,
                name,
                resource_type,
                resource_group,
                location,
                environment,
                owner_team,
                sku_name,
                provisioning_state
            FROM resource_inventory
            WHERE org_id = {{org_id:String}}
            {extra}
            ORDER BY resource_type ASC, name ASC
            LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}
            """,
            params,
        )
        items = [
            ResourceRow(
                resource_id=r.get("resource_id") or "",
                name=r.get("name") or "",
                resource_type=r.get("resource_type") or "",
                resource_group=r.get("resource_group") or "",
                location=r.get("location") or "",
                environment=r.get("environment") or "",
                owner_team=r.get("owner_team") or "Sem equipe identificada",
                sku_name=r.get("sku_name") or "",
                provisioning_state=r.get("provisioning_state") or "",
            )
            for r in rows
        ]
        return items, total

    def get_inventory_summary(self, org_id: UUID) -> InventorySummary:
        rows = _safe_query(
            """
            SELECT
                count()                                                          AS total,
                uniqExact(resource_type)                                         AS types,
                uniqExact(resource_group)                                        AS groups,
                countIf(owner_team = '' OR owner_team = 'untagged')             AS unowned
            FROM resource_inventory
            WHERE org_id = {org_id:String}
            """,
            {"org_id": str(org_id)},
        )
        if not rows:
            return InventorySummary(
                total_resources=0,
                resource_types=0,
                resource_groups=0,
                unowned_resources=0,
            )
        r = rows[0]
        return InventorySummary(
            total_resources=int(r.get("total") or 0),
            resource_types=int(r.get("types") or 0),
            resource_groups=int(r.get("groups") or 0),
            unowned_resources=int(r.get("unowned") or 0),
        )
