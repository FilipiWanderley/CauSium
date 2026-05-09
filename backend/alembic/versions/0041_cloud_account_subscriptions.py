"""add cloud_account_subscriptions table

Revision ID: 0041
Revises: 0040
Create Date: 2026-05-09
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: Union[str, None] = "0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cloud_account_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("cloud_account_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("azure", "aws", "gcp", name="cloudprovider"),
            nullable=False,
        ),
        sa.Column("cloud_tenant_id", sa.String(255), nullable=True),
        sa.Column("subscription_id", sa.String(255), nullable=False),
        sa.Column("subscription_name", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "discovered", "removed", name="subscriptionstatus"),
            nullable=False,
            server_default="discovered",
        ),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["cloud_account_id"], ["cloud_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "cloud_account_id",
            "provider",
            "subscription_id",
            name="uq_cas_org_account_provider_sub",
        ),
    )
    op.create_index("ix_cas_org_id", "cloud_account_subscriptions", ["org_id"])
    op.create_index(
        "ix_cas_cloud_account_id", "cloud_account_subscriptions", ["cloud_account_id"]
    )
    op.create_index(
        "ix_cas_subscription_id", "cloud_account_subscriptions", ["subscription_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cas_subscription_id", table_name="cloud_account_subscriptions")
    op.drop_index("ix_cas_cloud_account_id", table_name="cloud_account_subscriptions")
    op.drop_index("ix_cas_org_id", table_name="cloud_account_subscriptions")
    op.drop_table("cloud_account_subscriptions")
    # cloudprovider enum is shared with cloud_accounts -- do NOT drop it here.
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")