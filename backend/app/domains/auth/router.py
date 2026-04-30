from __future__ import annotations
from typing import Annotated, List
from urllib.parse import quote_plus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.security import decode_token
from app.domains.auth.models import UserRole
from app.domains.auth.schemas import (
    AdminDeactivateUserRequest,
    UserUpdate,
    UserDeleteAudit,
    AdminResetMFAResponse,
    AdminResetPasswordResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    PasswordlessPolicyOut,
    PasswordlessPolicyUpdate,
    PasskeyCredentialOut,
    PasskeyLoginOptionsOut,
    PasskeyLoginOptionsRequest,
    PasskeyLoginVerifyRequest,
    PasskeyRegistrationOptionsOut,
    PasskeyRegistrationOptionsRequest,
    PasskeyRegistrationVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    TOTPCodeRequest,
    TOTPEnableResponse,
    TOTPSetupOut,
    TOTPStatusOut,
    TOTPVerifyResponse,
    UserCreate,
    UserOut,
)
from app.core.schemas import Page, PageParams
from app.domains.auth.service import AuthService
from app.domains.auth.token_blacklist import revoke_all_tokens_for_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT, summary="Logout global (revoga todas as sessões)")
async def logout_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    await revoke_all_tokens_for_user(db, current_user.id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response


# --- PATCH membro ---
@router.patch("/users/{user_id}", response_model=UserOut, summary="Admin edita membro")
async def admin_update_user(
    user_id: UUID,
    req: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
):
    service = AuthService(db)
    user = await service.admin_update_user(current_user, user_id, req)
    org_name = await service.get_org_name(user.org_id)
    return _user_out(user, org_name)


# --- DELETE membro (soft) ---
@router.delete("/users/{user_id}", response_model=UserOut, summary="Admin remove membro (soft-delete)")
async def admin_delete_user(
    user_id: UUID,
    req: UserDeleteAudit,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
):
    service = AuthService(db)
    user = await service.admin_delete_user(current_user, user_id, req.reason)
    org_name = await service.get_org_name(user.org_id)
    return _user_out(user, org_name)


def _user_out(user, org_name: str) -> UserOut:
    from datetime import datetime, timezone

    return UserOut(
        id=user.id,
        org_id=user.org_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        passkey_enabled=user.passkey_enabled,
        totp_enabled=getattr(user, "totp_enabled", False),
        must_change_password=getattr(user, "must_change_password", False),
        created_at=user.created_at or datetime.now(timezone.utc),
        org_name=org_name,
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    cookie_secure = settings.auth_cookie_secure_effective
    cookie_domain = settings.auth_cookie_domain or None

    response.set_cookie(
        key=settings.auth_cookie_access_name,
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_cookie_path,
        domain=cookie_domain,
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key=settings.auth_cookie_refresh_name,
        value=refresh_token,
        httponly=True,
        secure=cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_cookie_path,
        domain=cookie_domain,
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    cookie_domain = settings.auth_cookie_domain or None
    response.delete_cookie(
        key=settings.auth_cookie_access_name,
        path=settings.auth_cookie_path,
        domain=cookie_domain,
    )
    response.delete_cookie(
        key=settings.auth_cookie_refresh_name,
        path=settings.auth_cookie_path,
        domain=cookie_domain,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário e workspace",
    description="Cria um novo workspace e usuário inicial. Retorna tokens de acesso e refresh, além dos dados do usuário."
)
async def register(req: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    try:
        org, user = await service.register(req)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    _, access, refresh = await service.login(req.email, req.password)
    payload = TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user, org.name))
    response = Response(content=payload.model_dump_json(), media_type="application/json", status_code=status.HTTP_201_CREATED)
    _set_auth_cookies(response, access, refresh)
    return response


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login do usuário",
    description="Realiza login com email, senha e opcionalmente código TOTP. Retorna tokens de acesso e refresh, além dos dados do usuário."
)
async def login(req: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    try:
        user, access, refresh = await service.login(req.email, req.password, req.totp_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    org_name = await service.get_org_name(user.org_id)
    payload = TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user, org_name))
    response = Response(content=payload.model_dump_json(), media_type="application/json")
    _set_auth_cookies(response, access, refresh)
    return response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar tokens de autenticação",
    description="Gera novos tokens de acesso e refresh a partir de um refresh token válido."
)
async def refresh(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    req: RefreshRequest | None = None,
):
    service = AuthService(db)
    try:
        settings = get_settings()
        cookie_refresh = request.cookies.get(settings.auth_cookie_refresh_name)
        refresh_token = req.refresh_token if req else cookie_refresh
        if not refresh_token:
            raise ValueError("Missing refresh token")
        access, new_refresh = await service.refresh_tokens(refresh_token)
        payload = decode_token(access)
        user = await service.get_user_by_id(UUID(payload["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    org_name = await service.get_org_name(user.org_id)
    body = TokenResponse(access_token=access, refresh_token=new_refresh, user=_user_out(user, org_name))
    response = Response(content=body.model_dump_json(), media_type="application/json")
    _set_auth_cookies(response, access, new_refresh)
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout da sessão atual",
    description="Remove os cookies de autenticação do usuário na sessão atual."
)
async def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response


@router.get(
    "/me",
    response_model=UserOut,
    summary="Obter dados do usuário autenticado",
    description="Retorna os dados do usuário atualmente autenticado."
)
async def me(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    org_name = await service.get_org_name(current_user.org_id)
    return _user_out(current_user, org_name)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    service = AuthService(db)
    user = await service.create_user(current_user.org_id, req)
    org_name = await service.get_org_name(user.org_id)
    return _user_out(user, org_name)


@router.get("/users", response_model=Page[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
    page_params: PageParams = Depends(PageParams),
):
    service = AuthService(db)
    users, total = await service.list_org_users(
        current_user.org_id, limit=page_params.limit, offset=page_params.offset
    )
    org_name = await service.get_org_name(current_user.org_id)
    return Page.of([_user_out(u, org_name) for u in users], total, page_params)


@router.patch("/passwordless-policy", response_model=PasswordlessPolicyOut)
async def update_passwordless_policy(
    req: PasswordlessPolicyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    service = AuthService(db)
    org = await service.update_passwordless_policy(current_user.org_id, req.passwordless_only)
    return PasswordlessPolicyOut(org_id=org.id, passwordless_only=org.passwordless_only)


@router.post("/passkey/register/options", response_model=PasskeyRegistrationOptionsOut)
async def passkey_register_options(
    req: PasskeyRegistrationOptionsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    settings = get_settings()
    challenge = await service.begin_passkey_registration(current_user)
    display_name = req.display_name or current_user.full_name
    return PasskeyRegistrationOptionsOut(
        challenge=challenge,
        rp_id=settings.passkey_rp_id,
        rp_name=settings.passkey_rp_name,
        user_id=str(current_user.id),
        user_name=current_user.email,
        user_display_name=display_name,
    )


@router.post("/passkey/register/verify", status_code=status.HTTP_204_NO_CONTENT)
async def passkey_register_verify(
    req: PasskeyRegistrationVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    try:
        await service.verify_passkey_registration(
            current_user,
            challenge=req.challenge,
            credential_id=req.credential_id,
            public_key_jwk=req.public_key_jwk,
            client_data_json=req.client_data_json,
            authenticator_data=req.authenticator_data,
            attestation_object=req.attestation_object,
            transports=req.transports,
            sign_count=req.sign_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/passkey/login/options", response_model=PasskeyLoginOptionsOut)
async def passkey_login_options(
    req: PasskeyLoginOptionsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    settings = get_settings()
    try:
        _, challenge, credential_ids = await service.begin_passkey_login(req.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return PasskeyLoginOptionsOut(
        challenge=challenge,
        rp_id=settings.passkey_rp_id,
        allow_credentials=credential_ids,
    )


@router.post("/passkey/login/verify", response_model=TokenResponse)
async def passkey_login_verify(
    req: PasskeyLoginVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(db)
    try:
        user, access, refresh = await service.verify_passkey_login(
            email=req.email,
            challenge=req.challenge,
            credential_id=req.credential_id,
            client_data_json=req.client_data_json,
            authenticator_data=req.authenticator_data,
            signature=req.signature,
            sign_count=req.sign_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    org_name = await service.get_org_name(user.org_id)
    payload = TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user, org_name))
    response = Response(content=payload.model_dump_json(), media_type="application/json")
    _set_auth_cookies(response, access, refresh)
    return response


@router.get("/passkeys", response_model=List[PasskeyCredentialOut])
async def list_passkeys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    passkeys = await service.list_user_passkeys(current_user)
    return [
        PasskeyCredentialOut(
            id=p.id,
            credential_id=p.credential_id,
            transports=[t for t in (p.transports or "").split(",") if t],
            sign_count=p.sign_count,
            created_at=p.created_at,
            last_used_at=p.last_used_at,
        )
        for p in passkeys
    ]


@router.delete("/passkeys/{passkey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_passkey(
    passkey_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = AuthService(db)
    try:
        await service.revoke_user_passkey(current_user, passkey_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/oidc/azure/start")
async def azure_oidc_start(db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    try:
        url = service.build_azure_oidc_start_url()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/oidc/azure/callback")
async def azure_oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    settings = get_settings()
    service = AuthService(db)
    response = RedirectResponse(url=settings.frontend_url + "/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    try:
        _, access, refresh = await service.login_with_azure_oidc_callback(code=code, state=state)
        _set_auth_cookies(response, access, refresh)
        response.headers["Location"] = f"{settings.frontend_url}/app/dashboard"
    except ValueError as e:
        response.headers["Location"] = f"{settings.frontend_url}/login?oidc_error={quote_plus(str(e))}"
    return response


# ── Password reset ────────────────────────────────────────────────────────


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Initiate a password-reset flow.

    Always returns 200 to prevent user enumeration.

    When SMTP is configured, the token is delivered out-of-band via email and
    omitted from the response body. When SMTP is disabled, the token is
    returned for local development convenience.
    """
    service = AuthService(db)
    token = await service.request_password_reset(req.email)
    if service.email.enabled:
        return ForgotPasswordResponse(token=None)
    return ForgotPasswordResponse(token=token)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    req: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete a password-reset using the token received via forgot-password."""
    service = AuthService(db)
    try:
        await service.reset_password(req.token, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ── SP-A01: Forced / voluntary password change ───────────────────────────


@router.post("/change-password", response_model=UserOut)
async def change_password(
    req: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    """Authenticated user changes their own password.

    Clears the ``must_change_password`` flag on success.  The updated
    ``UserOut`` is returned so the frontend can refresh its auth state
    without an extra round-trip.
    """
    service = AuthService(db)
    try:
        user = await service.change_password(
            current_user,
            req.current_password,
            req.new_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    org_name = await service.get_org_name(user.org_id)
    return _user_out(user, org_name)


@router.get("/mfa/totp/status", response_model=TOTPStatusOut)
async def totp_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPStatusOut:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    return TOTPStatusOut(enabled=bool(user and user.totp_enabled))


@router.post("/mfa/totp/setup", response_model=TOTPSetupOut)
async def totp_setup(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPSetupOut:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    secret, otpauth_url = await service.begin_totp_setup(user)
    return TOTPSetupOut(secret=secret, otpauth_url=otpauth_url)


@router.post("/mfa/totp/verify", response_model=TOTPVerifyResponse)
async def totp_verify(
    req: TOTPCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPVerifyResponse:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    valid = await service.verify_totp_code(user, req.code)
    return TOTPVerifyResponse(valid=valid)


@router.post("/mfa/totp/enable", response_model=TOTPEnableResponse)
async def totp_enable(
    req: TOTPCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPEnableResponse:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    try:
        user, backup_codes = await service.enable_totp(user, req.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return TOTPEnableResponse(enabled=user.totp_enabled, backup_codes=backup_codes)


@router.get("/mfa/totp/backup-codes/count", response_model=TOTPStatusOut)
async def totp_backup_codes_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPStatusOut:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    remaining = await service.backup_codes_remaining(user)
    return TOTPStatusOut(enabled=bool(user and user.totp_enabled), backup_codes_remaining=remaining)


@router.post("/mfa/totp/backup-codes/regenerate", response_model=TOTPEnableResponse)
async def totp_backup_codes_regenerate(
    req: TOTPCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPEnableResponse:
    """Regenera backup codes (requer código TOTP válido). Invalida todos os anteriores."""
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    if not user or not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not enabled")
    if not await service._verify_totp_code_for_user(user, req.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")
    backup_codes = await service.generate_backup_codes(user)
    return TOTPEnableResponse(enabled=True, backup_codes=backup_codes)


@router.post("/mfa/totp/disable", response_model=TOTPStatusOut)
async def totp_disable(
    req: TOTPCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TOTPStatusOut:
    service = AuthService(db)
    user = await service.get_user_by_id(current_user.id)
    try:
        user = await service.disable_totp(user, req.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return TOTPStatusOut(enabled=user.totp_enabled)


# ── SP-U01 + SP-U03: Admin-initiated reset of another user's password ────


@router.post(
    "/users/{user_id}/reset-password",
    response_model=AdminResetPasswordResponse,
    summary="Admin resets another user's password",
    responses={
        403: {"description": "Caller outranked or cross-admin violation (SP-U03)"},
        404: {"description": "Target user not found"},
    },
)
async def admin_reset_password(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(
        require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)
    ),
):
    """Admin generates a secure temporary password for *user_id*.

    The target user is forced to change it on next login
    (``must_change_password=True``).  The temporary password is returned
    exactly once — the calling admin is responsible for delivering it
    to the user out-of-band (email, Slack, etc.).

    **SP-U03**: An ``admin`` may only reset passwords of roles that are
    strictly below ``admin`` in the hierarchy (engineer, finops, executive,
    viewer).  Attempting to reset another ``admin`` or a ``platform_admin``
    returns **403**.
    """
    service = AuthService(db)
    try:
        target, temp_password = await service.admin_reset_password(current_user, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    org_name = await service.get_org_name(target.org_id)
    return AdminResetPasswordResponse(
        temporary_password=temp_password,
        user=_user_out(target, org_name),
    )


@router.post(
    "/users/{user_id}/reset-mfa",
    response_model=AdminResetMFAResponse,
    summary="Admin resets another user's MFA",
    responses={
        403: {"description": "Caller outranked or cross-admin violation (SP-U03)"},
        404: {"description": "Target user not found"},
    },
)
async def admin_reset_mfa(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
):
    """Admin revokes all MFA credentials from *user_id*.

    In the current passkey-first auth model, this removes all registered
    passkeys from the target account and disables passkey login until the
    user re-registers credentials.
    """
    service = AuthService(db)
    try:
        target, revoked_count, totp_disabled = await service.admin_reset_mfa(current_user, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    org_name = await service.get_org_name(target.org_id)
    return AdminResetMFAResponse(
        revoked_passkeys=revoked_count,
        totp_disabled=totp_disabled,
        user=_user_out(target, org_name),
    )


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=UserOut,
    summary="Admin deactivates a user",
    responses={
        403: {"description": "Caller outranked or forbidden by hierarchy"},
        404: {"description": "Target user not found"},
        409: {"description": "Target user already inactive"},
    },
)
async def admin_deactivate_user(
    user_id: UUID,
    req: AdminDeactivateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
):
    """SP-U05: Soft-deactivate member access while preserving user record."""
    service = AuthService(db)
    try:
        target = await service.admin_deactivate_user(current_user, user_id, req.reason)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        detail = str(e)
        if detail == "User is already inactive":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from e
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from e
    org_name = await service.get_org_name(target.org_id)
    return _user_out(target, org_name)


# --- LGPD: exportação de dados pessoais ---
@router.get(
    "/me/export",
    summary="LGPD Art. 18 — Exportar dados pessoais do titular",
)
async def export_my_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    """Retorna todos os dados pessoais do usuário autenticado em formato JSON."""
    service = AuthService(db)
    return await service.export_user_data(current_user)


# --- LGPD: exclusão/anonimização de dados pessoais ---
@router.delete(
    "/me/data",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="LGPD Art. 18 VI — Direito ao esquecimento (anonimização dos dados pessoais)",
)
async def delete_my_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    response: Response = None,
):
    """Anonimiza e remove dados pessoais do usuário. Ação irreversível."""
    service = AuthService(db)
    await service.lgpd_purge_user(current_user, current_user.id)
    # Limpar cookies de sessão após purge
    r = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(r)
    return r


@router.delete(
    "/users/{user_id}/data",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="LGPD Art. 18 VI — Admin anonimiza dados de membro",
)
async def admin_delete_user_data(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
):
    """Admin anonimiza dados pessoais de um membro do workspace. Ação irreversível."""
    service = AuthService(db)
    try:
        await service.lgpd_purge_user(current_user, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)
