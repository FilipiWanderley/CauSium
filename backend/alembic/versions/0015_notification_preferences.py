"""notification preferences

Revision ID: 0015_notification_preferences
Revises: 0014_dlq_messages
Create Date: 2026-04-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0015_notification_preferences"
down_revision = "0014_dlq_messages"
branch_labels = None
depends_on = None


notification_frequency_enum = postgresql.ENUM(
    "instant",
    "daily",
    "weekly",
    name="notificationfrequency",
    create_type=False,
)


def upgrade() -> None:
    notification_frequency_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("slack_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("frequency", notification_frequency_enum, nullable=False, server_default="instant"),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_notification_preferences_org_user"),
    )
    op.create_index(op.f("ix_notification_preferences_org_id"), "notification_preferences", ["org_id"], unique=False)
    op.create_index(op.f("ix_notification_preferences_user_id"), "notification_preferences", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_index(op.f("ix_notification_preferences_org_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")

    notification_frequency_enum.drop(op.get_bind(), checkfirst=True)
