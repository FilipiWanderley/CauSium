from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, func
from app.core.types import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_VC = lambda x: [e.value for e in x]  # noqa: E731


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    HYPOTHESIS = "hypothesis"
    SIMULATING = "simulating"
    APPROVED = "approved"
    RUNNING = "running"
    MEASURING = "measuring"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"


class ExperimentOutcome(str, enum.Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"


class RunType(str, enum.Enum):
    DRY_RUN = "dry_run"
    CANARY = "canary"
    FULL = "full"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


VALID_EXPERIMENT_TRANSITIONS: dict[ExperimentStatus, list[ExperimentStatus]] = {
    ExperimentStatus.DRAFT:       [ExperimentStatus.HYPOTHESIS, ExperimentStatus.CANCELLED],
    ExperimentStatus.HYPOTHESIS:  [ExperimentStatus.SIMULATING, ExperimentStatus.CANCELLED],
    ExperimentStatus.SIMULATING:  [ExperimentStatus.APPROVED, ExperimentStatus.DRAFT, ExperimentStatus.CANCELLED],
    ExperimentStatus.APPROVED:    [ExperimentStatus.RUNNING, ExperimentStatus.CANCELLED],
    ExperimentStatus.RUNNING:     [ExperimentStatus.MEASURING, ExperimentStatus.CANCELLED],
    ExperimentStatus.MEASURING:   [ExperimentStatus.CONCLUDED, ExperimentStatus.RUNNING],
    ExperimentStatus.CONCLUDED:   [],
    ExperimentStatus.CANCELLED:   [],
}


class OptimizationExperiment(Base):
    __tablename__ = "optimization_experiments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("optimization_opportunities.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hypothesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_environment: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    target_criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")

    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus, values_callable=_VC), default=ExperimentStatus.DRAFT
    )
    outcome: Mapped[Optional[ExperimentOutcome]] = mapped_column(
        Enum(ExperimentOutcome, values_callable=_VC), nullable=True
    )

    # Simulation results
    simulated_savings_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    simulated_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1
    simulation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Guardrails (JSON): {"max_blast_radius": 0.2, "rollback_on_error_rate": 0.05, ...}
    guardrails: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Causal context
    causal_change_event_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    causal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ownership
    owner_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Risk
    risk_budget_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("risk_budgets.id", ondelete="SET NULL"), nullable=True)
    estimated_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Actual results
    actual_savings_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    concluded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    experiment_id: Mapped[UUID] = mapped_column(ForeignKey("optimization_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    run_type: Mapped[RunType] = mapped_column(Enum(RunType, values_callable=_VC), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, values_callable=_VC), default=RunStatus.PENDING)

    # Metrics captured during run
    metrics_before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metrics_after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    impact_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rollback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentApproval(Base):
    __tablename__ = "experiment_approvals"
    __table_args__ = (UniqueConstraint("experiment_id", "approver_user_id", name="uq_experiment_approval_user"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_id: Mapped[UUID] = mapped_column(
        ForeignKey("optimization_experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approver_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
