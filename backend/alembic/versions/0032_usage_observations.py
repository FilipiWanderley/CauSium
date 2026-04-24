"""add usage observations table

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-24
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0032"
down_revision: Union[str, None] = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "usage_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("resource_id", sa.String(length=600), nullable=False),
        sa.Column("metric_name", sa.String(length=120), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_value", sa.Float(), nullable=False),
        sa.Column("p95_value", sa.Float(), nullable=False),
        sa.Column("max_value", sa.Float(), nullable=False),
        sa.Column("min_value", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "account_id",
            "provider",
            "resource_id",
            "metric_name",
            "window_start",
            "window_end",
            name="uq_usage_observation_window",
        ),
    )
    op.create_index(op.f("ix_usage_observations_org_id"), "usage_observations", ["org_id"], unique=False)
    op.create_index(op.f("ix_usage_observations_account_id"), "usage_observations", ["account_id"], unique=False)
    op.create_index(op.f("ix_usage_observations_provider"), "usage_observations", ["provider"], unique=False)
    op.create_index(op.f("ix_usage_observations_resource_id"), "usage_observations", ["resource_id"], unique=False)
    op.create_index(op.f("ix_usage_observations_metric_name"), "usage_observations", ["metric_name"], unique=False)
    op.create_index(op.f("ix_usage_observations_window_start"), "usage_observations", ["window_start"], unique=False)
    op.create_index(op.f("ix_usage_observations_window_end"), "usage_observations", ["window_end"], unique=False)
    op.create_index(op.f("ix_usage_observations_created_at"), "usage_observations", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_usage_observations_created_at"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_window_end"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_window_start"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_metric_name"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_resource_id"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_provider"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_account_id"), table_name="usage_observations")
    op.drop_index(op.f("ix_usage_observations_org_id"), table_name="usage_observations")
    op.drop_table("usage_observations")
