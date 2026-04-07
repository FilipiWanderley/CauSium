"""platform_admin global role

Adds 'platform_admin' value to the userrole PostgreSQL enum.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-07 00:00:00.000000

Note on downgrade:
  PostgreSQL does not support removing enum values once created.
  The downgrade is intentionally a no-op; to fully revert, recreate
  the enum without the value (requires a full column-type migration).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS is supported from PostgreSQL 9.6+
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'platform_admin'")


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE on enums.
    # Intentional no-op — see module docstring for full revert instructions.
    pass
