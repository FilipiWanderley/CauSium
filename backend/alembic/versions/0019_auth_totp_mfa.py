"""auth totp mfa

Revision ID: 0019_auth_totp_mfa
Revises: 0018_notification_alert_rules
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0019_auth_totp_mfa"
down_revision = "0018_notification_alert_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("totp_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_verified_at")
    op.drop_column("users", "totp_secret_encrypted")
    op.drop_column("users", "totp_enabled")
