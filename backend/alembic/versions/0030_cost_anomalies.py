"""Add cost_anomalies table for automatic anomaly detection.

Revision ID: 0030
Revises: 0029
Create Date: 2026-04-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    severity_enum = sa.Enum("low", "medium", "high", name="costanomalyseverity")
    severity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cost_anomalies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("service", sa.String(length=120), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("current_cost_usd", sa.Float(), nullable=False),
        sa.Column("historical_mean_usd", sa.Float(), nullable=False),
        sa.Column("historical_stddev_usd", sa.Float(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False),
        sa.Column("deviation_pct", sa.Float(), nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False, server_default=sa.text("14")),
        sa.Column("z_threshold", sa.Float(), nullable=False, server_default=sa.text("2.5")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "provider",
            "service",
            "observed_date",
            name="uq_cost_anomalies_org_provider_service_date",
        ),
    )
    op.create_index(op.f("ix_cost_anomalies_org_id"), "cost_anomalies", ["org_id"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_provider"), "cost_anomalies", ["provider"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_service"), "cost_anomalies", ["service"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_observed_date"), "cost_anomalies", ["observed_date"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_z_score"), "cost_anomalies", ["z_score"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_severity"), "cost_anomalies", ["severity"], unique=False)
    op.create_index(op.f("ix_cost_anomalies_created_at"), "cost_anomalies", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_cost_anomalies_created_at"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_severity"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_z_score"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_observed_date"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_service"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_provider"), table_name="cost_anomalies")
    op.drop_index(op.f("ix_cost_anomalies_org_id"), table_name="cost_anomalies")
    op.drop_table("cost_anomalies")
    sa.Enum(name="costanomalyseverity").drop(op.get_bind(), checkfirst=True)
