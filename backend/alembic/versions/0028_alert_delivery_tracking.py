"""Add email_sent_at and slack_sent_at to alert_records for delivery deduplication.

Revision ID: 0028
Revises: 0027
Create Date: 2026-03-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "alert_records",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "alert_records",
        sa.Column("slack_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Index to make the worker poll query efficient
    op.create_index(
        "ix_alert_records_email_sent_at",
        "alert_records",
        ["email_sent_at"],
    )
    op.create_index(
        "ix_alert_records_slack_sent_at",
        "alert_records",
        ["slack_sent_at"],
    )


def downgrade():
    op.drop_index("ix_alert_records_slack_sent_at", table_name="alert_records")
    op.drop_index("ix_alert_records_email_sent_at", table_name="alert_records")
    op.drop_column("alert_records", "slack_sent_at")
    op.drop_column("alert_records", "email_sent_at")
