from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.cloud_accounts.models import CloudProvider, ConnectorStatus


class AzureCredentials(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str


class CloudAccountCreate(BaseModel):
    provider: CloudProvider
    external_id: str = Field(..., description="Subscription/Account/Project ID")
    display_name: str = Field(..., min_length=2, max_length=255)
    tenant_id: str | None = None
    azure_credentials: AzureCredentials | None = None


class CloudAccountOut(BaseModel):
    id: UUID
    org_id: UUID
    provider: CloudProvider
    external_id: str
    display_name: str
    tenant_id: str | None
    status: ConnectorStatus
    last_sync_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorHealthOut(BaseModel):
    id: int
    account_id: UUID
    checked_at: datetime
    status: ConnectorStatus
    latency_ms: int | None
    message: str | None

    model_config = {"from_attributes": True}


class SyncStatusOut(BaseModel):
    account_id: UUID
    triggered: bool
    message: str
