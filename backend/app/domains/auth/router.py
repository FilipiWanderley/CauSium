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
    TokenResponse,
    UserCreate,
    UserOut,
)
from app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user, org_name: str) -> UserOut:
    data = UserOut.model_validate(user)
    data.org_name = org_name
    return data


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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
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


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    service = AuthService(db)
    try:
        user, access, refresh = await service.login(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    org_name = await service.get_org_name(user.org_id)
    payload = TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user, org_name))
    response = Response(content=payload.model_dump_json(), media_type="application/json")
    _set_auth_cookies(response, access, refresh)
    return response


@router.post("/refresh", response_model=TokenResponse)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserOut)
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


@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    service = AuthService(db)
    users = await service.list_org_users(current_user.org_id)
    org_name = await service.get_org_name(current_user.org_id)
    return [_user_out(u, org_name) for u in users]


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
        response.headers["Location"] = f"{settings.frontend_url}/dashboard"
    except ValueError as e:
        response.headers["Location"] = f"{settings.frontend_url}/login?oidc_error={quote_plus(str(e))}"
    return response
