"""SP-A01: force password change fields

Adds must_change_password and password_changed_at to the users table.

must_change_password — boolean flag; when True the user is required to set a
    new password before accessing any protected resource.  It is set by:
      • admin-created accounts (create_user)
      • admin-initiated password resets  (POST /users/{id}/reset-password, SP-U01)

password_changed_at — UTC timestamp of the most recent voluntary password
    change (excludes system-forced resets).  Used for future expiry policies.

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "must_change_password")
