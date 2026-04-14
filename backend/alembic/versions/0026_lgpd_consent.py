"""Add LGPD consent fields to users table (terms_accepted_at, terms_version)

LGPD Art. 7 / Art. 8 — registro do consentimento do titular e versão dos termos aceitos.
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
