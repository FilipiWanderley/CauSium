"""add sku and family fields to optimization opportunities

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "optimization_opportunities",
        sa.Column("sku_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "optimization_opportunities",
        sa.Column("machine_family", sa.String(length=80), nullable=True),
    )


def downgrade():
    op.drop_column("optimization_opportunities", "machine_family")
    op.drop_column("optimization_opportunities", "sku_name")
