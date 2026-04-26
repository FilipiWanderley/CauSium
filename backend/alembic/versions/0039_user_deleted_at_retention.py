"""add users.deleted_at for retention policy

Revision ID: 0039
Revises: 0038
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0039"
down_revision: Union[str, None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_column("users", "deleted_at")
