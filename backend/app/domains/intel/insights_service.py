from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clickhouse import execute_query
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.auth.models import Organization
from app.domains.decision_engine.models import (
    OptimizationOpportunity,
    OpportunityStatus,
    RiskLevel,
)
from app.domains.intel.llm_service import LlmService
from app.domains.intel.models import CostAnomaly, CostAnomalySeverity
from app.domains.intel.schemas import IntelInsightsOut

log = get_logger(__name__)


@dataclass(frozen=True)
class _RuleInsights:
    top_saving_opportunity: str
    main_risk: str
    cost_trend_summary: str
    recommended_action: str
    confidence: float


class IntelInsightsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.llm = LlmService()

    async def get_insights(
        self,
        *,
        org_id: UUID,
        language: str = "en",
    ) -> IntelInsightsOut:
        await self._require_ai_feature(org_id)
        lang = "pt" if str(language).lower().startswith("pt") else "en"

        trend = self._build_cost_trend(org_id, language=lang)
        opportunity = await self._get_top_saving_opportunity(org_id, language=lang)
        risk = await self._get_main_risk(org_id, language=lang)
        rule = self._compose_rule_insights(trend=trend, opportunity=opportunity, risk=risk, language=lang)

        context = {
            "language": lang,
            "workspace": {"org_id": str(org_id), "plan": (await self._get_org_plan(org_id))},
            "signals": {
                "top_saving_opportunity": opportunity,
                "main_risk": risk,
                "cost_trend": trend,
            },
            "fallback": {
                "top_saving_opportunity": rule.top_saving_opportunity,
                "main_risk": rule.main_risk,
                "cost_trend_summary": rule.cost_trend_summary,
                "recommended_action": rule.recommended_action,
                "confidence": rule.confidence,
            },
        }

        try:
            out = await self.llm.generate_insights(context)
            if out.confidence < rule.confidence:
                out.confidence = rule.confidence
            return out
        except Exception as exc:
            log.warning("intel.insights.llm_failed", org_id=str(org_id), error=str(exc))
            return IntelInsightsOut(
                top_saving_opportunity=rule.top_saving_opportunity,
                main_risk=rule.main_risk,
                cost_trend_summary=rule.cost_trend_summary,
                recommended_action=rule.recommended_action,
                confidence=rule.confidence,
                model="rules",
                debug={"llm_error": str(exc)},
            )

    async def _get_top_saving_opportunity(self, org_id: UUID, *, language: str) -> dict[str, Any] | None:
        result = await self.db.execute(
            select(OptimizationOpportunity)
            .where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status.in_([OpportunityStatus.OPEN, OpportunityStatus.IN_PROGRESS]),
            )
            .order_by(
                OptimizationOpportunity.estimated_monthly_savings_usd.desc(),
                OptimizationOpportunity.composite_score.desc(),
            )
            .limit(1)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None

        service = item.service or item.resource_name or "unknown service"
        if language == "pt":
            text = (
                f"Maior oportunidade em {service}: economia estimada de "
                f"${item.estimated_monthly_savings_usd:,.2f}/mes com risco {item.risk_level.value}."
            )
        else:
            text = (
                f"Top opportunity in {service}: estimated savings of "
                f"${item.estimated_monthly_savings_usd:,.2f}/month with {item.risk_level.value} risk."
            )
        return {
            "text": text,
            "service": service,
            "estimated_monthly_savings_usd": item.estimated_monthly_savings_usd,
            "risk_level": item.risk_level.value,
            "effort_level": item.effort_level.value,
            "category": item.category.value,
            "status": item.status.value,
        }

    async def _get_main_risk(self, org_id: UUID, *, language: str) -> dict[str, Any] | None:
        severity_rank = {
            CostAnomalySeverity.HIGH: 3,
            CostAnomalySeverity.MEDIUM: 2,
            CostAnomalySeverity.LOW: 1,
        }
        rows = await self.db.execute(
            select(CostAnomaly)
            .where(CostAnomaly.org_id == org_id)
            .order_by(CostAnomaly.observed_date.desc(), CostAnomaly.z_score.desc())
            .limit(20)
        )
        items = list(rows.scalars().all())
        if not items:
            return None

        best = max(items, key=lambda x: (severity_rank[x.severity], x.z_score))
        if language == "pt":
            text = (
                f"Risco principal: anomalia no servico {best.service} "
                f"({best.provider.upper()}) com z-score {best.z_score:.2f}."
            )
        else:
            text = (
                f"Main risk: anomaly in {best.service} "
                f"({best.provider.upper()}) with z-score {best.z_score:.2f}."
            )
        return {
            "text": text,
            "service": best.service,
            "provider": best.provider,
            "severity": best.severity.value,
            "z_score": best.z_score,
            "deviation_pct": best.deviation_pct,
            "observed_date": best.observed_date.isoformat(),
        }

    def _build_cost_trend(self, org_id: UUID, *, language: str) -> dict[str, Any]:
        today = date.today()
        current_start = today - timedelta(days=6)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=6)

        current_total = self._sum_cost(org_id, current_start, today)
        previous_total = self._sum_cost(org_id, previous_start, previous_end)
        delta = current_total - previous_total
        pct = ((delta / previous_total) * 100.0) if previous_total > 0 else None

        if language == "pt":
            if pct is None:
                text = "Tendencia de custo sem base historica suficiente para comparacao percentual."
            else:
                direction = "aumento" if delta >= 0 else "reducao"
                text = (
                    f"Custo dos ultimos 7 dias: ${current_total:,.2f}, "
                    f"{direction} de {abs(pct):.1f}% vs 7 dias anteriores."
                )
        else:
            if pct is None:
                text = "Cost trend has insufficient historical baseline for percentage comparison."
            else:
                direction = "increase" if delta >= 0 else "decrease"
                text = (
                    f"Last 7-day cost: ${current_total:,.2f}, "
                    f"{direction} of {abs(pct):.1f}% vs previous 7 days."
                )

        return {
            "text": text,
            "current_7d_total_usd": round(current_total, 2),
            "previous_7d_total_usd": round(previous_total, 2),
            "delta_usd": round(delta, 2),
            "change_pct": round(pct, 2) if pct is not None else None,
        }

    def _sum_cost(self, org_id: UUID, start: date, end: date) -> float:
        rows = execute_query(
            """
            SELECT sum(cost_usd) AS total
            FROM cost_facts
            WHERE org_id = {org_id:String}
              AND date >= {start:Date}
              AND date <= {end:Date}
            """,
            {"org_id": str(org_id), "start": start, "end": end},
        )
        return float(rows[0]["total"]) if rows and rows[0].get("total") is not None else 0.0

    def _compose_rule_insights(
        self,
        *,
        trend: dict[str, Any],
        opportunity: dict[str, Any] | None,
        risk: dict[str, Any] | None,
        language: str,
    ) -> _RuleInsights:
        if opportunity is not None:
            top_saving = str(opportunity["text"])
        else:
            top_saving = (
                "Nenhuma oportunidade de economia relevante disponivel no momento."
                if language == "pt"
                else "No significant saving opportunity available right now."
            )

        if risk is not None:
            main_risk = str(risk["text"])
        else:
            main_risk = (
                "Nenhuma anomalia critica de custo detectada no periodo recente."
                if language == "pt"
                else "No critical cost anomaly detected in the recent period."
            )

        recommended_action = self._build_recommended_action(opportunity, risk, trend, language=language)
        confidence = self._confidence_score(opportunity=opportunity, risk=risk, trend=trend)

        return _RuleInsights(
            top_saving_opportunity=top_saving,
            main_risk=main_risk,
            cost_trend_summary=str(trend["text"]),
            recommended_action=recommended_action,
            confidence=confidence,
        )

    def _build_recommended_action(
        self,
        opportunity: dict[str, Any] | None,
        risk: dict[str, Any] | None,
        trend: dict[str, Any],
        *,
        language: str,
    ) -> str:
        trend_up = (trend.get("delta_usd") or 0.0) > 0
        if risk is not None and risk.get("severity") == "high":
            service = risk.get("service") or "unknown service"
            if language == "pt":
                return (
                    f"Priorize agora a investigacao de anomalia em {service}, "
                    "validando deploys recentes e politicas de autoscaling antes de otimizar novos custos."
                )
            return (
                f"Prioritize immediate anomaly investigation in {service}, "
                "validating recent deployments and autoscaling policies before new optimizations."
            )

        if opportunity is not None:
            service = opportunity.get("service") or "unknown service"
            risk_level = (opportunity.get("risk_level") or RiskLevel.MEDIUM.value).lower()
            if language == "pt":
                return (
                    f"Execute primeiro a oportunidade de maior economia em {service} "
                    f"(risco {risk_level}) e monitore impacto por 7 dias."
                )
            return (
                f"Execute the top saving opportunity in {service} first "
                f"({risk_level} risk) and monitor impact for 7 days."
            )

        if language == "pt":
            return (
                "Sem oportunidade clara agora; mantenha monitoramento diario de custo e "
                "revise variacoes por servico para criar a proxima acao de economia."
            )
        return (
            "No clear opportunity now; keep daily cost monitoring and "
            "review service-level shifts to define the next saving action."
        )

    def _confidence_score(
        self,
        *,
        opportunity: dict[str, Any] | None,
        risk: dict[str, Any] | None,
        trend: dict[str, Any],
    ) -> float:
        score = 0.4
        if trend.get("current_7d_total_usd", 0.0) > 0:
            score += 0.15
        if trend.get("previous_7d_total_usd", 0.0) > 0:
            score += 0.1
        if opportunity is not None:
            score += 0.2
        if risk is not None:
            score += 0.15
        return round(min(score, 0.95), 2)

    async def _require_ai_feature(self, org_id: UUID) -> None:
        plan = await self._get_org_plan(org_id)
        if not self._plan_has_ai(plan):
            raise PermissionError("AI feature not enabled for this workspace plan")

    async def _get_org_plan(self, org_id: UUID) -> str:
        result = await self.db.execute(select(Organization.plan).where(Organization.id == org_id))
        plan = result.scalar_one_or_none()
        return str(plan or "unknown")

    def _plan_has_ai(self, plan: str) -> bool:
        # In local/dev environments we keep AI routes available for demos and
        # end-to-end validation, while production remains plan-gated.
        if not self.settings.is_production:
            return True
        allowed = {p.strip().lower() for p in (self.settings.ai_enabled_plans or "").split(",") if p.strip()}
        if not allowed:
            allowed = {"b", "plan_b", "ai", "enterprise", "pro_ai", "growth_ai"}
        p = (plan or "").strip().lower()
        return p in allowed or p.endswith("_ai") or "ai" in p
