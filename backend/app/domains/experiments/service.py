from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.audit_chain.service import AuditChainService
from app.domains.experiments.models import (
    ExperimentOutcome,
    ExperimentApproval,
    ExperimentRun,
    ExperimentStatus,
    OptimizationExperiment,
    RunStatus,
    VALID_EXPERIMENT_TRANSITIONS,
)
from app.domains.experiments.schemas import (
    ExperimentApprovalCreate,
    ExperimentCreate,
    ExperimentSummary,
    ExperimentTransition,
    ExperimentUpdate,
    RunCreate,
    RunUpdate,
)

log = get_logger(__name__)


class ExperimentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_chain = AuditChainService(db)

    # ── Experiments ──────────────────────────────────────────────────────────

    async def create(self, org_id: UUID, owner_id: UUID, req: ExperimentCreate) -> OptimizationExperiment:
        exp = OptimizationExperiment(
            org_id=org_id,
            owner_id=owner_id,
            title=req.title,
            hypothesis=req.hypothesis,
            description=req.description,
            target_environment=req.target_environment,
            target_criticality=req.target_criticality,
            opportunity_id=req.opportunity_id,
            risk_budget_id=req.risk_budget_id,
            guardrails=req.guardrails.model_dump() if req.guardrails else None,
            causal_change_event_ids=req.causal_change_event_ids,
        )
        self.db.add(exp)
        await self.db.flush()
        await self.db.refresh(exp)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=owner_id,
            event_type="experiment.created",
            entity_type="optimization_experiment",
            entity_id=str(exp.id),
            payload={
                "title": exp.title,
                "opportunity_id": str(exp.opportunity_id) if exp.opportunity_id else None,
                "risk_budget_id": str(exp.risk_budget_id) if exp.risk_budget_id else None,
                "target_environment": exp.target_environment,
                "target_criticality": exp.target_criticality,
                "guardrails": exp.guardrails or {},
            },
        )
        log.info("experiment.created", experiment_id=str(exp.id), org_id=str(org_id))
        return exp

    async def get(self, org_id: UUID, experiment_id: UUID) -> Optional[OptimizationExperiment]:
        result = await self.db.execute(
            select(OptimizationExperiment).where(
                OptimizationExperiment.id == experiment_id,
                OptimizationExperiment.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        org_id: UUID,
        status: Optional[ExperimentStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[OptimizationExperiment], int]:
        filters = [OptimizationExperiment.org_id == org_id]
        if status:
            filters.append(OptimizationExperiment.status == status)

        count_result = await self.db.execute(
            select(func.count()).select_from(OptimizationExperiment).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(OptimizationExperiment)
            .where(*filters)
            .order_by(OptimizationExperiment.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def update(
        self, org_id: UUID, experiment_id: UUID, req: ExperimentUpdate
    ) -> Optional[OptimizationExperiment]:
        exp = await self.get(org_id, experiment_id)
        if not exp:
            return None
        for field, value in req.model_dump(exclude_none=True).items():
            setattr(exp, field, value)
        await self.db.flush()
        await self.db.refresh(exp)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=exp.owner_id,
            event_type="experiment.updated",
            entity_type="optimization_experiment",
            entity_id=str(exp.id),
            payload=req.model_dump(exclude_none=True),
        )
        return exp

    async def transition(
        self, org_id: UUID, experiment_id: UUID, req: ExperimentTransition, approver_id: Optional[UUID] = None
    ) -> OptimizationExperiment:
        exp = await self.get(org_id, experiment_id)
        if not exp:
            raise ValueError("Experiment not found")

        allowed = VALID_EXPERIMENT_TRANSITIONS.get(exp.status, [])
        if req.status not in allowed:
            raise ValueError(
                f"Cannot transition from {exp.status.value} to {req.status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        exp.status = req.status

        if req.status == ExperimentStatus.RUNNING:
            exp.started_at = datetime.now(timezone.utc)

        if req.status == ExperimentStatus.APPROVED and approver_id:
            exp.approved_by_id = approver_id

        if req.status in (ExperimentStatus.CONCLUDED, ExperimentStatus.CANCELLED):
            exp.concluded_at = datetime.now(timezone.utc)
            if req.status == ExperimentStatus.CANCELLED:
                exp.outcome = ExperimentOutcome.CANCELLED

        await self.db.flush()
        await self.db.refresh(exp)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=approver_id,
            event_type="experiment.transitioned",
            entity_type="optimization_experiment",
            entity_id=str(exp.id),
            payload={
                "status": exp.status.value,
                "outcome": exp.outcome.value if exp.outcome else None,
                "notes": req.notes,
            },
        )
        log.info("experiment.transitioned", experiment_id=str(experiment_id), new_status=req.status.value)
        return exp

    async def create_approval(
        self,
        org_id: UUID,
        experiment_id: UUID,
        approver_user_id: UUID,
        req: ExperimentApprovalCreate,
    ) -> ExperimentApproval:
        exp = await self.get(org_id, experiment_id)
        if not exp:
            raise ValueError("Experiment not found")
        if exp.owner_id and exp.owner_id == approver_user_id:
            raise ValueError("Experiment owner cannot self-approve")
        approval = ExperimentApproval(
            org_id=org_id,
            experiment_id=experiment_id,
            approver_user_id=approver_user_id,
            note=req.note,
        )
        self.db.add(approval)
        try:
            await self.db.flush()
        except IntegrityError as e:
            raise ValueError("User already approved this experiment") from e
        await self.db.refresh(approval)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=approver_user_id,
            event_type="experiment.approved",
            entity_type="optimization_experiment",
            entity_id=str(experiment_id),
            payload={
                "approval_id": str(approval.id),
                "note": approval.note,
            },
        )
        return approval

    async def list_approvals(self, org_id: UUID, experiment_id: UUID) -> list[ExperimentApproval]:
        result = await self.db.execute(
            select(ExperimentApproval)
            .where(ExperimentApproval.org_id == org_id, ExperimentApproval.experiment_id == experiment_id)
            .order_by(ExperimentApproval.created_at.asc())
        )
        return list(result.scalars().all())

    async def approval_count(self, org_id: UUID, experiment_id: UUID) -> int:
        approvals = await self.list_approvals(org_id, experiment_id)
        return len({a.approver_user_id for a in approvals})

    @staticmethod
    def is_high_risk(exp: OptimizationExperiment) -> bool:
        guardrails = exp.guardrails or {}
        estimated_risk = exp.estimated_risk_score or 0.0
        blast_radius = float(guardrails.get("max_blast_radius_pct", 0.0) or 0.0)
        max_cost_increase = float(guardrails.get("max_cost_increase_pct", 0.0) or 0.0)
        return estimated_risk >= 0.7 or blast_radius >= 0.2 or max_cost_increase >= 0.1

    async def get_summary(self, org_id: UUID) -> ExperimentSummary:
        exps = await self.list(org_id, limit=9999)
        by_status: dict[str, int] = {}
        total_sim = 0.0
        total_actual = 0.0
        concluded = [e for e in exps if e.status == ExperimentStatus.CONCLUDED]
        improved = [e for e in concluded if e.outcome == ExperimentOutcome.IMPROVED]

        for e in exps:
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
            total_sim += e.simulated_savings_usd or 0
            total_actual += e.actual_savings_usd or 0

        success_rate = len(improved) / len(concluded) if concluded else 0.0

        return ExperimentSummary(
            total=len(exps),
            by_status=by_status,
            total_simulated_savings_usd=round(total_sim, 2),
            total_actual_savings_usd=round(total_actual, 2),
            success_rate=round(success_rate, 3),
        )

    # ── Runs ─────────────────────────────────────────────────────────────────

    async def create_run(
        self, org_id: UUID, experiment_id: UUID, req: RunCreate, actor_user_id: Optional[UUID] = None
    ) -> ExperimentRun:
        exp = await self.get(org_id, experiment_id)
        if not exp:
            raise ValueError("Experiment not found")
        if exp.status != ExperimentStatus.RUNNING:
            raise ValueError("Experiment must be in RUNNING state to create a run")

        run = ExperimentRun(
            experiment_id=experiment_id,
            org_id=org_id,
            run_type=req.run_type,
            notes=req.notes,
            metrics_before=req.metrics_before,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="experiment.run.created",
            entity_type="experiment_run",
            entity_id=str(run.id),
            payload={
                "experiment_id": str(experiment_id),
                "run_type": run.run_type.value,
                "notes": run.notes,
            },
        )
        return run

    async def update_run(
        self,
        org_id: UUID,
        experiment_id: UUID,
        run_id: UUID,
        req: RunUpdate,
        actor_user_id: Optional[UUID] = None,
    ) -> Optional[ExperimentRun]:
        result = await self.db.execute(
            select(ExperimentRun).where(
                ExperimentRun.id == run_id,
                ExperimentRun.experiment_id == experiment_id,
                ExperimentRun.org_id == org_id,
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            return None
        for field, value in req.model_dump(exclude_none=True).items():
            setattr(run, field, value)
        if req.status in (RunStatus.COMPLETED, RunStatus.ROLLED_BACK):
            run.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(run)
        await self.audit_chain.append_event(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type="experiment.run.updated",
            entity_type="experiment_run",
            entity_id=str(run.id),
            payload=req.model_dump(exclude_none=True),
        )
        return run

    async def list_runs(self, org_id: UUID, experiment_id: UUID) -> list[ExperimentRun]:
        result = await self.db.execute(
            select(ExperimentRun)
            .where(ExperimentRun.experiment_id == experiment_id, ExperimentRun.org_id == org_id)
            .order_by(ExperimentRun.created_at.desc())
        )
        return list(result.scalars().all())
