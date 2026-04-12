from __future__ import annotations
from typing import Optional, List
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CloudProvider(str, enum.Enum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"


class ConnectorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider: Mapped[CloudProvider] = mapped_column(Enum(CloudProvider, values_callable=lambda x: [e.value for e in x]), nullable=False)
    # Azure: subscription_id | AWS: account_id | GCP: project_id
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Tenant/directory for Azure
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Fernet-encrypted JSON with SP credentials
    credentials_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ConnectorStatus] = mapped_column(Enum(ConnectorStatus, values_callable=lambda x: [e.value for e in x]), default=ConnectorStatus.PENDING)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # SP-CL03: scope validation result (stamped after successful validate call)
    scopes_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped = relationship("Organization", back_populates="cloud_accounts")
    health_checks: Mapped[list["ConnectorHealth"]] = relationship(
        "ConnectorHealth", back_populates="account", cascade="all, delete-orphan"
    )


class ConnectorHealth(Base):
    __tablename__ = "connector_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("cloud_accounts.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[ConnectorStatus] = mapped_column(Enum(ConnectorStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped[CloudAccount] = relationship("CloudAccount", back_populates="health_checks")


class BlobIngestionCheckpoint(Base):
    __tablename__ = "blob_ingestion_checkpoints"
    __table_args__ = (
        UniqueConstraint("account_id", "checkpoint_key", name="uq_blob_ingestion_account_checkpoint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("cloud_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[CloudProvider] = mapped_column(
        Enum(CloudProvider, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    checkpoint_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    blob_etag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    records_ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
