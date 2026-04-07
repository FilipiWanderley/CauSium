from __future__ import annotations
from typing import Optional, List
import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkspaceLifecycleState(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class UserRole(str, enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    ADMIN = "admin"
    ENGINEER = "engineer"
    FINOPS = "finops"
    EXECUTIVE = "executive"
    VIEWER = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="growth")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    passwordless_only: Mapped[bool] = mapped_column(Boolean, default=False)
    lifecycle_state: Mapped[WorkspaceLifecycleState] = mapped_column(
        Enum(WorkspaceLifecycleState, values_callable=lambda x: [e.value for e in x]),
        default=WorkspaceLifecycleState.ACTIVE,
        nullable=False,
    )
    member_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    cloud_accounts: Mapped[list] = relationship("CloudAccount", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    passkey_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship("Organization", back_populates="users")


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"
    __table_args__ = (UniqueConstraint("user_id", "credential_id", name="uq_passkey_user_credential"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    public_key_jwk: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(default=0)
    transports: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
