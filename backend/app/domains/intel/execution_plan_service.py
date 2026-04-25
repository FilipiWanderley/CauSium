from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit_chain.service import AuditChainService
from app.domains.decision_engine.confidence_calibration_service import ConfidenceCalibrationService
from app.domains.decision_engine.models import (
    EffortLevel,
    OpportunityCategory,
    OptimizationOpportunity,
    RiskLevel,
)
from app.domains.experiments.schemas import ExperimentCreate
from app.domains.experiments.models import ExperimentOutcome, ExperimentStatus, OptimizationExperiment
from app.domains.experiments.service import ExperimentService
from app.domains.intel.models import ExecutionPlan
from app.domains.intel.schemas import (
    CreateExecutionPlanRequest,
    ExecutionPlanExecutionStatusOut,
    ExecutionPlanListItemOut,
    ExecutionPlanOut,
)

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


class ExecutionPlanNotFoundError(ValueError):
    pass


class InvalidExecutionPlanTransitionError(ValueError):
    pass


_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "review_required": {"approved", "rejected"},
    "blocked": {"rejected"},
    "approved": set(),
    "rejected": set(),
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

    async def list_plans(
        self,
        *,
        org_id: UUID,
        status: str | None = None,
        risk_level: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExecutionPlanListItemOut], int]:
        filters = [ExecutionPlan.org_id == org_id]
        if status:
            filters.append(ExecutionPlan.status == status)
        if risk_level:
            filters.append(ExecutionPlan.risk_level == risk_level)
        if created_from:
            filters.append(ExecutionPlan.created_at >= created_from)
        if created_to:
            filters.append(ExecutionPlan.created_at <= created_to)

        count_result = await self.db.execute(select(func.count()).select_from(ExecutionPlan).where(*filters))
        total = int(count_result.scalar_one() or 0)

        result = await self.db.execute(
            select(ExecutionPlan)
            .where(*filters)
            .order_by(ExecutionPlan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list(result.scalars().all())
        items = [
            ExecutionPlanListItemOut(
                execution_plan_id=str(row.id),
                status=row.status,
                risk_level=row.risk_level,
                total_savings_monthly=float(row.total_savings_monthly or 0.0),
                gates_triggered=list(row.gates_triggered or []),
                selected_opportunity_ids=list(row.selected_opportunity_ids or []),
                pulselab_experiment_id=_extract_pulselab_experiment_id(row.plan_payload),
                experiment_status=_extract_experiment_status(row.plan_payload),
                execution_outcome=_extract_execution_outcome(row.plan_payload),
                actual_savings=_extract_actual_savings(row.plan_payload),
                created_at=row.created_at,
            )
            for row in rows
        ]
        return items, total

    async def update_plan_status(
        self,
        *,
        org_id: UUID,
        execution_plan_id: UUID,
        new_status: str,
        actor_user_id: UUID,
        comment: str | None = None,
    ) -> ExecutionPlanOut:
        result = await self.db.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.org_id == org_id,
                ExecutionPlan.id == execution_plan_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ExecutionPlanNotFoundError("Execution plan not found")

        previous_status = row.status
        allowed_targets = _ALLOWED_STATUS_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed_targets:
            raise InvalidExecutionPlanTransitionError(
                f"Invalid status transition: {previous_status} -> {new_status}"
            )

        row.status = new_status
        updated_payload = dict(row.plan_payload or {})
        updated_payload["status"] = new_status
        if comment:
            review_payload = updated_payload.get("review")
            if not isinstance(review_payload, dict):
                review_payload = {}
            review_payload["comment"] = comment
            review_payload["actor_user_id"] = str(actor_user_id)
            review_payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
            updated_payload["review"] = review_payload
        row.plan_payload = updated_payload
        await self.db.flush()

        audit_event_type = (
            "execution_plan.approved" if new_status == "approved" else "execution_plan.rejected"
        )
        audit_payload = {
            "execution_plan_id": str(row.id),
            "previous_status": previous_status,
            "new_status": new_status,
            "actor_user_id": str(actor_user_id),
            "comment": comment,
            "total_savings_monthly": float(row.total_savings_monthly or 0.0),
            "risk_level": row.risk_level,
            "gates_triggered": list(row.gates_triggered or []),
        }
        audit = AuditChainService(self.db)
        await audit.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type=audit_event_type,
            entity_type="execution_plan",
            entity_id=str(row.id),
            payload=audit_payload,
        )
        return ExecutionPlanOut.model_validate(row.plan_payload)

    async def schedule_plan(
        self,
        *,
        org_id: UUID,
        execution_plan_id: UUID,
        actor_user_id: UUID,
        scheduled_for: datetime,
        maintenance_window: str,
        comment: str | None = None,
    ) -> ExecutionPlanOut:
        result = await self.db.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.org_id == org_id,
                ExecutionPlan.id == execution_plan_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ExecutionPlanNotFoundError("Execution plan not found")

        previous_status = row.status
        if previous_status != "approved":
            raise InvalidExecutionPlanTransitionError(
                f"Invalid schedule transition: {previous_status} -> scheduled"
            )

        row.status = "scheduled"
        updated_payload = dict(row.plan_payload or {})
        scheduled_for_iso = scheduled_for.isoformat()
        updated_payload["status"] = "scheduled"
        updated_payload["scheduled_for"] = scheduled_for_iso
        updated_payload["maintenance_window"] = maintenance_window

        schedule_payload = updated_payload.get("schedule")
        if not isinstance(schedule_payload, dict):
            schedule_payload = {}
        schedule_payload["scheduled_for"] = scheduled_for_iso
        schedule_payload["maintenance_window"] = maintenance_window
        schedule_payload["actor_user_id"] = str(actor_user_id)
        schedule_payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
        if comment:
            schedule_payload["comment"] = comment
        updated_payload["schedule"] = schedule_payload

        row.plan_payload = updated_payload
        await self.db.flush()

        audit_payload = {
            "execution_plan_id": str(row.id),
            "previous_status": previous_status,
            "new_status": "scheduled",
            "actor_user_id": str(actor_user_id),
            "scheduled_for": scheduled_for_iso,
            "maintenance_window": maintenance_window,
            "comment": comment,
            "total_savings_monthly": float(row.total_savings_monthly or 0.0),
            "risk_level": row.risk_level,
            "gates_triggered": list(row.gates_triggered or []),
        }
        audit = AuditChainService(self.db)
        await audit.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="execution_plan.scheduled",
            entity_type="execution_plan",
            entity_id=str(row.id),
            payload=audit_payload,
        )
        return ExecutionPlanOut.model_validate(row.plan_payload)

    async def create_pulselab_handoff(
        self,
        *,
        org_id: UUID,
        execution_plan_id: UUID,
        actor_user_id: UUID,
        target_environment: str = "production",
        target_criticality: str = "medium",
        comment: str | None = None,
    ) -> ExecutionPlanOut:
        result = await self.db.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.org_id == org_id,
                ExecutionPlan.id == execution_plan_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ExecutionPlanNotFoundError("Execution plan not found")

        if row.status not in {"approved", "scheduled"}:
            raise InvalidExecutionPlanTransitionError(
                f"Invalid handoff transition: {row.status} -> pulselab_handoff"
            )

        current_experiment_id = _extract_pulselab_experiment_id(row.plan_payload)
        if current_experiment_id:
            raise InvalidExecutionPlanTransitionError(
                f"Execution plan already handed off to PulseLab: {current_experiment_id}"
            )

        handoff_checklist = self._build_handoff_checklist(row.plan_payload)
        experiment = await self._create_experiment_for_handoff(
            org_id=org_id,
            actor_user_id=actor_user_id,
            row=row,
            target_environment=target_environment,
            target_criticality=target_criticality,
            comment=comment,
        )
        experiment_id = str(experiment.id)

        previous_mode = row.mode
        row.mode = "pulselab_handoff"
        updated_payload = dict(row.plan_payload or {})
        updated_payload["mode"] = "pulselab_handoff"
        updated_payload["pulselab_experiment_id"] = experiment_id
        updated_payload["handoff_checklist"] = handoff_checklist
        handoff_payload = updated_payload.get("handoff")
        if not isinstance(handoff_payload, dict):
            handoff_payload = {}
        handoff_payload["experiment_id"] = experiment_id
        handoff_payload["target_environment"] = target_environment
        handoff_payload["target_criticality"] = target_criticality
        handoff_payload["actor_user_id"] = str(actor_user_id)
        handoff_payload["created_at"] = datetime.utcnow().isoformat() + "Z"
        handoff_payload["checklist"] = handoff_checklist
        if comment:
            handoff_payload["comment"] = comment
        updated_payload["handoff"] = handoff_payload

        row.plan_payload = updated_payload
        await self.db.flush()

        audit_payload = {
            "execution_plan_id": str(row.id),
            "experiment_id": experiment_id,
            "previous_mode": previous_mode,
            "new_mode": "pulselab_handoff",
            "status": row.status,
            "scheduled_for": updated_payload.get("scheduled_for"),
            "maintenance_window": updated_payload.get("maintenance_window"),
            "target_environment": target_environment,
            "target_criticality": target_criticality,
            "final_checklist": handoff_checklist,
            "comment": comment,
            "actor_user_id": str(actor_user_id),
            "total_savings_monthly": float(row.total_savings_monthly or 0.0),
            "risk_level": row.risk_level,
            "gates_triggered": list(row.gates_triggered or []),
        }
        audit = AuditChainService(self.db)
        await audit.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="execution_plan.handoff_created",
            entity_type="execution_plan",
            entity_id=str(row.id),
            payload=audit_payload,
        )
        return ExecutionPlanOut.model_validate(row.plan_payload)

    async def get_execution_status(
        self,
        *,
        org_id: UUID,
        execution_plan_id: UUID,
        actor_user_id: UUID,
    ) -> ExecutionPlanExecutionStatusOut:
        result = await self.db.execute(
            select(ExecutionPlan).where(
                ExecutionPlan.org_id == org_id,
                ExecutionPlan.id == execution_plan_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ExecutionPlanNotFoundError("Execution plan not found")

        experiment_id_raw = _extract_pulselab_experiment_id(row.plan_payload)
        if not experiment_id_raw:
            raise InvalidExecutionPlanTransitionError("Execution plan has no PulseLab experiment handoff")
        try:
            experiment_id = UUID(experiment_id_raw)
        except ValueError as exc:
            raise InvalidExecutionPlanTransitionError("Execution plan has invalid PulseLab experiment id") from exc

        experiment_service = ExperimentService(self.db)
        experiment = await experiment_service.get(org_id=org_id, experiment_id=experiment_id)
        if not experiment:
            raise ExecutionPlanNotFoundError("PulseLab experiment not found for this execution plan")
        return await self._sync_execution_tracking(
            org_id=org_id,
            actor_user_id=actor_user_id,
            row=row,
            experiment=experiment,
        )

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

    def _build_handoff_checklist(self, plan_payload: dict | None) -> list[str]:
        payload = plan_payload or {}
        base = payload.get("checklist")
        checklist = [item for item in base if isinstance(item, str)] if isinstance(base, list) else []
        if payload.get("status") != "scheduled":
            checklist.append("Recomenda-se agendar janela de manutencao antes de iniciar qualquer experimento.")
        else:
            checklist.append("Confirmar que a janela agendada continua valida com os owners responsaveis.")
        checklist.extend(
            [
                "Registrar experimento PulseLab com escopo controlado e rollback explicito.",
                "Garantir monitoramento ativo de custo, performance e erro durante o experimento.",
                "Nao executar mudanca direta em cloud sem etapa assistida no PulseLab.",
            ]
        )
        return checklist

    async def _create_experiment_for_handoff(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID,
        row: ExecutionPlan,
        target_environment: str,
        target_criticality: str,
        comment: str | None,
    ):
        opportunity_id: UUID | None = None
        selected_ids = row.selected_opportunity_ids or []
        if selected_ids:
            try:
                opportunity_id = UUID(str(selected_ids[0]))
            except Exception:
                opportunity_id = None

        req = ExperimentCreate(
            title=f"PulseLab handoff for execution plan {row.id}",
            hypothesis="Mudanca controlada pode capturar savings com risco operacional limitado.",
            description=(
                "Handoff gerado a partir de execution plan aprovado/agendado. "
                "Sem execucao automatica em cloud."
            ),
            opportunity_id=opportunity_id,
            target_environment=target_environment,
            target_criticality=target_criticality,
            causal_change_event_ids=[str(row.id)],
        )
        experiment_service = ExperimentService(self.db)
        return await experiment_service.create(org_id=org_id, owner_id=actor_user_id, req=req)

    async def _infer_primary_category(
        self,
        *,
        org_id: UUID,
        row: ExecutionPlan,
    ) -> OpportunityCategory | None:
        selected_ids = row.selected_opportunity_ids or []
        uuids: list[UUID] = []
        for raw in selected_ids:
            try:
                uuids.append(UUID(str(raw)))
            except Exception:
                continue
        if not uuids:
            return None
        result = await self.db.execute(
            select(OptimizationOpportunity.category).where(
                OptimizationOpportunity.org_id == org_id,
                OptimizationOpportunity.id.in_(uuids),
            )
        )
        categories = [value for value in result.scalars().all() if isinstance(value, OpportunityCategory)]
        if not categories:
            return None
        counts: dict[OpportunityCategory, int] = {}
        for category in categories:
            counts[category] = counts.get(category, 0) + 1
        return max(counts.items(), key=lambda item: item[1])[0]

    async def _sync_execution_tracking(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID,
        row: ExecutionPlan,
        experiment: OptimizationExperiment,
    ) -> ExecutionPlanExecutionStatusOut:
        derived_status, derived_outcome = _derive_execution_state(
            experiment_status=experiment.status,
            experiment_outcome=experiment.outcome,
        )
        actual_savings = round(float(experiment.actual_savings_usd or 0.0), 2)
        expected_savings = round(float(row.total_savings_monthly or 0.0), 2)
        delta = round(actual_savings - expected_savings, 2)

        previous_status = _extract_experiment_status(row.plan_payload)
        payload = dict(row.plan_payload or {})
        payload["experiment_status"] = derived_status
        payload["execution_outcome"] = derived_outcome
        payload["actual_savings"] = actual_savings
        payload["experiment_result"] = {
            "experiment_status": experiment.status.value,
            "experiment_outcome": experiment.outcome.value if experiment.outcome else None,
            "actual_savings_usd": actual_savings,
            "actual_confidence": (
                round(float(experiment.actual_confidence), 4)
                if experiment.actual_confidence is not None
                else None
            ),
            "started_at": _to_iso_or_none(experiment.started_at),
            "concluded_at": _to_iso_or_none(experiment.concluded_at),
            "updated_at": _to_iso_or_none(experiment.updated_at),
        }
        tracking_payload = payload.get("execution_tracking")
        if not isinstance(tracking_payload, dict):
            tracking_payload = {}
        tracking_payload["last_synced_at"] = datetime.utcnow().isoformat() + "Z"
        tracking_payload["experiment_status_raw"] = experiment.status.value
        tracking_payload["experiment_outcome_raw"] = experiment.outcome.value if experiment.outcome else None
        payload["execution_tracking"] = tracking_payload
        row.plan_payload = payload
        await self.db.flush()

        if previous_status != derived_status:
            audit_event_type = {
                "running": "execution_plan.execution_started",
                "completed": "execution_plan.execution_completed",
                "failed": "execution_plan.execution_failed",
            }[derived_status]
            audit = AuditChainService(self.db)
            await audit.append_event(
                org_id=org_id,
                actor_user_id=actor_user_id,
                event_type=audit_event_type,
                entity_type="execution_plan",
                entity_id=str(row.id),
                payload={
                    "execution_plan_id": str(row.id),
                    "experiment_id": str(experiment.id),
                    "previous_status": previous_status,
                    "new_status": derived_status,
                    "outcome": derived_outcome,
                    "actual_savings": actual_savings,
                    "expected_savings": expected_savings,
                    "delta": delta,
                },
            )
            if derived_status in {"completed", "failed"}:
                category = await self._infer_primary_category(org_id=org_id, row=row)
                if category is not None:
                    calibration = await ConfidenceCalibrationService(self.db).record_category_result(
                        org_id=org_id,
                        category=category,
                        expected_savings=expected_savings,
                        actual_savings=actual_savings,
                    )
                    tracking_payload = payload.get("execution_tracking")
                    if not isinstance(tracking_payload, dict):
                        tracking_payload = {}
                    tracking_payload["calibration"] = {
                        "dimension_type": "category",
                        "dimension_key": category.value,
                        "historical_accuracy": calibration.historical_accuracy,
                        "confidence_adjustment": calibration.confidence_adjustment,
                        "total_executions": calibration.total_executions,
                    }
                    payload["execution_tracking"] = tracking_payload
                    row.plan_payload = payload
                    await self.db.flush()

        return ExecutionPlanExecutionStatusOut(
            execution_plan_id=str(row.id),
            experiment_id=str(experiment.id),
            status=derived_status,
            actual_savings=actual_savings,
            expected_savings=expected_savings,
            delta=delta,
            outcome=derived_outcome,
        )


def _extract_pulselab_experiment_id(plan_payload: dict | None) -> str | None:
    payload = plan_payload or {}
    value = payload.get("pulselab_experiment_id")
    if isinstance(value, str) and value.strip():
        return value
    handoff = payload.get("handoff")
    if isinstance(handoff, dict):
        nested = handoff.get("experiment_id")
        if isinstance(nested, str) and nested.strip():
            return nested
    return None


def _extract_experiment_status(plan_payload: dict | None) -> str | None:
    payload = plan_payload or {}
    value = payload.get("experiment_status")
    if isinstance(value, str) and value in {"running", "completed", "failed"}:
        return value
    return None


def _extract_execution_outcome(plan_payload: dict | None) -> str | None:
    payload = plan_payload or {}
    value = payload.get("execution_outcome")
    if isinstance(value, str) and value in {"success", "partial", "failed"}:
        return value
    return None


def _extract_actual_savings(plan_payload: dict | None) -> float | None:
    payload = plan_payload or {}
    raw = payload.get("actual_savings")
    try:
        if raw is None:
            return None
        return float(raw)
    except (TypeError, ValueError):
        return None


def _derive_execution_state(
    *,
    experiment_status: ExperimentStatus,
    experiment_outcome: ExperimentOutcome | None,
) -> tuple[str, str]:
    if experiment_status in {ExperimentStatus.CANCELLED}:
        return "failed", "failed"
    if experiment_status == ExperimentStatus.CONCLUDED:
        if experiment_outcome == ExperimentOutcome.IMPROVED:
            return "completed", "success"
        if experiment_outcome == ExperimentOutcome.INCONCLUSIVE:
            return "completed", "partial"
        return "failed", "failed"
    return "running", "partial"


def _to_iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
