from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit_chain.service import AuditChainService
from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OptimizationOpportunity,
    RiskLevel,
)
from app.domains.intel.models import ExecutionPlan
from app.domains.intel.schemas import CreateExecutionPlanRequest, ExecutionPlanOut

_CATEGORY_CHECKLISTS: dict[OpportunityCategory, list[str]] = {
    OpportunityCategory.RIGHTSIZING: [
        "Validar baseline de CPU/memoria e confirmar que o recurso nao atende workload elastico temporario.",
        "Confirmar rollback rapido para SKU anterior em caso de degradacao.",
    ],
    OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING: [
        "Revisar workloads criticos e pods de sistema antes de reduzir nodepool.",
        "Executar mudanca em janela com monitoramento de saturacao e pending pods.",
    ],
    OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION: [
        "Validar limites min/max com time de plataforma e SLO do servico.",
        "Simular impacto de burst para evitar throttling por limite baixo.",
    ],
    OpportunityCategory.IDLE_RESOURCES: [
        "Confirmar recurso sem dependencia ativa antes de desligar/remover.",
        "Validar owner e janela de manutencao para operacao segura.",
    ],
    OpportunityCategory.STORAGE_OPTIMIZATION: [
        "Validar politica de retencao e compliance antes de mover para cold tier.",
        "Executar em lote pequeno e medir latencia/custos por 24h.",
    ],
}


class ExecutionPlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def prepare_plan(
        self,
        *,
        org_id: UUID,
        req: CreateExecutionPlanRequest,
        actor_user_id: UUID | None = None,
    ) -> ExecutionPlanOut:
        selected = await self._fetch_selected(org_id=org_id, ids=req.opportunity_ids)
        if len(selected) != len(req.opportunity_ids):
            found = {op.id for op in selected}
            missing = [str(oid) for oid in req.opportunity_ids if oid not in found]
            raise ValueError(f"Opportunities not found: {', '.join(missing)}")

        total_savings = round(sum(float(op.estimated_monthly_savings_usd or 0.0) for op in selected), 2)
        conflicts = self._detect_conflicts(selected)

        gates_triggered: list[str] = []
        if any(op.risk_level == RiskLevel.HIGH for op in selected):
            gates_triggered.append("high_risk")
        if conflicts:
            gates_triggered.append("aks_conflict_same_nodepool")
        if any(_extract_confidence(op) < 0.60 for op in selected):
            gates_triggered.append("low_confidence")
        if any(float(op.estimated_monthly_savings_usd or 0.0) <= 0.0 for op in selected):
            gates_triggered.append("non_positive_savings")
        if any(not (op.playbook or "").strip() for op in selected):
            gates_triggered.append("missing_playbook")

        status = (
            "blocked"
            if "non_positive_savings" in gates_triggered or "missing_playbook" in gates_triggered
            else "review_required"
        )

        risk_level = _max_risk_level(selected)
        checklist = self._build_checklist(selected=selected, conflicts=conflicts)
        steps = self._build_steps(mode=req.mode, selected=selected, status=status)

        plan = ExecutionPlanOut(
            execution_plan_id=str(uuid4()),
            status=status,
            mode=req.mode,
            total_savings_monthly=total_savings,
            risk_level=risk_level,
            conflicts=conflicts,
            checklist=checklist,
            steps=steps,
            gates_triggered=gates_triggered,
            selected_opportunity_ids=[str(op.id) for op in selected],
        )
        await self._persist_plan(org_id=org_id, actor_user_id=actor_user_id, plan=plan)
        return plan

    async def get_plan(self, *, org_id: UUID, execution_plan_id: UUID) -> ExecutionPlanOut | None:
        result = await self.db.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.org_id == org_id,
                ExecutionPlan.id == execution_plan_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return ExecutionPlanOut.model_validate(row.plan_payload)

    async def _fetch_selected(self, *, org_id: UUID, ids: list[UUID]) -> list[OptimizationOpportunity]:
        result = await self.db.execute(
            select(OptimizationOpportunity).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.id.in_(ids),
            )
        )
        return list(result.scalars().all())

    async def _persist_plan(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID | None,
        plan: ExecutionPlanOut,
    ) -> None:
        row = ExecutionPlan(
            id=UUID(plan.execution_plan_id),
            org_id=org_id,
            mode=plan.mode,
            status=plan.status,
            risk_level=plan.risk_level,
            total_savings_monthly=float(plan.total_savings_monthly),
            selected_opportunity_ids=plan.selected_opportunity_ids,
            gates_triggered=plan.gates_triggered,
            conflicts=plan.conflicts,
            plan_payload=plan.model_dump(),
            created_by_user_id=actor_user_id,
        )
        self.db.add(row)
        await self.db.flush()

        audit_payload = {
            "execution_plan_id": plan.execution_plan_id,
            "selected_opportunity_ids": plan.selected_opportunity_ids,
            "risk_level": plan.risk_level,
            "status": plan.status,
            "total_savings_monthly": plan.total_savings_monthly,
            "gates_triggered": plan.gates_triggered,
            "conflicts": plan.conflicts,
        }
        audit = AuditChainService(self.db)
        await audit.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="execution_plan.created",
            entity_type="execution_plan",
            entity_id=plan.execution_plan_id,
            payload=audit_payload,
        )

    def _detect_conflicts(self, selected: list[OptimizationOpportunity]) -> list[str]:
        by_resource: dict[str, set[OpportunityCategory]] = {}
        for op in selected:
            if op.category not in {
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            }:
                continue
            if not op.resource_id:
                continue
            key = op.resource_id.strip().lower()
            by_resource.setdefault(key, set()).add(op.category)

        conflicts: list[str] = []
        for resource_id, categories in by_resource.items():
            if categories >= {
                OpportunityCategory.AKS_NODEPOOL_RIGHTSIZING,
                OpportunityCategory.AKS_AUTOSCALER_RECOMMENDATION,
            }:
                conflicts.append(
                    f"Conflito em {resource_id}: AKS nodepool rightsizing e autoscaler nao devem ser aplicados simultaneamente sem revisao."
                )
        return conflicts

    def _build_checklist(
        self, *, selected: list[OptimizationOpportunity], conflicts: list[str]
    ) -> list[str]:
        items: list[str] = [
            "Confirmar aprovacao de negocio e owner tecnico antes de qualquer execucao.",
            "Definir janela de mudanca, observabilidade e criterio de rollback.",
        ]
        seen_categories: set[OpportunityCategory] = set()
        for op in selected:
            if op.category in seen_categories:
                continue
            seen_categories.add(op.category)
            items.extend(
                _CATEGORY_CHECKLISTS.get(
                    op.category,
                    ["Validar runbook e riscos da categoria antes da execucao assistida."],
                )
            )
        if conflicts:
            items.append("Executar itens conflitantes em etapas separadas com validacao intermediaria.")
        return items

    def _build_steps(
        self,
        *,
        mode: str,
        selected: list[OptimizationOpportunity],
        status: str,
    ) -> list[str]:
        ranked = sorted(
            selected,
            key=lambda item: (float(item.estimated_monthly_savings_usd or 0.0), item.composite_score),
            reverse=True,
        )
        top = ranked[:3]
        top_names = ", ".join(op.title for op in top) if top else "sem itens"
        steps = [
            f"Priorizar revisao iniciando por: {top_names}.",
            f"Aplicar checklist deterministico e registrar evidencias de risco ({status}).",
        ]
        if mode == "manual_review":
            steps.append("Gerar handoff para execucao manual assistida, sem automacao de mudanca.")
        else:
            steps.append("Gerar handoff para PulseLab como experimento controlado, sem execucao automatica.")
        return steps


def _max_risk_level(selected: list[OptimizationOpportunity]) -> str:
    if any(op.risk_level == RiskLevel.HIGH for op in selected):
        return "high"
    if any(op.risk_level == RiskLevel.MEDIUM for op in selected):
        return "medium"
    return "low"


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
