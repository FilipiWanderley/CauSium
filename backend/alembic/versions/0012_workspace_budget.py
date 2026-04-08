"""SP-EC01: workspace_budgets table

WorkspaceBudget stores the configurable financial budget for each workspace
(one row per org_id).  Columns:
  - id              UUID PK
  - org_id          FK → organizations(id) ON DELETE CASCADE, UNIQUE
  - amount_usd      FLOAT — total budget ceiling
  - period          ENUM 'monthly' | 'quarterly' | 'annual'
  - currency        CHAR(3) — ISO-4217 display currency (default 'USD')
  - alert_thresholds TEXT  — JSON-encoded list[int] of % alert breakpoints
  - created_at / updated_at timestamps

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERIOD_ENUM = sa.Enum(
    "monthly",
    "quarterly",
    "annual",
    name="financialbudgetperiod",
)


def upgrade() -> None:
    op.create_table(
        "workspace_budgets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column(
            "period",
            _PERIOD_ENUM,
            nullable=False,
            server_default="monthly",
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "alert_thresholds",
            sa.Text(),
            nullable=False,
            server_default="[50, 80, 90]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", name="uq_workspace_budgets_org_id"),
    )
    op.create_index(
        op.f("ix_workspace_budgets_org_id"),
        "workspace_budgets",
        ["org_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_budgets_org_id"), table_name="workspace_budgets")
    op.drop_table("workspace_budgets")
    _PERIOD_ENUM.drop(op.get_bind(), checkfirst=True)
