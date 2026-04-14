"""passkey-first auth

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("passwordless_only", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("passkey_enabled", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("challenge", sa.String(length=512), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge"),
    )
    op.create_index("ix_auth_challenges_org_id", "auth_challenges", ["org_id"])
    op.create_index("ix_auth_challenges_user_id", "auth_challenges", ["user_id"])
    op.create_index("ix_auth_challenges_challenge", "auth_challenges", ["challenge"])

    op.create_table(
        "passkey_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key_jwk", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
        sa.UniqueConstraint("user_id", "credential_id", name="uq_passkey_user_credential"),
    )
    op.create_index("ix_passkey_credentials_org_id", "passkey_credentials", ["org_id"])
    op.create_index("ix_passkey_credentials_user_id", "passkey_credentials", ["user_id"])
    op.create_index("ix_passkey_credentials_credential_id", "passkey_credentials", ["credential_id"])


def downgrade() -> None:
    op.drop_table("passkey_credentials")
    op.drop_table("auth_challenges")
    op.drop_column("users", "passkey_enabled")
    op.drop_column("organizations", "passwordless_only")
