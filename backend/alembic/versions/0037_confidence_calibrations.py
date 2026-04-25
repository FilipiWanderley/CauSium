"""add confidence calibrations table

Revision ID: 0037
Revises: 0036
Create Date: 2026-04-25
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0037"
down_revision: Union[str, None] = "0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "confidence_calibrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("dimension_type", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=120), nullable=False),
        sa.Column("total_executions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cumulative_accuracy", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("historical_accuracy", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_adjustment", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "dimension_type",
            "dimension_key",
            name="uq_confidence_calibrations_org_dimension",
        ),
    )
    op.create_index(op.f("ix_confidence_calibrations_org_id"), "confidence_calibrations", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_confidence_calibrations_dimension_key"),
        "confidence_calibrations",
        ["dimension_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_confidence_calibrations_dimension_key"), table_name="confidence_calibrations")
    op.drop_index(op.f("ix_confidence_calibrations_org_id"), table_name="confidence_calibrations")
    op.drop_table("confidence_calibrations")
