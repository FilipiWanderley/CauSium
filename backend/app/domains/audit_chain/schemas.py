from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: UUID
    org_id: UUID
    actor_user_id: UUID | None
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditVerificationOut(BaseModel):
    is_valid: bool
    checked_events: int
    broken_event_id: UUID | None = None
    expected_prev_hash: str | None = None
    found_prev_hash: str | None = None


class AuditCheckpointOut(BaseModel):
    id: UUID
    org_id: UUID
    generated_by_user_id: UUID | None
    latest_event_hash: str
    checked_events: int
    snapshot_payload: dict
    snapshot_signature: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditCheckpointVerificationOut(BaseModel):
    checkpoint_id: UUID
    is_signature_valid: bool
    is_chain_valid: bool
    checked_events: int
    latest_event_hash: str
    checkpoint_created_at: datetime


class AuditCheckpointCleanupOut(BaseModel):
    org_id: UUID
    deleted_count: int
    kept_count: int
