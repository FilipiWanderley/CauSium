"""tenant settings for FinOps configuration

Revision ID: 0043
Revises: 0042
Create Date: 2026-06-07 16:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0043"
down_revision: Union[str, None] = "0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "setting_key", name="uq_tenant_settings_org_key"),
    )
    op.create_index("ix_tenant_settings_org_id", "tenant_settings", ["org_id"])
    op.create_index("ix_tenant_settings_org_key", "tenant_settings", ["org_id", "setting_key"])


def downgrade() -> None:
    op.drop_index("ix_tenant_settings_org_key", table_name="tenant_settings")
    op.drop_index("ix_tenant_settings_org_id", table_name="tenant_settings")
    op.drop_table("tenant_settings")