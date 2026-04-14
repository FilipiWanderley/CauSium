"""workspace keyrings per org

Revision ID: 0021_workspace_keyrings
Revises: 0020_report_export_jobs
Create Date: 2026-04-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0021_workspace_keyrings"
down_revision = "0020_report_export_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_keyrings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("key_material_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "key_version", name="uq_workspace_keyrings_org_key_version"),
    )
    op.create_index(op.f("ix_workspace_keyrings_org_id"), "workspace_keyrings", ["org_id"], unique=False)
    op.create_index(op.f("ix_workspace_keyrings_is_active"), "workspace_keyrings", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_keyrings_is_active"), table_name="workspace_keyrings")
    op.drop_index(op.f("ix_workspace_keyrings_org_id"), table_name="workspace_keyrings")
    op.drop_table("workspace_keyrings")
