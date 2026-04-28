from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

# Renders as JSONB on PostgreSQL (GIN-indexable), JSON on SQLite and other dialects.
JSONB = JSON().with_variant(PG_JSONB(), "postgresql")
