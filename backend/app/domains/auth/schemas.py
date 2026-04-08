from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.domains.auth.models import UserRole


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER


class UserOut(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    passkey_enabled: bool
    must_change_password: bool
    created_at: datetime
    org_name: str = ""

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)


class PasswordlessPolicyUpdate(BaseModel):
    passwordless_only: bool


class PasswordlessPolicyOut(BaseModel):
    org_id: UUID
    passwordless_only: bool


class PasskeyRegistrationOptionsRequest(BaseModel):
    display_name: str | None = None


class PasskeyRegistrationOptionsOut(BaseModel):
    challenge: str
    rp_id: str
    rp_name: str
    user_id: str
    user_name: str
    user_display_name: str
    timeout_ms: int = 60000


class PasskeyRegistrationVerifyRequest(BaseModel):
    challenge: str
    credential_id: str
    public_key_jwk: dict
    client_data_json: str
    authenticator_data: str
    attestation_object: str | None = None
    transports: list[str] | None = None
    sign_count: int = 0


class PasskeyLoginOptionsRequest(BaseModel):
    email: EmailStr


class PasskeyLoginOptionsOut(BaseModel):
    challenge: str
    rp_id: str
    allow_credentials: list[str]
    timeout_ms: int = 60000


class PasskeyLoginVerifyRequest(BaseModel):
    email: EmailStr
    challenge: str
    credential_id: str
    client_data_json: str
    authenticator_data: str
    signature: str
    user_handle: str | None = None
    sign_count: int = 0


class PasskeyCredentialOut(BaseModel):
    id: UUID
    credential_id: str
    transports: list[str] = []
    sign_count: int
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


# ── Password reset ──────────────────────────────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Token returned directly for dev convenience (no email service configured).
    In production, this token would be delivered via email and NOT included here.
    """

    token: str
    message: str = (
        "If this email is registered you will receive reset instructions. "
        "In development the token is returned in this response."
    )


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Authenticated user changing their own password (satisfies must_change_password)."""

    current_password: str
    new_password: str = Field(..., min_length=8)


# ── SP-U01: admin reset another user's password ─────────────────────────────


class AdminResetPasswordResponse(BaseModel):
    """One-time response containing the temporary password set by an admin.

    The ``temporary_password`` is returned exactly once so the calling admin
    can communicate it to the target user out-of-band.  The user will be forced
    to change it on next login (``must_change_password=True``).
    """

    temporary_password: str
    user: UserOut


class AdminResetMFAResponse(BaseModel):
    """Response for admin-initiated MFA reset on a target user.

    In the current passkey-first model, MFA reset revokes all registered
    passkey credentials from the target account and disables passkey login
    until the user re-registers new credentials.
    """

    revoked_passkeys: int
    user: UserOut


class AdminDeactivateUserRequest(BaseModel):
    """SP-U05: Reason payload for admin-driven user deactivation."""

    reason: str = Field(..., min_length=3, max_length=500)
