"""Add LGPD consent fields to users table (terms_accepted_at, terms_version)

LGPD Art. 7 / Art. 8 — registro do consentimento do titular e versão dos termos aceitos.

Revision ID: 0026
Revises: 0025_merge_workspace_lifecycle
Create Date: 2026-04-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0026"
down_revision: Union[str, Sequence[str], None] = "0025_merge_workspace_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
