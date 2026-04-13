"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="growth"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "engineer", "finops", "executive", "viewer", name="userrole"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])

    # cloud_accounts
    op.create_table(
        "cloud_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("azure", "aws", "gcp", name="cloudprovider"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=True),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "error", "pending", name="connectorstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cloud_accounts_org_id", "cloud_accounts", ["org_id"])

    # connector_health
    op.create_table(
        "connector_health",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", "error", "pending", name="connectorstatus"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connector_health_account_id", "connector_health", ["account_id"])

    # optimization_opportunities
    op.create_table(
        "optimization_opportunities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "rightsizing", "idle_resources", "reserved_instances",
                "storage_optimization", "network_optimization",
                "license_optimization", "architecture_change",
                name="opportunitycategory",
            ),
            nullable=False,
        ),
        sa.Column("financial_impact_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("effort_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("criticality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estimated_monthly_savings_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estimated_annual_savings_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_monthly_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.Enum("low", "medium", "high", name="risklevel"), nullable=False, server_default="low"),
        sa.Column("effort_level", sa.Enum("low", "medium", "high", name="effortlevel"), nullable=False, server_default="medium"),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "resolved", "dismissed", "validated", name="opportunitystatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("resource_id", sa.String(500), nullable=True),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("service", sa.String(255), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("environment", sa.String(50), nullable=True),
        sa.Column("owner_team", sa.String(100), nullable=True),
        sa.Column("score_rationale", sa.Text(), nullable=True),
        sa.Column("playbook", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_org_id_score", "optimization_opportunities", ["org_id", "composite_score"])
    op.create_index("ix_opportunities_status", "optimization_opportunities", ["status"])

    # initiatives
    op.create_table(
        "initiatives",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("backlog", "planned", "in_progress", "review", "done", "cancelled", name="initiativestatus"),
            nullable=False,
            server_default="backlog",
        ),
        sa.Column("sla_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_ref", sa.String(255), nullable=True),
        sa.Column("external_url", sa.String(1000), nullable=True),
        sa.Column("realized_savings_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["optimization_opportunities.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_initiatives_org_id", "initiatives", ["org_id"])

    # initiative_comments
    op.create_table(
        "initiative_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("initiative_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiatives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("initiative_comments")
    op.drop_table("initiatives")
    op.drop_table("optimization_opportunities")
    op.drop_table("connector_health")
    op.drop_table("cloud_accounts")
    op.drop_table("users")
    op.drop_table("organizations")

    for enum in ["userrole", "cloudprovider", "connectorstatus", "opportunitycategory",
                 "risklevel", "effortlevel", "opportunitystatus", "initiativestatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
