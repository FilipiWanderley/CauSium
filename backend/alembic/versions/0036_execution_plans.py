"""add execution plans persistence

Revision ID: 0036
Revises: 0035
Create Date: 2026-04-24
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0036"
down_revision: Union[str, None] = "0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("total_savings_monthly", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("selected_opportunity_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gates_triggered", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conflicts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_plans_org_id"), "execution_plans", ["org_id"], unique=False)
    op.create_index(op.f("ix_execution_plans_status"), "execution_plans", ["status"], unique=False)
    op.create_index(op.f("ix_execution_plans_created_by_user_id"), "execution_plans", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_execution_plans_created_at"), "execution_plans", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_execution_plans_created_at"), table_name="execution_plans")
    op.drop_index(op.f("ix_execution_plans_created_by_user_id"), table_name="execution_plans")
    op.drop_index(op.f("ix_execution_plans_status"), table_name="execution_plans")
    op.drop_index(op.f("ix_execution_plans_org_id"), table_name="execution_plans")
    op.drop_table("execution_plans")
