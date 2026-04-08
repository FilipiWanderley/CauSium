"""notifications: alert_records table

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "financial", "optimization", "governance", "activity", "security",
                name="alertcategory",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("info", "warning", "critical", name="alertseverity"),
            nullable=False,
            server_default="info",
        ),
        sa.Column(
            "status",
            sa.Enum("unread", "read", "archived", name="alertstatus"),
            nullable=False,
            server_default="unread",
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("action_url", sa.String(length=1000), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_records_org_id", "alert_records", ["org_id"])
    op.create_index("ix_alert_records_user_id", "alert_records", ["user_id"])
    op.create_index("ix_alert_records_category", "alert_records", ["category"])
    op.create_index("ix_alert_records_status", "alert_records", ["status"])
    op.create_index("ix_alert_records_created_at", "alert_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("alert_records")
    op.execute("DROP TYPE IF EXISTS alertcategory")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS alertstatus")
