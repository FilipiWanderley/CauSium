"""add tenant_business_rules and tenant_business_audit tables

Revision ID: 0044
Revises: 0043
Create Date: 2026-06-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0044"
down_revision: Union[str, None] = "0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

rule_type_enum = postgresql.ENUM(
    "resource_group",
    "service",
    "subscription",
    "resource_name",
    name="busineseruletype",
    create_type=False,
)

criteria_operator_enum = postgresql.ENUM(
    "equals",
    "contains",
    "starts_with",
    "ends_with",
    name="businesscriteriaoperator",
    create_type=False,
)

audit_action_enum = postgresql.ENUM(
    "RULE_CREATED",
    "RULE_UPDATED",
    "RULE_DELETED",
    "RULE_ACTIVATED",
    "RULE_DEACTIVATED",
    name="businessauditaction",
    create_type=False,
)


def upgrade() -> None:
    # Create enums
    rule_type_enum.create(op.get_bind(), checkfirst=True)
    criteria_operator_enum.create(op.get_bind(), checkfirst=True)
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create tenant_business_rules table
    op.create_table(
        "tenant_business_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_type", rule_type_enum, nullable=False),
        sa.Column("criteria_field", sa.String(100), nullable=False),
        sa.Column("criteria_operator", criteria_operator_enum, nullable=False),
        sa.Column("criteria_value", sa.String(500), nullable=False),
        sa.Column("destination_team", sa.String(255), nullable=False),
        sa.Column("destination_cost_center", sa.String(255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tbr_org_id", "tenant_business_rules", ["org_id"])
    op.create_index("ix_tbr_is_active", "tenant_business_rules", ["is_active"])
    op.create_index("ix_tbr_priority", "tenant_business_rules", ["priority"])

    # Create tenant_business_audit table
    op.create_table(
        "tenant_business_audit",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tba_org_id", "tenant_business_audit", ["org_id"])
    op.create_index("ix_tba_entity", "tenant_business_audit", ["entity_type", "entity_id"])
    op.create_index("ix_tba_created_at", "tenant_business_audit", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tba_created_at", table_name="tenant_business_audit")
    op.drop_index("ix_tba_entity", table_name="tenant_business_audit")
    op.drop_index("ix_tba_org_id", table_name="tenant_business_audit")
    op.drop_table("tenant_business_audit")

    op.drop_index("ix_tbr_priority", table_name="tenant_business_rules")
    op.drop_index("ix_tbr_is_active", table_name="tenant_business_rules")
    op.drop_index("ix_tbr_org_id", table_name="tenant_business_rules")
    op.drop_table("tenant_business_rules")

    audit_action_enum.drop(op.get_bind(), checkfirst=True)
    criteria_operator_enum.drop(op.get_bind(), checkfirst=True)
    rule_type_enum.drop(op.get_bind(), checkfirst=True)
