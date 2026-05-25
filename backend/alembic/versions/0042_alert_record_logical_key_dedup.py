"""add alert_records.logical_key and dedupe indexes

Revision ID: 0042
Revises: 0041
Create Date: 2026-05-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0042"
down_revision: Union[str, None] = "0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alert_records", sa.Column("logical_key", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            "UPDATE alert_records "
            "SET logical_key = source_type || ':' || source_id "
            "WHERE logical_key IS NULL AND source_type IS NOT NULL AND source_id IS NOT NULL"
        )
    )
    op.create_index(
        "uq_alert_records_org_cat_logical_user_null",
        "alert_records",
        ["org_id", "category", "logical_key"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL AND logical_key IS NOT NULL"),
    )
    op.create_index(
        "uq_alert_records_org_user_cat_logical",
        "alert_records",
        ["org_id", "user_id", "category", "logical_key"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND logical_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_alert_records_org_user_cat_logical", table_name="alert_records")
    op.drop_index("uq_alert_records_org_cat_logical_user_null", table_name="alert_records")
    op.drop_column("alert_records", "logical_key")

