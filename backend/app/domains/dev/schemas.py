from __future__ import annotations
from uuid import UUID

from pydantic import BaseModel, Field


class SeedRequest(BaseModel):
    days: int = Field(default=90, ge=30, le=90, description="Number of days of historical data to generate")
    force: bool = Field(default=False, description="Overwrite existing seed data if present")


class SeedResult(BaseModel):
    org_id: UUID
    accounts_created: int
    cost_records: int
    event_records: int
    usage_records: int
    recommendation_records: int
    resource_records: int
    days_seeded: int


class ClearResult(BaseModel):
    org_id: UUID
    cleared: bool


class SeedStatus(BaseModel):
    """ClickHouse row counts per table — use to diagnose missing dashboard data."""
    org_id: UUID
    seeded: bool
    cost_records: int
    event_records: int
    usage_records: int
    recommendation_records: int
    resource_records: int
