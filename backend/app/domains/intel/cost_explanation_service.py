from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.auth.models import Organization
from app.domains.intel.llm_service import _mock_explain_cost_change, LlmService
from app.domains.intel.schemas import ExplainCostChangeOut

log = get_logger(__name__)


@dataclass(frozen=True)
class _Period:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def start_dt(self) -> datetime:
        return datetime.combine(self.start, time.min).replace(tzinfo=timezone.utc)

    @property
    def end_dt_exclusive(self) -> datetime:
        return datetime.combine(self.end + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)


class CostExplanationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.llm = LlmService()

    async def explain_cost_change(
        self,
        *,
        org_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
    ) -> ExplainCostChangeOut:
        await self._require_ai_feature(org_id)

        current = _Period(start=start_date, end=end_date)
        prev_end = current.start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=current.days - 1)
        previous = _Period(start=prev_start, end=prev_end)

        delta = self._get_cost_delta(org_id, current=current, previous=previous, provider=provider)
        drivers = self._get_service_drivers(org_id, current=current, previous=previous, provider=provider)
        events = self._get_events(org_id, current=current, provider=provider)
        recs = self._get_cost_recommendations(org_id, current=current, provider=provider)

        context = {
            "workspace": {"org_id": str(org_id), "plan": (await self._get_org_plan(org_id))},
            "period": {
                "current": {"start": str(current.start), "end": str(current.end)},
                "previous": {"start": str(previous.start), "end": str(previous.end)},
                "days": current.days,
            },
            "delta": delta,
            "drivers": drivers,
            "events": events,
            "recommendations": recs,
        }

        try:
            return await self.llm.explain_cost_change(context)
        except Exception as exc:
            log.warning("intel.explain_cost_change.llm_failed", org_id=str(org_id), error=str(exc))
            out = _mock_explain_cost_change(context)
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
        allowed = {p.strip().lower() for p in (self.settings.ai_enabled_plans or "").split(",") if p.strip()}
        if not allowed:
            allowed = {"b", "plan_b", "ai", "enterprise", "pro_ai", "growth_ai"}
        p = (plan or "").strip().lower()
        return p in allowed or p.endswith("_ai") or "ai" in p

    def _get_cost_delta(
        self,
        org_id: UUID,
        *,
        current: _Period,
        previous: _Period,
        provider: str | None,
    ) -> dict[str, Any]:
        provider_where = "AND provider = {provider:String}" if provider else ""
        params_common: dict[str, Any] = {"org_id": str(org_id)}
        if provider:
            params_common["provider"] = provider

        def _sum(period: _Period) -> float:
            rows = execute_query(
                f"""
                SELECT sum(cost_usd) AS total
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{start:Date}}
                  AND date <= {{end:Date}}
                  {provider_where}
                """,
                {**params_common, "start": period.start, "end": period.end},
            )
            return float(rows[0]["total"]) if rows and rows[0].get("total") is not None else 0.0

        current_total = _sum(current)
        previous_total = _sum(previous)
        delta_usd = current_total - previous_total
        change_pct = round((delta_usd / previous_total) * 100, 2) if previous_total else None

        return {
            "current_total_usd": round(current_total, 2),
            "previous_total_usd": round(previous_total, 2),
            "delta_usd": round(delta_usd, 2),
            "change_pct": change_pct,
        }

    def _get_service_drivers(
        self,
        org_id: UUID,
        *,
        current: _Period,
        previous: _Period,
        provider: str | None,
    ) -> dict[str, Any]:
        provider_where = "AND provider = {provider:String}" if provider else ""
        params: dict[str, Any] = {
            "org_id": str(org_id),
            "c_start": current.start,
            "c_end": current.end,
            "p_start": previous.start,
            "p_end": previous.end,
        }
        if provider:
            params["provider"] = provider

        rows = execute_query(
            f"""
            WITH
              current AS (
                SELECT service, sum(cost_usd) AS cost_usd
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{c_start:Date}}
                  AND date <= {{c_end:Date}}
                  {provider_where}
                GROUP BY service
              ),
              previous AS (
                SELECT service, sum(cost_usd) AS cost_usd
                FROM cost_facts
                WHERE org_id = {{org_id:String}}
                  AND date >= {{p_start:Date}}
                  AND date <= {{p_end:Date}}
                  {provider_where}
                GROUP BY service
              )
            SELECT
              coalesce(c.service, p.service) AS service,
              ifNull(c.cost_usd, 0) AS current_cost_usd,
              ifNull(p.cost_usd, 0) AS previous_cost_usd,
              current_cost_usd - previous_cost_usd AS delta_usd
            FROM current c
            FULL OUTER JOIN previous p ON c.service = p.service
            ORDER BY abs(delta_usd) DESC
            LIMIT 30
            """,
            params,
        )

        drivers = []
        for r in rows:
            svc = str(r.get("service") or "unknown")
            cur = float(r.get("current_cost_usd") or 0.0)
            prev = float(r.get("previous_cost_usd") or 0.0)
            delta = float(r.get("delta_usd") or 0.0)
            pct = round((delta / prev) * 100, 2) if prev else None
            drivers.append(
                {
                    "service": svc,
                    "current_usd": round(cur, 2),
                    "previous_usd": round(prev, 2),
                    "delta_usd": round(delta, 2),
                    "change_pct": pct,
                }
            )

        increases = [d for d in drivers if d["delta_usd"] > 0]
        decreases = [d for d in drivers if d["delta_usd"] < 0]
        increases.sort(key=lambda x: x["delta_usd"], reverse=True)
        decreases.sort(key=lambda x: x["delta_usd"])

        return {
            "top_increases": increases[:8],
            "top_decreases": decreases[:8],
        }

    def _get_events(
        self,
        org_id: UUID,
        *,
        current: _Period,
        provider: str | None,
    ) -> list[dict[str, Any]]:
        provider_where = "AND provider = {provider:String}" if provider else ""
        params: dict[str, Any] = {
            "org_id": str(org_id),
            "start": current.start_dt,
            "end": current.end_dt_exclusive,
        }
        if provider:
            params["provider"] = provider

        rows = execute_query(
            f"""
            SELECT
              timestamp,
              provider,
              event_type,
              severity,
              resource_name,
              description
            FROM event_facts
            WHERE org_id = {{org_id:String}}
              AND timestamp >= {{start:DateTime}}
              AND timestamp < {{end:DateTime}}
              {provider_where}
            ORDER BY timestamp DESC
            LIMIT 50
            """,
            params,
        )
        out = []
        for r in rows:
            out.append(
                {
                    "timestamp": str(r.get("timestamp") or ""),
                    "provider": str(r.get("provider") or ""),
                    "event_type": str(r.get("event_type") or ""),
                    "severity": str(r.get("severity") or ""),
                    "resource_name": str(r.get("resource_name") or ""),
                    "description": str(r.get("description") or ""),
                }
            )
        return out

    def _get_cost_recommendations(
        self,
        org_id: UUID,
        *,
        current: _Period,
        provider: str | None,
    ) -> list[dict[str, Any]]:
        provider_where = "AND provider = {provider:String}" if provider else ""
        params: dict[str, Any] = {"org_id": str(org_id), "start": current.start_dt}
        if provider:
            params["provider"] = provider

        rows = execute_query(
            f"""
            SELECT
              category,
              impact,
              service,
              short_description,
              estimated_savings_usd
            FROM recommendation_facts
            WHERE org_id = {{org_id:String}}
              AND fetched_at >= {{start:DateTime}}
              {provider_where}
              AND (
                positionCaseInsensitiveUTF8(category, 'cost') > 0
                OR positionCaseInsensitiveUTF8(short_description, 'cost') > 0
                OR positionCaseInsensitiveUTF8(short_description, 'reservation') > 0
                OR positionCaseInsensitiveUTF8(short_description, 'savings') > 0
              )
            ORDER BY estimated_savings_usd DESC NULLS LAST
            LIMIT 20
            """,
            params,
        )
        out = []
        for r in rows:
            out.append(
                {
                    "category": str(r.get("category") or ""),
                    "impact": str(r.get("impact") or ""),
                    "service": str(r.get("service") or ""),
                    "short_description": str(r.get("short_description") or ""),
                    "estimated_savings_usd": float(r.get("estimated_savings_usd") or 0.0),
                }
            )
        return out

