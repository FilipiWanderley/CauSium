"""experiment policy and approvals

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "optimization_experiments",
        sa.Column("target_environment", sa.String(length=50), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "optimization_experiments",
        sa.Column("target_criticality", sa.String(length=50), nullable=False, server_default="medium"),
    )

    op.create_table(
        "experiment_approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=False),
        sa.Column("approver_user_id", sa.UUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experiment_id"], ["optimization_experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "approver_user_id", name="uq_experiment_approval_user"),
    )
    op.create_index("ix_experiment_approvals_org_id", "experiment_approvals", ["org_id"])
    op.create_index("ix_experiment_approvals_experiment_id", "experiment_approvals", ["experiment_id"])
    op.create_index("ix_experiment_approvals_approver_user_id", "experiment_approvals", ["approver_user_id"])


def downgrade() -> None:
    op.drop_table("experiment_approvals")
    op.drop_column("optimization_experiments", "target_criticality")
    op.drop_column("optimization_experiments", "target_environment")
