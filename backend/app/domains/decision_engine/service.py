from __future__ import annotations
from datetime import datetime, timezone
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.decision_engine.models import (
    OptimizationOpportunity,
    OpportunityCategory,
    OpportunityStatus,
)
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.domains.decision_engine.schemas import (
    OpportunityCreate,
    OpportunitySummary,
    OpportunityStatusUpdate,
)
from app.domains.decision_engine.scorer import PLAYBOOKS, compute_score

log = get_logger(__name__)


class DecisionEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_opportunities_for_account(
        self, org_id: UUID, account_id: UUID
    ) -> list[OptimizationOpportunity]:
        """Generate opportunities from ClickHouse cost data."""
        from app.core.clickhouse import execute_query

        try:
            rows = execute_query(
                """
                SELECT
                    service,
                    owner_team,
                    environment,
                    region,
                    sum(cost_usd) as monthly_cost,
                    argMax(resource_id, date) as resource_id,
                    argMax(resource_name, date) as resource_name,
                    argMax(sku_name, date) as sku_name,
                    count() as data_points
                FROM cost_facts
                WHERE org_id = {org_id:String}
                  AND account_id = {account_id:String}
                  AND date >= today() - 30
                GROUP BY service, owner_team, environment, region
                HAVING monthly_cost > 50
                ORDER BY monthly_cost DESC
                LIMIT 50
                """,
                {"org_id": str(org_id), "account_id": str(account_id)},
            )
        except Exception as e:
            log.warning("decision_engine.cost_query.failed", error=str(e))
            rows = []

        active_statuses = (
            OpportunityStatus.OPEN,
            OpportunityStatus.IN_PROGRESS,
            OpportunityStatus.VALIDATED,
        )
        existing_result = await self.db.execute(
            select(OptimizationOpportunity)
            .where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.account_id == account_id,
                OptimizationOpportunity.status.in_(active_statuses),
            )
            .order_by(OptimizationOpportunity.created_at.desc())
        )
        existing_items = list(existing_result.scalars().all())

        existing_by_key: dict[str, OptimizationOpportunity] = {}
        duplicate_existing: list[OptimizationOpportunity] = []
        for item in existing_items:
            key = _opportunity_dedupe_key(
                category=item.category,
                service=item.service,
                owner_team=item.owner_team,
                environment=item.environment,
                region=item.region,
                resource_id=item.resource_id,
                account_id=item.account_id,
            )
            if key in existing_by_key:
                duplicate_existing.append(item)
                continue
            existing_by_key[key] = item

        now = datetime.now(timezone.utc)
        opportunities: list[OptimizationOpportunity] = []
        seen_keys_in_run: set[str] = set()
        for row in rows:
            monthly_cost = float(row.get("monthly_cost", 0))
            service = str(row.get("service", "unknown"))
            env = str(row.get("environment", "unknown"))
            team = str(row.get("owner_team", "untagged"))
            resource_id = str(row.get("resource_id", ""))
            resource_name = str(row.get("resource_name", ""))
            sku_name = (row.get("sku_name") or "").strip()
            machine_family = _infer_machine_family(sku_name, resource_name, service)
            region = str(row.get("region", ""))

            # Determine category heuristically
            category = _classify_service(service)
            estimated_savings = _estimate_savings(category, monthly_cost)
            if estimated_savings < 10:
                continue

            score = compute_score(
                category=category,
                monthly_savings_usd=estimated_savings,
                environment=env,
            )

            dedupe_key = _opportunity_dedupe_key(
                category=category,
                service=service,
                owner_team=team,
                environment=env,
                region=region,
                resource_id=resource_id,
                account_id=account_id,
            )
            if dedupe_key in seen_keys_in_run:
                continue
            seen_keys_in_run.add(dedupe_key)

            existing = existing_by_key.get(dedupe_key)
            if existing is not None:
                existing.title = _generate_title(category, service, team)
                existing.description = _generate_description(category, service, monthly_cost, estimated_savings)
                existing.category = category
                existing.financial_impact_score = score.financial_impact_score
                existing.risk_score = score.risk_score
                existing.effort_score = score.effort_score
                existing.criticality_score = score.criticality_score
                existing.composite_score = score.composite_score
                existing.estimated_monthly_savings_usd = estimated_savings
                existing.estimated_annual_savings_usd = round(estimated_savings * 12, 2)
                existing.current_monthly_cost_usd = monthly_cost
                existing.risk_level = score.risk_level
                existing.effort_level = score.effort_level
                existing.resource_id = resource_id
                existing.resource_name = resource_name
                existing.sku_name = sku_name or None
                existing.machine_family = machine_family
                existing.service = service
                existing.region = region
                existing.environment = env
                existing.owner_team = team
                existing.score_rationale = score.rationale
                existing.playbook = PLAYBOOKS.get(category)
                existing.detected_at = now
                op = existing
            else:
                op = OptimizationOpportunity(
                    org_id=org_id,
                    account_id=account_id,
                    title=_generate_title(category, service, team),
                    description=_generate_description(category, service, monthly_cost, estimated_savings),
                    category=category,
                    financial_impact_score=score.financial_impact_score,
                    risk_score=score.risk_score,
                    effort_score=score.effort_score,
                    criticality_score=score.criticality_score,
                    composite_score=score.composite_score,
                    estimated_monthly_savings_usd=estimated_savings,
                    estimated_annual_savings_usd=round(estimated_savings * 12, 2),
                    current_monthly_cost_usd=monthly_cost,
                    risk_level=score.risk_level,
                    effort_level=score.effort_level,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    sku_name=sku_name or None,
                    machine_family=machine_family,
                    service=service,
                    region=region,
                    environment=env,
                    owner_team=team,
                    score_rationale=score.rationale,
                    playbook=PLAYBOOKS.get(category),
                )
                self.db.add(op)
                existing_by_key[dedupe_key] = op
            opportunities.append(op)

        for duplicated in duplicate_existing:
            if duplicated.status != OpportunityStatus.OPEN:
                continue
            duplicated.status = OpportunityStatus.DISMISSED
            duplicated.score_rationale = (
                (duplicated.score_rationale or "").strip()
                + "\n\n[system] Auto-dismissed duplicate opportunity."
            ).strip()

        await self.db.flush()
        log.info("decision_engine.generated", org_id=str(org_id), count=len(opportunities))
        return opportunities

    async def create_opportunity(self, org_id: UUID, req: OpportunityCreate) -> OptimizationOpportunity:
        score = compute_score(
            category=req.category,
            monthly_savings_usd=req.estimated_monthly_savings_usd,
            environment=req.environment,
            override_risk=req.risk_level,
            override_effort=req.effort_level,
        )
        op = OptimizationOpportunity(
            org_id=org_id,
            account_id=req.account_id,
            title=req.title,
            description=req.description,
            category=req.category,
            financial_impact_score=score.financial_impact_score,
            risk_score=score.risk_score,
            effort_score=score.effort_score,
            criticality_score=score.criticality_score,
            composite_score=score.composite_score,
            estimated_monthly_savings_usd=req.estimated_monthly_savings_usd,
            estimated_annual_savings_usd=round(req.estimated_monthly_savings_usd * 12, 2),
            current_monthly_cost_usd=req.current_monthly_cost_usd,
            risk_level=score.risk_level,
            effort_level=score.effort_level,
            resource_id=req.resource_id,
            resource_name=req.resource_name,
            sku_name=req.sku_name,
            machine_family=req.machine_family,
            service=req.service,
            region=req.region,
            environment=req.environment,
            owner_team=req.owner_team,
            score_rationale=score.rationale,
            playbook=PLAYBOOKS.get(req.category),
        )
        self.db.add(op)
        await self.db.flush()
        await self.db.refresh(op)

        notif = NotificationsService(self.db)
        await notif.create_realtime_alert(
            org_id=org_id,
            category=AlertCategory.OPTIMIZATION,
            severity=AlertSeverity.CRITICAL,
            event_type="opportunity.created",
            title=f"New optimization opportunity: {op.title}",
            body=op.description,
            source_type="optimization_opportunity",
            source_id=str(op.id),
            extra_metadata={
                "estimated_monthly_savings_usd": op.estimated_monthly_savings_usd,
                "category": op.category.value,
            },
        )
        return op

    async def list_opportunities(
        self,
        org_id: UUID,
        status: OpportunityStatus | None = None,
        category: OpportunityCategory | None = None,
        owner_team: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OptimizationOpportunity], int]:
        filters = [OptimizationOpportunity.org_id == org_id]
        if status:
            filters.append(OptimizationOpportunity.status == status)
        if category:
            filters.append(OptimizationOpportunity.category == category)
        if owner_team:
            filters.append(OptimizationOpportunity.owner_team == owner_team)

        count_result = await self.db.execute(
            select(func.count()).select_from(OptimizationOpportunity).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(OptimizationOpportunity)
            .where(*filters)
            .order_by(OptimizationOpportunity.composite_score.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def get_opportunity(self, org_id: UUID, opp_id: UUID) -> OptimizationOpportunity | None:
        result = await self.db.execute(
            select(OptimizationOpportunity).where(
                OptimizationOpportunity.id == opp_id,
                OptimizationOpportunity.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, org_id: UUID, opp_id: UUID, req: OpportunityStatusUpdate
    ) -> OptimizationOpportunity | None:
        op = await self.get_opportunity(org_id, opp_id)
        if not op:
            return None
        op.status = req.status
        await self.db.flush()
        await self.db.refresh(op)
        return op

    async def get_summary(self, org_id: UUID) -> OpportunitySummary:
        result = await self.db.execute(
            select(
                func.count(OptimizationOpportunity.id).label("total"),
                func.sum(OptimizationOpportunity.estimated_monthly_savings_usd).label("total_savings"),
            ).where(OptimizationOpportunity.org_id == org_id)
        )
        row = result.one()
        total = row.total or 0
        total_savings = float(row.total_savings or 0)

        open_count = await self._count_by_status(org_id, OpportunityStatus.OPEN)
        in_progress = await self._count_by_status(org_id, OpportunityStatus.IN_PROGRESS)
        resolved = await self._count_by_status(org_id, OpportunityStatus.RESOLVED)

        top_cat_row = await self.db.execute(
            select(OptimizationOpportunity.category, func.count().label("cnt"))
            .where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == OpportunityStatus.OPEN,
            )
            .group_by(OptimizationOpportunity.category)
            .order_by(func.count().desc())
            .limit(1)
        )
        top_cat = top_cat_row.first()

        return OpportunitySummary(
            total=total,
            open=open_count,
            in_progress=in_progress,
            resolved=resolved,
            total_potential_savings_usd=total_savings,
            top_category=top_cat[0].value if top_cat else None,
        )

    async def _count_by_status(self, org_id: UUID, status: OpportunityStatus) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == status,
            )
        )
        return result.scalar() or 0


