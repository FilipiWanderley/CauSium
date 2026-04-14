"""workspace lifecycle state machine

Adds lifecycle_state, member_quota, suspended_at, suspended_reason to organizations.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_lifecycle_enum = sa.Enum(
    "active", "suspended", "archived",
    name="workspacelifecyclestate",
)


def upgrade() -> None:
    _lifecycle_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "organizations",
        sa.Column(
            "lifecycle_state",
            _lifecycle_enum,
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("member_quota", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "organizations",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("suspended_reason", sa.String(500), nullable=True),
    )
    op.create_index(
        "ix_organizations_lifecycle_state",
        "organizations",
        ["lifecycle_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_lifecycle_state", table_name="organizations")
    op.drop_column("organizations", "suspended_reason")
    op.drop_column("organizations", "suspended_at")
    op.drop_column("organizations", "member_quota")
    op.drop_column("organizations", "lifecycle_state")
    _lifecycle_enum.drop(op.get_bind(), checkfirst=True)
