from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domains.cloud_accounts.models import CloudProvider, ConnectorStatus, SubscriptionStatus


class AzureCredentials(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    storage_account_url: str = Field(..., min_length=10)
    cost_export_container: str = Field(..., min_length=1)
    cost_export_prefix: str = Field(..., min_length=1)
    cost_export_format: str = Field(default="auto", pattern="^(auto|csv|parquet)$")


class AwsCredentials(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str | None = None
    region: str | None = "us-east-1"
    cur_bucket: str | None = None
    cur_prefix: str | None = None


class GcpCredentials(BaseModel):
    service_account_json: str | None = None
    project_id: str
    use_workload_identity: bool = False
    billing_export_table: str | None = None
    logging_filter: str | None = None

    @model_validator(mode="after")
    def validate_auth_source(self) -> "GcpCredentials":
        if not self.use_workload_identity and not self.service_account_json:
            raise ValueError(
                "Provide service_account_json or enable use_workload_identity for GCP credentials"
            )
        return self


class CloudAccountCreate(BaseModel):
    provider: CloudProvider
    external_id: str = Field(..., description="Subscription/Account/Project ID")
    display_name: str = Field(..., min_length=2, max_length=255)
    tenant_id: str | None = None
    azure_credentials: AzureCredentials | None = None
    aws_credentials: AwsCredentials | None = None
    gcp_credentials: GcpCredentials | None = None

    @model_validator(mode="after")
    def validate_provider_payload(self) -> "CloudAccountCreate":
        if self.provider == CloudProvider.AZURE and not self.azure_credentials:
            raise ValueError("azure_credentials is required when provider is azure")
        if self.provider == CloudProvider.AWS and not self.aws_credentials:
            raise ValueError("aws_credentials is required when provider is aws")
        if self.provider == CloudProvider.GCP and not self.gcp_credentials:
            raise ValueError("gcp_credentials is required when provider is gcp")
        return self


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


class ConnectorSyncStatusOut(BaseModel):
    account_id: UUID
    provider: CloudProvider
    display_name: str
    connector_status: ConnectorStatus
    last_sync_at: datetime | None
    last_health_check_at: datetime | None
    open_dlq_count: int
    needs_attention: bool


class ScopeValidationOut(BaseModel):
    account_id: UUID
    provider: CloudProvider
    ok: bool
    message: str
    validated_scopes: list[str] = []
    scopes_validated_at: datetime | None = None


class CloudAccountSubscriptionOut(BaseModel):
    id: UUID
    org_id: UUID
    cloud_account_id: UUID
    provider: CloudProvider
    cloud_tenant_id: str | None
    subscription_id: str
    subscription_name: str | None
    display_name: str | None
    status: SubscriptionStatus
    discovered_at: datetime
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class SubscriptionListOut(BaseModel):
    items: list[CloudAccountSubscriptionOut]
    total: int