# ── Heuristics ────────────────────────────────────────────────────────────────

def _classify_service(service: str) -> OpportunityCategory:
    s = service.lower()
    if any(k in s for k in ("virtual machine", "compute")):
        return OpportunityCategory.RIGHTSIZING
    if any(k in s for k in ("storage", "blob", "disk")):
        return OpportunityCategory.STORAGE_OPTIMIZATION
    if any(k in s for k in ("bandwidth", "network", "cdn")):
        return OpportunityCategory.NETWORK_OPTIMIZATION
    if any(k in s for k in ("sql", "database", "cosmos")):
        return OpportunityCategory.RIGHTSIZING
    if any(k in s for k in ("function", "app service")):
        return OpportunityCategory.IDLE_RESOURCES
    if any(k in s for k in ("kubernetes", "aks")):
        return OpportunityCategory.RIGHTSIZING
    return OpportunityCategory.IDLE_RESOURCES


def _estimate_savings(category: OpportunityCategory, monthly_cost: float) -> float:
    rates = {
        OpportunityCategory.IDLE_RESOURCES: 0.80,
        OpportunityCategory.RIGHTSIZING: 0.30,
        OpportunityCategory.STORAGE_OPTIMIZATION: 0.40,
        OpportunityCategory.NETWORK_OPTIMIZATION: 0.25,
        OpportunityCategory.RESERVED_INSTANCES: 0.35,
        OpportunityCategory.LICENSE_OPTIMIZATION: 0.20,
        OpportunityCategory.ARCHITECTURE_CHANGE: 0.45,
    }
    return round(monthly_cost * rates.get(category, 0.20), 2)


