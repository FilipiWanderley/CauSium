"""activity events

Revision ID: 0017_activity_events
Revises: 0016_notification_slack_configs
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0017_activity_events"
down_revision = "0016_notification_slack_configs"
branch_labels = None
depends_on = None


activity_event_severity_enum = postgresql.ENUM(
    "info",
    "warning",
    "critical",
    name="activityeventseverity",
    create_type=False,
)


def upgrade() -> None:
    activity_event_severity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("severity", activity_event_severity_enum, nullable=False, server_default="info"),
        sa.Column("service", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_activity_events_org_id"), "activity_events", ["org_id"], unique=False)
    op.create_index(op.f("ix_activity_events_account_id"), "activity_events", ["account_id"], unique=False)
    op.create_index(op.f("ix_activity_events_event_type"), "activity_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_activity_events_severity"), "activity_events", ["severity"], unique=False)
    op.create_index(op.f("ix_activity_events_service"), "activity_events", ["service"], unique=False)
    op.create_index(op.f("ix_activity_events_resource_id"), "activity_events", ["resource_id"], unique=False)
    op.create_index(op.f("ix_activity_events_occurred_at"), "activity_events", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_activity_events_created_at"), "activity_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_events_created_at"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_occurred_at"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_resource_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_service"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_severity"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_event_type"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_account_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_org_id"), table_name="activity_events")
    op.drop_table("activity_events")

    activity_event_severity_enum.drop(op.get_bind(), checkfirst=True)
