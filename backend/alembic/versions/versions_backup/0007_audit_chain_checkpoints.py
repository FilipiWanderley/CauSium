"""audit chain checkpoints

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_chain_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("generated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("latest_event_hash", sa.Text(), nullable=False),
        sa.Column("checked_events", sa.Integer(), nullable=False),
        sa.Column("snapshot_payload", JSONB(), nullable=False),
        sa.Column("snapshot_signature", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_chain_checkpoints_org_id", "audit_chain_checkpoints", ["org_id"])
    op.create_index("ix_audit_chain_checkpoints_generated_by_user_id", "audit_chain_checkpoints", ["generated_by_user_id"])
    op.create_index("ix_audit_chain_checkpoints_snapshot_signature", "audit_chain_checkpoints", ["snapshot_signature"])
    op.create_index("ix_audit_chain_checkpoints_created_at", "audit_chain_checkpoints", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_chain_checkpoints")
