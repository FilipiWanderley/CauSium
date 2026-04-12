"""
Alembic migration for ProviderRecommendation and SyncRecord tables
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from uuid import uuid4

revision = 'provider_recommendation_sync'
down_revision = '0023_aws_cur_ingestion_checkpoints'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'provider_recommendations',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('org_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('external_id', sa.String(128), nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('short_description', sa.String(512), nullable=False),
        sa.Column('impact_level', sa.String(32), nullable=True),
        sa.Column('annual_savings_usd', sa.Float, nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='open'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'sync_records',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('org_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('records_processed', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
    )

def downgrade():
    op.drop_table('provider_recommendations')
    op.drop_table('sync_records')
