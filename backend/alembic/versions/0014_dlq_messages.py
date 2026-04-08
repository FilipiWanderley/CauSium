"""SP-WK01: DLQ messages table for failed worker jobs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dlq_status = sa.Enum("open", "requeued", "resolved", name="dlqstatus")

    op.create_table(
        "dlq_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("queue_name", sa.String(length=100), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("original_payload", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", dlq_status, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dlq_messages_queue_name"), "dlq_messages", ["queue_name"], unique=False)
    op.create_index(op.f("ix_dlq_messages_org_id"), "dlq_messages", ["org_id"], unique=False)
    op.create_index(op.f("ix_dlq_messages_account_id"), "dlq_messages", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dlq_messages_account_id"), table_name="dlq_messages")
    op.drop_index(op.f("ix_dlq_messages_org_id"), table_name="dlq_messages")
    op.drop_index(op.f("ix_dlq_messages_queue_name"), table_name="dlq_messages")
    op.drop_table("dlq_messages")
    sa.Enum("open", "requeued", "resolved", name="dlqstatus").drop(op.get_bind(), checkfirst=True)
