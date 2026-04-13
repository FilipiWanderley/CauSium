"""
Add revoked_tokens table for global logout/session revocation
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(), primary_key=True),
        sa.Column("user_id", sa.UUID(), index=True, nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table("revoked_tokens")
