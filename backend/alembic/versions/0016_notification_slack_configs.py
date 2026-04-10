"""notification slack configs

Revision ID: 0016_notification_slack_configs
Revises: 0015_notification_preferences
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0016_notification_slack_configs"
down_revision = "0015_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_slack_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("webhook_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", name="uq_notification_slack_configs_org"),
    )
    op.create_index(op.f("ix_notification_slack_configs_org_id"), "notification_slack_configs", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_slack_configs_org_id"), table_name="notification_slack_configs")
    op.drop_table("notification_slack_configs")
