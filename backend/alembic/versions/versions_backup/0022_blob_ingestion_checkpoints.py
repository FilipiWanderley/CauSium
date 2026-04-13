"""blob ingestion checkpoints for idempotent cloud export ingestion

Revision ID: 0022_blob_ingestion_checkpoints
Revises: 0021_workspace_keyrings
Create Date: 2026-04-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0022_blob_ingestion_checkpoints"
down_revision = "0021_workspace_keyrings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blob_ingestion_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Enum("azure", "aws", "gcp", name="cloudprovider"), nullable=False),
        sa.Column("checkpoint_key", sa.String(length=1024), nullable=False),
        sa.Column("blob_name", sa.String(length=1024), nullable=False),
        sa.Column("blob_etag", sa.String(length=255), nullable=True),
        sa.Column("records_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "checkpoint_key", name="uq_blob_ingestion_account_checkpoint"),
    )
    op.create_index(
        op.f("ix_blob_ingestion_checkpoints_org_id"),
        "blob_ingestion_checkpoints",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_blob_ingestion_checkpoints_account_id"),
        "blob_ingestion_checkpoints",
        ["account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_blob_ingestion_checkpoints_account_id"), table_name="blob_ingestion_checkpoints")
    op.drop_index(op.f("ix_blob_ingestion_checkpoints_org_id"), table_name="blob_ingestion_checkpoints")
    op.drop_table("blob_ingestion_checkpoints")
