from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.auth.models import Organization
from app.domains.decision_engine.models import OptimizationOpportunity
from app.domains.intel.llm_service import LlmService, _mock_explain_recommendation
from app.domains.intel.models import UsageObservation
from app.domains.intel.schemas import ExplainRecommendationOut

log = get_logger(__name__)


class OpportunityExplanationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.llm = LlmService()

    async def explain_opportunity(
        self,
        *,
        org_id: UUID,
        opportunity_id: UUID,
        language: str = "en",
    ) -> ExplainRecommendationOut:
        await self._require_ai_feature(org_id)

        opportunity = await self._get_opportunity(org_id=org_id, opportunity_id=opportunity_id)
        if opportunity is None:
            raise ValueError("Opportunity not found")

        usage = await self._get_usage_observations(
            org_id=org_id,
            account_id=opportunity.account_id,
            resource_id=opportunity.resource_id,
        )
        events = self._get_recent_events(
            org_id=org_id,
            account_id=opportunity.account_id,
            resource_id=opportunity.resource_id,
        )

        context = {
            "language": (language or "en").lower(),
            "workspace": {"org_id": str(org_id), "plan": (await self._get_org_plan(org_id))},
            "recommendation": {
                "id": str(opportunity.id),
                "title": opportunity.title,
                "description": opportunity.description,
                "category": opportunity.category.value,
                "status": opportunity.status.value,
                "estimated_monthly_savings_usd": opportunity.estimated_monthly_savings_usd,
                "estimated_annual_savings_usd": opportunity.estimated_annual_savings_usd,
                "composite_score": opportunity.composite_score,
                "risk_level": opportunity.risk_level.value,
                "effort_level": opportunity.effort_level.value,
                "resource_id": opportunity.resource_id,
                "resource_name": opportunity.resource_name,
                "sku_name": opportunity.sku_name,
                "machine_family": opportunity.machine_family,
                "service": opportunity.service,
                "region": opportunity.region,
                "environment": opportunity.environment,
                "owner_team": opportunity.owner_team,
            },
            "usage_observations": usage,
            "events": events,
        }

        try:
            return await self.llm.explain_recommendation(context)
        except Exception as exc:
            log.warning(
                "decision_engine.explain_opportunity.llm_failed",
                org_id=str(org_id),
                opportunity_id=str(opportunity_id),
                error=str(exc),
            )
            out = _mock_explain_recommendation(context, language=(language or "en").lower())
            out.debug = {"llm_error": str(exc)}
            return out

    async def _require_ai_feature(self, org_id: UUID) -> None:
        plan = await self._get_org_plan(org_id)
        if not self._plan_has_ai(plan):
            raise PermissionError("AI feature not enabled for this workspace plan")

    async def _get_org_plan(self, org_id: UUID) -> str:
        result = await self.db.execute(select(Organization.plan).where(Organization.id == org_id))
        plan = result.scalar_one_or_none()
        return str(plan or "unknown")

    def _plan_has_ai(self, plan: str) -> bool:
        if not self.settings.is_production:
            return True
        allowed = {p.strip().lower() for p in (self.settings.ai_enabled_plans or "").split(",") if p.strip()}
        if not allowed:
            allowed = {"b", "plan_b", "ai", "enterprise", "pro_ai", "growth_ai"}
        p = (plan or "").strip().lower()
        return p in allowed or p.endswith("_ai") or "ai" in p

    async def _get_opportunity(
        self, *, org_id: UUID, opportunity_id: UUID
    ) -> OptimizationOpportunity | None:
        result = await self.db.execute(
            select(OptimizationOpportunity).where(
                OptimizationOpportunity.id == opportunity_id,
                OptimizationOpportunity.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_usage_observations(
        self,
        *,
        org_id: UUID,
        account_id: UUID | None,
        resource_id: str | None,
    ) -> list[dict[str, Any]]:
        if account_id is None or not resource_id:
            return []

        now = datetime.now(timezone.utc)
        lookback_start = now - timedelta(hours=24)
        result = await self.db.execute(
            select(UsageObservation)
            .where(
                UsageObservation.org_id == org_id,
                UsageObservation.account_id == account_id,
                UsageObservation.resource_id == resource_id,
                UsageObservation.window_start >= lookback_start,
            )
            .order_by(UsageObservation.window_start.desc())
            .limit(18)
        )
        rows = list(result.scalars().all())
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "metric_name": row.metric_name,
                    "avg_value": row.avg_value,
                    "p95_value": row.p95_value,
                    "max_value": row.max_value,
                    "min_value": row.min_value,
                    "sample_count": row.sample_count,
                    "unit": row.unit,
                    "region": row.region,
                    "environment": row.environment,
                    "window_start": row.window_start.isoformat(),
                    "window_end": row.window_end.isoformat(),
                }
            )
        return out

    def _get_recent_events(
        self,
        *,
        org_id: UUID,
        account_id: UUID | None,
        resource_id: str | None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "org_id": str(org_id),
            "start": (datetime.now(timezone.utc) - timedelta(days=7)),
        }
        account_filter = ""
        resource_filter = ""
        if account_id is not None:
            account_filter = "AND account_id = {account_id:String}"
            params["account_id"] = str(account_id)
        if resource_id:
            resource_filter = "AND resource_id = {resource_id:String}"
            params["resource_id"] = resource_id

        try:
            rows = execute_query(
                f"""
                SELECT
                  timestamp,
                  provider,
                  event_type,
                  severity,
                  description
                FROM event_facts
                WHERE org_id = {{org_id:String}}
                  {account_filter}
                  {resource_filter}
                  AND timestamp >= {{start:DateTime}}
                ORDER BY timestamp DESC
                LIMIT 20
                """,
                params,
            )
            return [
                {
                    "timestamp": str(row.get("timestamp") or ""),
                    "provider": str(row.get("provider") or ""),
                    "event_type": str(row.get("event_type") or ""),
                    "severity": str(row.get("severity") or ""),
                    "description": str(row.get("description") or ""),
                }
                for row in rows
            ]
        except Exception as exc:
            log.warning(
                "decision_engine.explain_opportunity.events_query_failed",
                org_id=str(org_id),
                reason=str(exc),
            )
            return []
