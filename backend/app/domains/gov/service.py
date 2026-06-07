from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class TopUntaggedRow:
    name: str
    cost_usd: float
    record_count: int


@dataclass
class TagComplianceMetrics:
    configured_tag_key: str
    total_cost: float
    tagged_cost: float
    untagged_cost: float
    coverage_pct: float
    total_records: int
    tagged_records: int
    untagged_records: int
    top_untagged_resource_groups: list[TopUntaggedRow]
    top_untagged_services: list[TopUntaggedRow]


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

        # Count "unowned": resources without team tag (untagged, empty, or null)
        unowned_rows = _safe_query(
            """
            SELECT
                uniqExact(resource_id) AS cnt,
                sum(cost_usd)          AS cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date  >= {cutoff:String}
              AND resource_id != ''
              AND (owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged')
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        unowned_cnt = int(unowned_rows[0]["cnt"]) if unowned_rows else 0
        unowned_cost = float(unowned_rows[0]["cost"] or 0) if unowned_rows else 0.0

        # Count distinct teams (official tags only)
        teams_rows = _safe_query(
            """
            SELECT uniqExact(owner_team) AS cnt
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND owner_team != ''
              AND owner_team IS NOT NULL
              AND owner_team != 'untagged'
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        teams = int(teams_rows[0]["cnt"]) if teams_rows else 0

        # Calculate avg compliance (official data only)
        compliance = _safe_query(
            """
            SELECT
                if(owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged', 'Sem equipe identificada', owner_team) AS team,
                sum(cost_usd) AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged') AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY team
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
              AND (owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged')
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
        """Official label compliance: uses real Azure tags only."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = _safe_query(
            """
            SELECT
                if(owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged', 'Sem equipe identificada', owner_team) AS team,
                sum(cost_usd) AS total,
                sumIf(cost_usd, owner_team = '' OR owner_team IS NULL OR owner_team = 'untagged') AS untagged
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
            GROUP BY team
            ORDER BY total DESC
            LIMIT 100
            """,
            {"org_id": str(org_id), "cutoff": cutoff},
        )
        return [
            LabelComplianceRow(
                team=r.get("team") or "Sem equipe identificada",
                total_cost_usd=round(float(r.get("total") or 0), 2),
                untagged_cost_usd=round(float(r.get("untagged") or 0), 2),
                compliance_pct=round(100.0 * (1.0 - float(r.get("untagged", 0) or 0) / max(float(r.get("total", 1) or 1), 0.01)), 1),
            )
            for r in rows
        ]

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

    # ------------------------------------------------------------------
    # Tag Compliance (monitored tag visibility)
    # ------------------------------------------------------------------

    # Sync-safe fallback: query settings using sync session
    def _get_monitored_tag_key_sync(self, org_id: UUID) -> str:
        """Get monitored tag key from tenant_settings (sync version)."""
        from sqlalchemy import select
        from app.core.database import get_sync_session_factory
        from app.domains.settings.models import TenantSetting

        SessionFactory = get_sync_session_factory()
        with SessionFactory() as db:
            result = db.execute(
                select(TenantSetting).where(
                    TenantSetting.org_id == org_id,
                    TenantSetting.setting_key == "monitored_tag_key",
                )
            )
            row = result.scalar_one_or_none()
            return row.setting_value if row else "team"

    def get_tag_compliance(
        self,
        org_id: UUID,
        *,
        tag_key: str | None = None,
        days: int = _DAYS,
    ) -> TagComplianceMetrics:
        """Returns compliance metrics for a monitored tag key.

        Uses cost_facts.tags Map to check if the configured key is present.
        Does NOT use owner_team or Resource Group inference.

        Args:
            org_id: Organization UUID
            tag_key: If provided, overrides tenant settings (URL param use case).
                    If None, reads from tenant_settings.
        """
        # Resolve effective tag key
        if tag_key is None:
            tag_key = self._get_monitored_tag_key_sync(org_id)

        cutoff = (date.today() - timedelta(days=days)).isoformat()

        # Main compliance query using tags Map
        main_rows = _safe_query(
            """
            SELECT
                count()                            AS total_records,
                sum(cost_usd)                      AS total_cost,
                sumIf(1, mapContains(tags, {tag_key:String})) AS tagged_records,
                sumIf(cost_usd, mapContains(tags, {tag_key:String})) AS tagged_cost,
                sumIf(1, NOT mapContains(tags, {tag_key:String})) AS untagged_records,
                sumIf(cost_usd, NOT mapContains(tags, {tag_key:String})) AS untagged_cost
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND resource_id != ''
            """,
            {"org_id": str(org_id), "cutoff": cutoff, "tag_key": tag_key},
        )

        if not main_rows or main_rows[0].get("total_records", 0) == 0:
            return TagComplianceMetrics(
                configured_tag_key=tag_key,
                total_cost=0.0,
                tagged_cost=0.0,
                untagged_cost=0.0,
                coverage_pct=100.0,
                total_records=0,
                tagged_records=0,
                untagged_records=0,
                top_untagged_resource_groups=[],
                top_untagged_services=[],
            )

        r = main_rows[0]
        total_records = int(r.get("total_records") or 0)
        total_cost = float(r.get("total_cost") or 0)
        tagged_records = int(r.get("tagged_records") or 0)
        tagged_cost = float(r.get("tagged_cost") or 0)
        untagged_records = int(r.get("untagged_records") or 0)
        untagged_cost = float(r.get("untagged_cost") or 0)

        coverage_pct = round(100.0 * tagged_records / max(total_records, 1), 1)

        # Top untagged resource groups (extracted from Azure resource_id via regex)
        # Pattern: /subscriptions/.../resourcegroups/NOME_RG/providers/...
        rg_rows = _safe_query(
            """
            SELECT
                regexpExtract(resource_id, 'resourcegroups/([^/]+)', 1) AS name,
                sum(cost_usd) AS cost_usd,
                count()       AS record_count
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND resource_id != ''
              AND NOT mapContains(tags, {tag_key:String})
            GROUP BY name
            HAVING name != '' AND name IS NOT NULL
            ORDER BY cost_usd DESC
            LIMIT 10
            """,
            {"org_id": str(org_id), "cutoff": cutoff, "tag_key": tag_key},
        )
        top_untagged_resource_groups = [
            TopUntaggedRow(
                name=r.get("name") or "N/A",
                cost_usd=round(float(r.get("cost_usd") or 0), 2),
                record_count=int(r.get("record_count") or 0),
            )
            for r in rg_rows
        ]

        # Top untagged services
        svc_rows = _safe_query(
            """
            SELECT
                if(service = '' OR service IS NULL, 'N/A', service) AS name,
                sum(cost_usd) AS cost_usd,
                count()       AS record_count
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {cutoff:String}
              AND resource_id != ''
              AND NOT mapContains(tags, {tag_key:String})
            GROUP BY name
            ORDER BY cost_usd DESC
            LIMIT 10
            """,
            {"org_id": str(org_id), "cutoff": cutoff, "tag_key": tag_key},
        )
        top_untagged_services = [
            TopUntaggedRow(
                name=r.get("name") or "N/A",
                cost_usd=round(float(r.get("cost_usd") or 0), 2),
                record_count=int(r.get("record_count") or 0),
            )
            for r in svc_rows
        ]

        return TagComplianceMetrics(
            configured_tag_key=tag_key,
            total_cost=round(total_cost, 2),
            tagged_cost=round(tagged_cost, 2),
            untagged_cost=round(untagged_cost, 2),
            coverage_pct=coverage_pct,
            total_records=total_records,
            tagged_records=tagged_records,
            untagged_records=untagged_records,
            top_untagged_resource_groups=top_untagged_resource_groups,
            top_untagged_services=top_untagged_services,
        )
