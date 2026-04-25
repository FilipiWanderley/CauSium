from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OpportunityStatus,
    OptimizationOpportunity,
    RiskLevel,
)
from app.domains.decision_engine.confidence_calibration_service import ConfidenceCalibrationService
from app.domains.decision_engine.schemas import (
    OptimizationPlanGroup,
    OptimizationPlanOut,
    OptimizationPlanRecommendation,
)
from app.domains.intel.llm_service import LlmService

_RISK_SCORE = {
    RiskLevel.LOW: 1.0,
    RiskLevel.MEDIUM: 0.6,
    RiskLevel.HIGH: 0.2,
}
_EFFORT_SCORE = {
    EffortLevel.LOW: 1.0,
    EffortLevel.MEDIUM: 0.6,
    EffortLevel.HIGH: 0.2,
}
_CATEGORY_LABELS = {
    OpportunityCategory.RIGHTSIZING: "VM Rightsizing",
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: "AKS Node Pool Rightsizing",
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: "AKS Autoscaler",
    OpportunityCategory.IDLE_RESOURCES: "Idle Resources",
    OpportunityCategory.RESERVED_INSTANCES: "Reserved Instances",
    OpportunityCategory.STORAGE_OPTIMIZATION: "Storage Optimization",
    OpportunityCategory.NETWORK_OPTIMIZATION: "Network Optimization",
    OpportunityCategory.LICENSE_OPTIMIZATION: "License Optimization",
    OpportunityCategory.ARCHITECTURE_CHANGE: "Architecture Change",
}


@dataclass(frozen=True)
class _ScoreBreakdown:
    normalized_savings: float
    confidence: float
    base_confidence: float
    confidence_adjustment: float
    historical_accuracy: float | None
    risk_score: float
    effort_score: float
    priority_score: float


class OptimizationPlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = LlmService()

    async def build_plan(
        self,
        *,
        org_id: UUID,
        language: str = "pt",
        include_ai_summary: bool = False,
    ) -> OptimizationPlanOut:
        opportunities = await self._list_open_opportunities(org_id=org_id)
        if not opportunities:
            return OptimizationPlanOut(
                total_recommendations=0,
                total_savings_monthly_raw_usd=0.0,
                total_savings_monthly_adjusted_usd=0.0,
                total_savings_annual_adjusted_usd=0.0,
                confidence_global=0.0,
                summary=(
                    "Nenhuma oportunidade aberta para montar plano de otimização."
                    if language == "pt"
                    else "No open opportunities available to build an optimization plan."
                ),
                summary_source="deterministic",
                quick_wins=[],
                prioritized=[],
                groups=[],
                conflict_hints=[],
            )

        max_savings = max(float(op.estimated_monthly_savings_usd or 0.0) for op in opportunities) or 1.0
        category_calibration = await ConfidenceCalibrationService(self.db).get_category_snapshots(
            org_id=org_id,
            categories={op.category for op in opportunities},
        )
        recommendations: list[OptimizationPlanRecommendation] = []
        for op in opportunities:
            score = self._compute_priority_score(
                op=op,
                max_savings=max_savings,
                category_calibration=category_calibration,
            )
            confidence = score.confidence
            why_now = self._build_why_now(op=op, score=score)
            next_step = self._build_next_step(op=op)
            recommendations.append(
                OptimizationPlanRecommendation(
                    opportunity_id=op.id,
                    category=op.category,
                    title=op.title,
                    resource_id=op.resource_id,
                    resource_name=op.resource_name,
                    service=op.service,
                    environment=op.environment,
                    owner_team=op.owner_team,
                    estimated_monthly_savings_usd=round(float(op.estimated_monthly_savings_usd or 0.0), 2),
                    confidence=round(confidence, 4),
                    base_confidence=round(score.base_confidence, 4),
                    confidence_adjustment=round(score.confidence_adjustment, 4),
                    historical_accuracy=(
                        round(score.historical_accuracy, 4)
                        if score.historical_accuracy is not None
                        else None
                    ),
                    risk_level=op.risk_level,
                    effort_level=op.effort_level,
                    priority_score=round(score.priority_score, 4),
                    rank=0,
                    why_now=why_now,
                    next_step=next_step,
                    conflict_hints=[],
                    conflicting_with_opportunity_ids=[],
                )
            )

        prioritized = sorted(
            recommendations,
            key=lambda r: (r.priority_score, r.estimated_monthly_savings_usd, r.confidence),
            reverse=True,
        )
        for idx, rec in enumerate(prioritized, start=1):
            rec.rank = idx

        conflict_hints = self._apply_conflict_hints(prioritized)
        total_raw = round(sum(r.estimated_monthly_savings_usd for r in prioritized), 2)
        total_adjusted = round(self._compute_adjusted_savings(prioritized), 2)
        confidence_global = round(self._compute_global_confidence(prioritized), 4)
        quick_wins = [
            rec
            for rec in prioritized
            if rec.risk_level == RiskLevel.LOW
            and rec.effort_level == EffortLevel.LOW
            and rec.estimated_monthly_savings_usd > 0
            and rec.confidence >= 0.75
        ][:5]
        groups = self._build_groups(prioritized)
        deterministic_summary = self._build_deterministic_summary(
            prioritized=prioritized,
            total_adjusted=total_adjusted,
            quick_wins=quick_wins,
            conflict_hints=conflict_hints,
            language=language,
        )

        summary = deterministic_summary
        summary_source = "deterministic"
        ai_summary: str | None = None
        ai_model: str | None = None
        if include_ai_summary:
            ai_summary, ai_model = await self._build_ai_summary(
                deterministic_summary=deterministic_summary,
                prioritized=prioritized,
                total_adjusted=total_adjusted,
                language=language,
            )
            if ai_summary:
                summary = ai_summary
                summary_source = "ai"

        return OptimizationPlanOut(
            total_recommendations=len(prioritized),
            total_savings_monthly_raw_usd=total_raw,
            total_savings_monthly_adjusted_usd=total_adjusted,
            total_savings_annual_adjusted_usd=round(total_adjusted * 12, 2),
            confidence_global=confidence_global,
            summary=summary,
            summary_source=summary_source,
            ai_summary=ai_summary,
            ai_model=ai_model,
            quick_wins=quick_wins,
            prioritized=prioritized,
            groups=groups,
            conflict_hints=conflict_hints,
        )

    async def _list_open_opportunities(self, *, org_id: UUID) -> list[OptimizationOpportunity]:
        result = await self.db.execute(
            select(OptimizationOpportunity).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.status == OpportunityStatus.OPEN,
            )
        )
        return list(result.scalars().all())

    def _compute_priority_score(
        self,
        *,
        op: OptimizationOpportunity,
        max_savings: float,
        category_calibration,
    ) -> _ScoreBreakdown:
        savings = float(op.estimated_monthly_savings_usd or 0.0)
        normalized_savings = max(0.0, min(1.0, savings / max_savings))
        base_confidence = _extract_confidence(op)
        snapshot = category_calibration.get(op.category)
        confidence_adjustment = float(snapshot.confidence_adjustment) if snapshot else 0.0
        confidence = max(0.0, min(1.0, base_confidence + confidence_adjustment))
        risk_score = _RISK_SCORE.get(op.risk_level, 0.6)
        effort_score = _EFFORT_SCORE.get(op.effort_level, 0.6)
        priority_score = (
            normalized_savings * 0.45
            + confidence * 0.30
            + risk_score * 0.15
            + effort_score * 0.10
        )
        return _ScoreBreakdown(
            normalized_savings=normalized_savings,
            confidence=confidence,
            base_confidence=base_confidence,
            confidence_adjustment=confidence_adjustment,
            historical_accuracy=(float(snapshot.historical_accuracy) if snapshot else None),
            risk_score=risk_score,
            effort_score=effort_score,
            priority_score=priority_score,
        )

    def _build_why_now(self, *, op: OptimizationOpportunity, score: _ScoreBreakdown) -> str:
        calibration = (
            f", base_confidence={score.base_confidence:.2f}, "
            f"adjustment={score.confidence_adjustment:.2f}, "
            f"historical_accuracy={score.historical_accuracy:.2f}"
            if score.historical_accuracy is not None
            else ""
        )
        return (
            f"Savings norm={score.normalized_savings:.2f}, "
            f"confidence={score.confidence:.2f}, "
            f"risk_score={score.risk_score:.2f}, "
            f"effort_score={score.effort_score:.2f}{calibration}."
        )

    def _build_next_step(self, *, op: OptimizationOpportunity) -> str:
        if op.playbook:
            first_line = str(op.playbook).splitlines()[0].strip()
            if first_line:
                return first_line
        return (
            "Abrir execução controlada com validação de impacto."
            if op.environment == "production"
            else "Aplicar em janela controlada e monitorar por 24h."
        )

    def _apply_conflict_hints(self, prioritized: list[OptimizationPlanRecommendation]) -> list[str]:
        by_resource: dict[str, list[OptimizationPlanRecommendation]] = {}
        for rec in prioritized:
            if rec.category not in {
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            }:
                continue
            if not rec.resource_id:
                continue
            key = rec.resource_id.strip().lower()
            by_resource.setdefault(key, []).append(rec)

        hints: list[str] = []
        for resource, recs in by_resource.items():
            has_rightsizing = any(
                rec.category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING for rec in recs
            )
            has_autoscaler = any(
                rec.category == OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION for rec in recs
            )
            if not (has_rightsizing and has_autoscaler):
                continue
            hint = (
                f"Conflito potencial em {resource}: AKS nodepool rightsizing e autoscaler podem coexistir, "
                "mas nao devem ser aplicados simultaneamente sem revisao."
            )
            hints.append(hint)
            ids = [rec.opportunity_id for rec in recs]
            for rec in recs:
                rec.conflict_hints.append(hint)
                rec.conflicting_with_opportunity_ids = [oid for oid in ids if oid != rec.opportunity_id]
        return hints

    def _compute_adjusted_savings(self, recommendations: Iterable[OptimizationPlanRecommendation]) -> float:
        recs = list(recommendations)
        total = sum(r.estimated_monthly_savings_usd for r in recs)
        by_resource: dict[str, list[OptimizationPlanRecommendation]] = {}
        for rec in recs:
            if rec.category not in {
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            }:
                continue
            if not rec.resource_id:
                continue
            key = rec.resource_id.strip().lower()
            by_resource.setdefault(key, []).append(rec)

        for group in by_resource.values():
            if len(group) <= 1:
                continue
            has_rightsizing = any(
                rec.category == OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING for rec in group
            )
            has_autoscaler = any(
                rec.category == OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION for rec in group
            )
            if not (has_rightsizing and has_autoscaler):
                continue
            keep = max(rec.estimated_monthly_savings_usd for rec in group)
            total -= sum(rec.estimated_monthly_savings_usd for rec in group) - keep
        return total

    def _compute_global_confidence(self, recommendations: list[OptimizationPlanRecommendation]) -> float:
        total_savings = sum(rec.estimated_monthly_savings_usd for rec in recommendations)
        if total_savings <= 0:
            return 0.0
        weighted = sum(rec.confidence * rec.estimated_monthly_savings_usd for rec in recommendations)
        return weighted / total_savings

    def _build_groups(
        self, recommendations: list[OptimizationPlanRecommendation]
    ) -> list[OptimizationPlanGroup]:
        groups: dict[OpportunityCategory, list[OptimizationPlanRecommendation]] = {}
        for rec in recommendations:
            groups.setdefault(rec.category, []).append(rec)
        out: list[OptimizationPlanGroup] = []
        for category, recs in groups.items():
            out.append(
                OptimizationPlanGroup(
                    key=category.value,
                    label=_CATEGORY_LABELS.get(category, category.value),
                    total_items=len(recs),
                    total_estimated_monthly_savings_usd=round(
                        sum(i.estimated_monthly_savings_usd for i in recs), 2
                    ),
                    opportunity_ids=[i.opportunity_id for i in recs],
                )
            )
        out.sort(key=lambda g: g.total_estimated_monthly_savings_usd, reverse=True)
        return out

    def _build_deterministic_summary(
        self,
        *,
        prioritized: list[OptimizationPlanRecommendation],
        total_adjusted: float,
        quick_wins: list[OptimizationPlanRecommendation],
        conflict_hints: list[str],
        language: str,
    ) -> str:
        top = prioritized[:2]
        if language == "pt":
            parts = [
                f"Plano priorizado com {len(prioritized)} recomendacoes e economia ajustada estimada de US${total_adjusted:,.2f}/mes.",
                (
                    f"Comece por: 1) {top[0].title}; 2) {top[1].title}."
                    if len(top) > 1
                    else f"Comece por: {top[0].title}."
                ),
            ]
            if quick_wins:
                parts.append(f"Quick wins identificados: {len(quick_wins)}.")
            if conflict_hints:
                parts.append("Ha conflitos potenciais que exigem revisao antes de execucao simultanea.")
            return " ".join(parts)
        parts = [
            f"Prioritized plan with {len(prioritized)} recommendations and adjusted estimated savings of ${total_adjusted:,.2f}/month.",
            (
                f"Start with: 1) {top[0].title}; 2) {top[1].title}."
                if len(top) > 1
                else f"Start with: {top[0].title}."
            ),
        ]
        if quick_wins:
            parts.append(f"Quick wins identified: {len(quick_wins)}.")
        if conflict_hints:
            parts.append("Potential conflicts require review before simultaneous execution.")
        return " ".join(parts)

    async def _build_ai_summary(
        self,
        *,
        deterministic_summary: str,
        prioritized: list[OptimizationPlanRecommendation],
        total_adjusted: float,
        language: str,
    ) -> tuple[str | None, str | None]:
        fallback = {
            "top_saving_opportunity": prioritized[0].title if prioritized else "",
            "main_risk": prioritized[0].risk_level.value if prioritized else "",
            "cost_trend_summary": deterministic_summary,
            "recommended_action": (
                "Execute em ordem de prioridade e valide riscos antes de cada mudanca."
                if language == "pt"
                else "Execute in priority order and validate risks before each change."
            ),
            "confidence": 0.65,
        }
        context = {
            "language": language,
            "task": "Summarize optimization plan ordering and execution cautions.",
            "plan": {
                "total_adjusted_savings_usd": total_adjusted,
                "prioritized": [
                    {
                        "rank": rec.rank,
                        "title": rec.title,
                        "category": rec.category.value,
                        "estimated_monthly_savings_usd": rec.estimated_monthly_savings_usd,
                        "risk_level": rec.risk_level.value,
                        "effort_level": rec.effort_level.value,
                        "priority_score": rec.priority_score,
                    }
                    for rec in prioritized[:6]
                ],
            },
            "fallback": fallback,
        }
        try:
            out = await self.llm.generate_insights(context)
            ai_summary = (
                f"{out.cost_trend_summary} {out.recommended_action}".strip()
                if language == "pt"
                else f"{out.cost_trend_summary} {out.recommended_action}".strip()
            )
            return ai_summary, out.model
        except Exception:
            return None, None


def _extract_confidence(opportunity: OptimizationOpportunity) -> float:
    evidence = opportunity.decision_evidence or {}
    raw = evidence.get("confidence")
    try:
        value = float(raw) if raw is not None else None
    except Exception:
        value = None
    if value is None:
        if opportunity.risk_level == RiskLevel.LOW and opportunity.effort_level == EffortLevel.LOW:
            value = 0.8
        elif opportunity.risk_level == RiskLevel.LOW:
            value = 0.72
        elif opportunity.risk_level == RiskLevel.MEDIUM:
            value = 0.58
        else:
            value = 0.45
    return max(0.0, min(1.0, value))
