"""workspace invites

Adds workspace_invites table for the member invite flow.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invitestatus') THEN
                CREATE TYPE invitestatus AS ENUM ('pending', 'accepted', 'expired', 'revoked');
            END IF;
        END$$;
        """
    )

    op.create_table(
        "workspace_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("invited_email", sa.String(255), nullable=False),
        sa.Column(
            "invited_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_workspace_invites_org_id", "workspace_invites", ["org_id"])
    op.create_index("ix_workspace_invites_token", "workspace_invites", ["token"], unique=True)
    op.create_index("ix_workspace_invites_invited_email", "workspace_invites", ["invited_email"])

    op.execute("ALTER TABLE workspace_invites ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE workspace_invites ALTER COLUMN status TYPE invitestatus USING status::invitestatus")
    op.execute("ALTER TABLE workspace_invites ALTER COLUMN status SET DEFAULT 'pending'::invitestatus")


def downgrade() -> None:
    op.drop_index("ix_workspace_invites_invited_email", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_token", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_org_id", table_name="workspace_invites")
    op.drop_table("workspace_invites")
    op.execute("DROP TYPE IF EXISTS invitestatus")
