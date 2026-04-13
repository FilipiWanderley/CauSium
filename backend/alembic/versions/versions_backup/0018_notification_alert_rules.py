"""notification alert rules

Revision ID: 0018_notification_alert_rules
Revises: 0017_activity_events
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0018_notification_alert_rules"
down_revision = "0017_activity_events"
branch_labels = None
depends_on = None


alert_category_enum = postgresql.ENUM(
    "financial",
    "optimization",
    "governance",
    "activity",
    "security",
    name="alertcategory",
    create_type=False,
)

alert_severity_enum = postgresql.ENUM(
    "info",
    "warning",
    "critical",
    name="alertseverity",
    create_type=False,
)


def upgrade() -> None:
    alert_category_enum.create(op.get_bind(), checkfirst=True)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification_alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", alert_category_enum, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("min_severity", alert_severity_enum, nullable=False, server_default="critical"),
        sa.Column("event_type_prefix", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "category", name="uq_notification_alert_rules_org_category"),
    )

    op.create_index(op.f("ix_notification_alert_rules_org_id"), "notification_alert_rules", ["org_id"], unique=False)
    op.create_index(op.f("ix_notification_alert_rules_category"), "notification_alert_rules", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_alert_rules_category"), table_name="notification_alert_rules")
    op.drop_index(op.f("ix_notification_alert_rules_org_id"), table_name="notification_alert_rules")
    op.drop_table("notification_alert_rules")
