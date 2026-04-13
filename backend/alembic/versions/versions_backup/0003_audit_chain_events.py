"""add audit chain events

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_chain_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("event_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_hash"),
    )
    op.create_index("ix_audit_chain_events_org_id", "audit_chain_events", ["org_id"])
    op.create_index("ix_audit_chain_events_actor_user_id", "audit_chain_events", ["actor_user_id"])
    op.create_index("ix_audit_chain_events_event_type", "audit_chain_events", ["event_type"])
    op.create_index("ix_audit_chain_events_entity_type", "audit_chain_events", ["entity_type"])
    op.create_index("ix_audit_chain_events_entity_id", "audit_chain_events", ["entity_id"])
    op.create_index("ix_audit_chain_events_event_hash", "audit_chain_events", ["event_hash"])
    op.create_index("ix_audit_chain_events_created_at", "audit_chain_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_chain_events")
