"""policy bundle and decision evidence

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_bundles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=30), nullable=False, server_default="1.0.0"),
        sa.Column("engine", sa.String(length=30), nullable=False, server_default="internal-pbac-abac"),
        sa.Column("rules", JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_bundles_org_id", "policy_bundles", ["org_id"])

    op.create_table(
        "policy_decision_evidences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("policy_bundle_id", sa.UUID(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("session_context", JSONB(), nullable=False),
        sa.Column("policy_decision_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_bundle_id"], ["policy_bundles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_decision_id"),
    )
    op.create_index("ix_policy_decision_evidences_org_id", "policy_decision_evidences", ["org_id"])
    op.create_index("ix_policy_decision_evidences_policy_bundle_id", "policy_decision_evidences", ["policy_bundle_id"])
    op.create_index("ix_policy_decision_evidences_actor_user_id", "policy_decision_evidences", ["actor_user_id"])
    op.create_index("ix_policy_decision_evidences_action", "policy_decision_evidences", ["action"])
    op.create_index("ix_policy_decision_evidences_policy_decision_id", "policy_decision_evidences", ["policy_decision_id"])


def downgrade() -> None:
    op.drop_table("policy_decision_evidences")
    op.drop_table("policy_bundles")
