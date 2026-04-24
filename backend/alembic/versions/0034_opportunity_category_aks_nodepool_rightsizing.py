"""add aks_nodepool_rightsizing opportunity category

Revision ID: 0034
Revises: 0033
Create Date: 2026-04-24

Note on downgrade:
  PostgreSQL does not support removing enum values once created.
  The downgrade is intentionally a no-op.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0034"
down_revision: Union[str, None] = "0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE opportunitycategory ADD VALUE IF NOT EXISTS 'aks_nodepool_rightsizing'")


def downgrade() -> None:
    pass