def _generate_title(category: OpportunityCategory, service: str, team: str) -> str:
    titles = {
        OpportunityCategory.IDLE_RESOURCES: f"Idle {service} resources in team {team}",
        OpportunityCategory.RIGHTSIZING: f"Rightsize {service} for team {team}",
        OpportunityCategory.STORAGE_OPTIMIZATION: f"Optimize {service} storage tier",
        OpportunityCategory.NETWORK_OPTIMIZATION: f"Reduce {service} network costs",
        OpportunityCategory.RESERVED_INSTANCES: f"Purchase Reserved Instances for {service}",
        OpportunityCategory.LICENSE_OPTIMIZATION: f"Optimize {service} licenses",
        OpportunityCategory.ARCHITECTURE_CHANGE: f"Architectural optimization for {service}",
    }
    return titles.get(category, f"Optimize {service}")


def _generate_description(
    category: OpportunityCategory, service: str, monthly_cost: float, estimated_savings: float
) -> str:
    rate = estimated_savings / monthly_cost * 100 if monthly_cost else 0
    return (
        f"{service} is currently costing ${monthly_cost:,.2f}/month. "
        f"Analysis indicates a {rate:.0f}% cost reduction opportunity (${estimated_savings:,.2f}/month) "
        f"through {category.value.replace('_', ' ')}."
    )


