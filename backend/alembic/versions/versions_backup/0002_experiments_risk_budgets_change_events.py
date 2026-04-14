"""experiments, risk_budgets, change_events

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(name: str) -> PgEnum:
    """Reference an existing PostgreSQL enum type without auto-creating it."""
    return PgEnum(name=name, create_type=False)


def upgrade() -> None:
    # ── Create enum types ─────────────────────────────────────────────────────
    enums = {
        "budgetperiod": ["daily", "weekly", "monthly"],
        "budgettype": ["blast_radius", "cost_variance", "error_rate", "change_frequency"],
        "experimentstatus": ["draft", "hypothesis", "simulating", "approved", "running", "measuring", "concluded", "cancelled"],
        "experimentoutcome": ["improved", "regressed", "inconclusive", "cancelled"],
        "runtype": ["dry_run", "canary", "full"],
        "runstatus": ["pending", "running", "completed", "rolled_back"],
        "changeeventtype": ["deploy", "config_change", "scaling", "incident", "cost_anomaly", "policy_change"],
    }
    for name, values in enums.items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({vals})")

    # ── risk_budgets ──────────────────────────────────────────────────────────
    op.create_table(
        "risk_budgets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("budget_type", _enum("budgettype"), nullable=False),
        sa.Column("period", _enum("budgetperiod"), nullable=False, server_default="weekly"),
        sa.Column("limit_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_budgets_org_id", "risk_budgets", ["org_id"])

    # ── optimization_experiments ──────────────────────────────────────────────
    op.create_table(
        "optimization_experiments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("experimentstatus"), nullable=False, server_default="draft"),
        sa.Column("outcome", _enum("experimentoutcome"), nullable=True),
        sa.Column("simulated_savings_usd", sa.Float(), nullable=True),
        sa.Column("simulated_confidence", sa.Float(), nullable=True),
        sa.Column("simulation_notes", sa.Text(), nullable=True),
        sa.Column("guardrails", JSONB(), nullable=True),
        sa.Column("causal_change_event_ids", JSONB(), nullable=True),
        sa.Column("causal_summary", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("approved_by_id", sa.UUID(), nullable=True),
        sa.Column("risk_budget_id", sa.UUID(), nullable=True),
        sa.Column("estimated_risk_score", sa.Float(), nullable=True),
        sa.Column("actual_savings_usd", sa.Float(), nullable=True),
        sa.Column("actual_confidence", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["optimization_opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_budget_id"], ["risk_budgets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_org_id", "optimization_experiments", ["org_id"])

    # ── experiment_runs ───────────────────────────────────────────────────────
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("run_type", _enum("runtype"), nullable=False),
        sa.Column("status", _enum("runstatus"), nullable=False, server_default="pending"),
        sa.Column("metrics_before", JSONB(), nullable=True),
        sa.Column("metrics_after", JSONB(), nullable=True),
        sa.Column("impact_usd", sa.Float(), nullable=True),
        sa.Column("error_rate_before", sa.Float(), nullable=True),
        sa.Column("error_rate_after", sa.Float(), nullable=True),
        sa.Column("rollback_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["optimization_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_runs_experiment_id", "experiment_runs", ["experiment_id"])

    # ── change_events ─────────────────────────────────────────────────────────
    op.create_table(
        "change_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("event_type", _enum("changeeventtype"), nullable=False),
        sa.Column("service", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.String(500), nullable=True),
        sa.Column("environment", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("owner_team", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost_impact_usd", sa.Float(), nullable=True),
        sa.Column("causal_confidence", sa.Float(), nullable=True),
        sa.Column("external_ref", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_events_org_id", "change_events", ["org_id"])
    op.create_index("ix_change_events_occurred_at", "change_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("change_events")
    op.drop_table("experiment_runs")
    op.drop_table("optimization_experiments")
    op.drop_table("risk_budgets")
    for enum in ["changeeventtype", "runstatus", "runtype", "experimentoutcome", "experimentstatus", "budgettype", "budgetperiod"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
