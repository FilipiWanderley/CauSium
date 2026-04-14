"""merge all heads: workspace lifecycle, main chain and provider sync

Revision ID: 0025_merge_workspace_lifecycle
Revises: 0008, 0023_aws_cur_ingestion_checkpoints, provider_recommendation_sync
Create Date: 2026-04-12 00:00:00.000000
"""
from typing import Sequence, Union

revision: str = "0025_merge_workspace_lifecycle"
down_revision: Union[str, Sequence[str], None] = (
    "0008",
    "0023_aws_cur_ingestion_checkpoints",
    "provider_recommendation_sync",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
