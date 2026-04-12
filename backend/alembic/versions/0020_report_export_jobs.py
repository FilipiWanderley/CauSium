"""report export jobs

Revision ID: 0020_report_export_jobs
Revises: 0019_auth_totp_mfa
Create Date: 2026-04-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0020_report_export_jobs"
down_revision = "0019_auth_totp_mfa"
branch_labels = None
depends_on = None


_REPORT_TYPE_ENUM = sa.Enum("summary", name="economicsreporttype")
_FILE_FORMAT_ENUM = sa.Enum("csv", "xlsx", name="reportexportformat")
_STATUS_ENUM = sa.Enum("queued", "running", "completed", "failed", name="reportexportstatus")


def upgrade() -> None:
    op.create_table(
        "report_export_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("report_type", _REPORT_TYPE_ENUM, nullable=False, server_default="summary"),
        sa.Column("file_format", _FILE_FORMAT_ENUM, nullable=False, server_default="csv"),
        sa.Column("status", _STATUS_ENUM, nullable=False, server_default="queued"),
        sa.Column("window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_export_jobs_org_id"), "report_export_jobs", ["org_id"], unique=False)
    op.create_index(op.f("ix_report_export_jobs_requested_by_user_id"), "report_export_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_report_export_jobs_status"), "report_export_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_report_export_jobs_created_at"), "report_export_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_export_jobs_created_at"), table_name="report_export_jobs")
    op.drop_index(op.f("ix_report_export_jobs_status"), table_name="report_export_jobs")
    op.drop_index(op.f("ix_report_export_jobs_requested_by_user_id"), table_name="report_export_jobs")
    op.drop_index(op.f("ix_report_export_jobs_org_id"), table_name="report_export_jobs")
    op.drop_table("report_export_jobs")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
    _FILE_FORMAT_ENUM.drop(op.get_bind(), checkfirst=True)
    _REPORT_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)