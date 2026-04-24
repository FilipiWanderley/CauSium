"""add decision evidence to optimization opportunities

Revision ID: 0033
Revises: 0032
Create Date: 2026-04-24
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: Union[str, None] = "0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "optimization_opportunities",
        sa.Column("decision_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("optimization_opportunities", "decision_evidence")
