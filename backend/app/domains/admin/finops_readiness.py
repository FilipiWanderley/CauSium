"""
FinOps Readiness Diagnostics — read-only endpoint for recommendation pipeline health.

Returns a comprehensive assessment of whether a tenant has sufficient data
for the decision engine to generate real recommendations.

Design principles:
- Strictly read-only — no mutations, no side effects
- Safe null handling — never fails on missing data
- No sensitive data exposure — counts and booleans only
- Protected by PLATFORM_ADMIN role
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_platform_admin
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["platform-admin"])


# ── Response Schema ───────────────────────────────────────────────────────────


class CostCoverage(BaseModel):
    total_cost_facts_30d: int = 0
    first_cost_date: str | None = None
    last_cost_date: str | None = None
    providers: list[str] = []
    subscriptions_count: int = 0
    currencies: list[str] = []
    total_cost_30d_usd: float = 0.0


class UsageCoverage(BaseModel):
    total_usage_facts_30d: int = 0
    metric_names: list[str] = []
    has_cpu_metric: bool = False
    has_memory_metric: bool = False
    has_aks_agentpool_metrics: bool = False
    agentpool_resource_count: int = 0
    observation_days: int = 0


class OpportunitiesStatus(BaseModel):
    total_opportunities: int = 0
    opportunities_by_status: dict[str, int] = {}
    opportunities_by_category: dict[str, int] = {}
    open_opportunities: int = 0
    generated_recently_count: int = 0
    latest_opportunity_at: str | None = None


class RecommendationReadiness(BaseModel):
    vm_rightsizing_ready: bool = False
    aks_rightsizing_ready: bool = False
    autoscaler_ready: bool = False
    blockers: list[str] = []
    warnings: list[str] = []


class ExportReadiness(BaseModel):
    csv_export_expected_rows: int = 0
    csv_export_ready: bool = False


class DataFreshness(BaseModel):
    cost_data_stale: bool = True
    usage_data_stale: bool = True
    latest_cost_seen_at: str | None = None
    latest_usage_seen_at: str | None = None


class FinOpsReadinessResponse(BaseModel):
    org_id: str
    assessed_at: str
    cost_coverage: CostCoverage
    usage_coverage: UsageCoverage
    opportunities: OpportunitiesStatus
    recommendation_readiness: RecommendationReadiness
    export_readiness: ExportReadiness
    data_freshness: DataFreshness


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get("/finops-readiness", response_model=FinOpsReadinessResponse)
async def get_finops_readiness(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_platform_admin),
) -> FinOpsReadinessResponse:
    """Read-only diagnostics for recommendation pipeline readiness."""
    org_id = current_user.org_id
    now = datetime.now(timezone.utc)

    cost = await _assess_cost_coverage(org_id)
    usage = await _assess_usage_coverage(org_id)
    opps = await _assess_opportunities(db, org_id)
    readiness = _assess_readiness(cost, usage)
    export = ExportReadiness(
        csv_export_expected_rows=opps.total_opportunities,
        csv_export_ready=opps.total_opportunities > 0,
    )
    freshness = _assess_freshness(cost, usage)

    return FinOpsReadinessResponse(
        org_id=str(org_id),
        assessed_at=now.isoformat(),
        cost_coverage=cost,
        usage_coverage=usage,
        opportunities=opps,
        recommendation_readiness=readiness,
        export_readiness=export,
        data_freshness=freshness,
    )


# ── Internal helpers (read-only) ─────────────────────────────────────────────


async def _assess_cost_coverage(org_id: UUID) -> CostCoverage:
    """Query ClickHouse for cost data coverage. Read-only."""
    try:
        from app.core.clickhouse import execute_query

        rows = execute_query(
            """
            SELECT
                count() AS total_rows,
                min(date) AS first_date,
                max(date) AS last_date,
                groupUniqArray(provider) AS providers,
                uniqExact(subscription_id) AS subs_count,
                groupUniqArray(currency) AS currencies,
                sumIf(cost_usd, date >= today() - 30) AS total_cost_30d,
                countIf(date >= today() - 30) AS rows_30d
            FROM cost_facts
            WHERE org_id = {org_id:String}
            """,
            {"org_id": str(org_id)},
        )
        if not rows:
            return CostCoverage()

        row = rows[0]
        first_date = row.get("first_date")
        last_date = row.get("last_date")

        return CostCoverage(
            total_cost_facts_30d=int(row.get("rows_30d") or 0),
            first_cost_date=str(first_date) if first_date else None,
            last_cost_date=str(last_date) if last_date else None,
            providers=list(row.get("providers") or []),
            subscriptions_count=int(row.get("subs_count") or 0),
            currencies=list(row.get("currencies") or []),
            total_cost_30d_usd=round(float(row.get("total_cost_30d") or 0), 2),
        )
    except Exception as e:
        log.warning("finops_readiness.cost_coverage.failed", error=str(e))
        return CostCoverage()


async def _assess_usage_coverage(org_id: UUID) -> UsageCoverage:
    """Query ClickHouse for usage/performance data coverage. Read-only."""
    try:
        from app.core.clickhouse import execute_query

        rows = execute_query(
            """
            SELECT
                countIf(date >= today() - 30) AS rows_30d,
                groupUniqArray(metric_name) AS metric_names,
                uniqExactIf(
                    date,
                    positionCaseInsensitiveUTF8(metric_name, 'cpu') > 0
                ) AS cpu_days,
                uniqExactIf(
                    date,
                    positionCaseInsensitiveUTF8(metric_name, 'memory') > 0
                ) AS memory_days,
                countIf(
                    match(resource_id, '(?i).*/managedClusters/[^/]+/agentPools/[^/]+$')
                    AND date >= today() - 30
                ) AS aks_rows,
                uniqExactIf(
                    resource_id,
                    match(resource_id, '(?i).*/managedClusters/[^/]+/agentPools/[^/]+$')
                    AND date >= today() - 30
                ) AS aks_resources
            FROM usage_facts
            WHERE org_id = {org_id:String}
            """,
            {"org_id": str(org_id)},
        )
        if not rows:
            return UsageCoverage()

        row = rows[0]
        metric_names = list(row.get("metric_names") or [])
        cpu_days = int(row.get("cpu_days") or 0)
        memory_days = int(row.get("memory_days") or 0)

        has_cpu = any("cpu" in m.lower() for m in metric_names)
        has_memory = any("memory" in m.lower() or "mem" in m.lower() for m in metric_names)

        return UsageCoverage(
            total_usage_facts_30d=int(row.get("rows_30d") or 0),
            metric_names=metric_names,
            has_cpu_metric=has_cpu,
            has_memory_metric=has_memory,
            has_aks_agentpool_metrics=int(row.get("aks_rows") or 0) > 0,
            agentpool_resource_count=int(row.get("aks_resources") or 0),
            observation_days=max(cpu_days, memory_days),
        )
    except Exception as e:
        log.warning("finops_readiness.usage_coverage.failed", error=str(e))
        return UsageCoverage()


async def _assess_opportunities(db: AsyncSession, org_id: UUID) -> OpportunitiesStatus:
    """Query PostgreSQL for current opportunities state. Read-only."""
    from app.domains.decision_engine.models import OptimizationOpportunity

    try:
        # Total count
        total_result = await db.execute(
            select(func.count()).select_from(OptimizationOpportunity).where(
                OptimizationOpportunity.org_id == org_id
            )
        )
        total = total_result.scalar_one()

        # By status
        status_result = await db.execute(
            select(
                OptimizationOpportunity.status,
                func.count(),
            )
            .where(OptimizationOpportunity.org_id == org_id)
            .group_by(OptimizationOpportunity.status)
        )
        by_status = {str(row[0].value): row[1] for row in status_result.all()}

        # By category
        cat_result = await db.execute(
            select(
                OptimizationOpportunity.category,
                func.count(),
            )
            .where(OptimizationOpportunity.org_id == org_id)
            .group_by(OptimizationOpportunity.category)
        )
        by_category = {str(row[0].value): row[1] for row in cat_result.all()}

        # Recent (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_result = await db.execute(
            select(func.count()).select_from(OptimizationOpportunity).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.created_at >= seven_days_ago,
            )
        )
        recent_count = recent_result.scalar_one()

        # Latest
        latest_result = await db.execute(
            select(func.max(OptimizationOpportunity.created_at)).where(
                OptimizationOpportunity.org_id == org_id
            )
        )
        latest_at = latest_result.scalar_one()

        open_count = by_status.get("open", 0)

        return OpportunitiesStatus(
            total_opportunities=total,
            opportunities_by_status=by_status,
            opportunities_by_category=by_category,
            open_opportunities=open_count,
            generated_recently_count=recent_count,
            latest_opportunity_at=latest_at.isoformat() if latest_at else None,
        )
    except Exception as e:
        log.warning("finops_readiness.opportunities.failed", error=str(e))
        return OpportunitiesStatus()


def _assess_readiness(cost: CostCoverage, usage: UsageCoverage) -> RecommendationReadiness:
    """Determine recommendation readiness from coverage data. Pure function."""
    blockers: list[str] = []
    warnings: list[str] = []

    # VM Rightsizing requires CPU + Memory with 7+ days
    vm_ready = (
        usage.has_cpu_metric
        and usage.has_memory_metric
        and usage.observation_days >= 7
        and cost.total_cost_facts_30d > 0
    )
    if not usage.has_cpu_metric:
        blockers.append("Missing CPU metrics in usage_facts")
    if not usage.has_memory_metric:
        blockers.append("Missing Memory metrics in usage_facts")
    if usage.observation_days < 7:
        blockers.append(f"Insufficient observation window ({usage.observation_days} days, need 7+)")

    # AKS requires agentPool resource_ids with CPU + Memory
    aks_ready = (
        usage.has_aks_agentpool_metrics
        and usage.agentpool_resource_count > 0
        and usage.has_cpu_metric
        and usage.has_memory_metric
        and cost.total_cost_facts_30d > 0
    )
    if not usage.has_aks_agentpool_metrics:
        blockers.append("No AKS agentPool metrics found in usage_facts")

    # Autoscaler uses same data as AKS rightsizing
    autoscaler_ready = aks_ready

    # Warnings
    if cost.total_cost_30d_usd < 500:
        warnings.append(f"Low total cost (${cost.total_cost_30d_usd:.0f}/30d) — few opportunities expected")
    if usage.observation_days < 14:
        warnings.append(f"Short observation window ({usage.observation_days} days) — confidence will be lower")
    if cost.total_cost_facts_30d == 0:
        blockers.append("No cost data in last 30 days")

    return RecommendationReadiness(
        vm_rightsizing_ready=vm_ready,
        aks_rightsizing_ready=aks_ready,
        autoscaler_ready=autoscaler_ready,
        blockers=blockers,
        warnings=warnings,
    )


def _assess_freshness(cost: CostCoverage, usage: UsageCoverage) -> DataFreshness:
    """Assess data freshness. Pure function."""

    cost_stale = True
    if cost.last_cost_date:
        try:
            last_cost = date.fromisoformat(str(cost.last_cost_date))
            cost_stale = (date.today() - last_cost).days > 3
        except (ValueError, TypeError):
            pass

    usage_stale = True
    if usage.observation_days > 0 and usage.total_usage_facts_30d > 0:
        # If we have data in the last 30 days, consider it fresh enough
        usage_stale = usage.observation_days < 3

    return DataFreshness(
        cost_data_stale=cost_stale,
        usage_data_stale=usage_stale,
        latest_cost_seen_at=str(cost.last_cost_date) if cost.last_cost_date else None,
        latest_usage_seen_at=None,  # Would need separate query; keep simple
    )
