"""make users.org_id nullable for platform_admin accounts

Revision ID: 0040
Revises: 0039
Create Date: 2026-05-01
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0040"
down_revision: Union[str, None] = "0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "org_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    # Set any NULL org_id to a sentinel before reverting (prevents data loss)
    op.execute("UPDATE users SET org_id = '00000000-0000-0000-0000-000000000000' WHERE org_id IS NULL")
    op.alter_column("users", "org_id", existing_type=sa.UUID(), nullable=False)
