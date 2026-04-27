"""add support access sessions

Revision ID: 0038
Revises: 0037
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0038"
down_revision: Union[str, None] = "0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

support_status = postgresql.ENUM(
    "active", "ended", "expired",
    name="supportaccessstatus",
    create_type=False,
)


def upgrade() -> None:
    support_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "support_access_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("target_org_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", support_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_access_sessions_actor_user_id"),
        "support_access_sessions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_access_sessions_target_org_id"),
        "support_access_sessions",
        ["target_org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_access_sessions_status"),
        "support_access_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_access_sessions_expires_at"),
        "support_access_sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_support_access_sessions_expires_at"), table_name="support_access_sessions")
    op.drop_index(op.f("ix_support_access_sessions_status"), table_name="support_access_sessions")
    op.drop_index(op.f("ix_support_access_sessions_target_org_id"), table_name="support_access_sessions")
    op.drop_index(op.f("ix_support_access_sessions_actor_user_id"), table_name="support_access_sessions")
    op.drop_table("support_access_sessions")
    sa.Enum(name="supportaccessstatus").drop(op.get_bind(), checkfirst=True)
