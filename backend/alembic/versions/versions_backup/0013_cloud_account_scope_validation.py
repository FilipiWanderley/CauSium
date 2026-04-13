"""SP-CL03: cloud_accounts scope validation metadata

Adds:
  - cloud_accounts.scopes_validated_at (timestamp with tz)
  - cloud_accounts.validated_scopes (text JSON list[str])

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cloud_accounts",
        sa.Column("scopes_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cloud_accounts",
        sa.Column("validated_scopes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cloud_accounts", "validated_scopes")
    op.drop_column("cloud_accounts", "scopes_validated_at")