def _extract_family_token(raw_value: str) -> str | None:
    value = (raw_value or "").strip()
    if not value:
        return None

    normalized = re.sub(r"^standard[_-]", "", value, flags=re.IGNORECASE)
    normalized = normalized.strip()
    if not normalized:
        return None

    # AWS-style (e.g., m5.large -> m5) and GCP-style (e.g., n2-standard-4 -> n2).
    dotted_prefix = re.match(r"^([a-z]\d+)\.", normalized, flags=re.IGNORECASE)
    if dotted_prefix:
        return dotted_prefix.group(1).lower()
    hyphen_prefix = re.match(r"^([a-z]\d+)-", normalized, flags=re.IGNORECASE)
    if hyphen_prefix:
        return hyphen_prefix.group(1).lower()

    # Azure-style (e.g., Standard_D4s_v5 -> D4s).
    token_match = re.search(r"\b([A-Za-z]+\d+[A-Za-z0-9]*)\b", normalized)
    if token_match:
        return token_match.group(1)

    return None


def _infer_machine_family(sku_name: str | None, resource_name: str | None, service: str | None) -> str | None:
    for candidate in (sku_name or "", resource_name or "", service or ""):
        token = _extract_family_token(candidate)
        if token:
            return token
    return None


def _norm_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_uuid(value: UUID | None) -> str:
    return str(value) if value is not None else ""


def _norm_resource_id(value: str | None) -> str:
    return _norm_text(value).rstrip("/")


def _opportunity_dedupe_key(
    *,
    category: OpportunityCategory,
    service: str | None,
    owner_team: str | None,
    environment: str | None,
    region: str | None,
    resource_id: str | None,
    account_id: UUID | None,
) -> str:
    # A stable identity for "same optimization target" across scoring runs.
    return "|".join(
        [
            _norm_uuid(account_id),
            category.value,
            _norm_resource_id(resource_id),
            _norm_text(service),
            _norm_text(owner_team),
            _norm_text(environment),
            _norm_text(region),
        ]
    )
