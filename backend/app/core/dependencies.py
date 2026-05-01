from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.policy import SessionContext, build_session_context
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def _get_token_payload(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    """Decode and validate the access token, returning the full JWT payload."""
    try:
        token: str | None = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        else:
            from app.core.config import get_settings

            settings = get_settings()
            token = request.cookies.get(settings.auth_cookie_access_name)

        if not token:
            raise ValueError("Missing access token")

        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        return payload
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_id(
    payload: Annotated[dict, Depends(_get_token_payload)],
) -> UUID:
    return UUID(payload["sub"])


async def get_current_user(
    payload: Annotated[dict, Depends(_get_token_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.domains.auth.models import UserRole, WorkspaceLifecycleState
    from app.domains.auth.service import AuthService
    from app.domains.auth.token_blacklist import is_token_revoked

    user_id = UUID(payload["sub"])
    # "iat" may be absent in tokens issued before this field was added — fall back to epoch 0
    issued_at = datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc)

    if await is_token_revoked(db, user_id, issued_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")

    service = AuthService(db)
    user = await service.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    # PLATFORM_ADMIN bypasses workspace lifecycle enforcement — must still be active themselves.
    if user.role == UserRole.PLATFORM_ADMIN:
        return user

    org = await service.get_org(user.org_id)
    if org and org.lifecycle_state != WorkspaceLifecycleState.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Workspace is {org.lifecycle_state.value}. Contact your administrator.",
        )

    return user


def require_roles(*roles: str):
    async def _check(current_user=Depends(get_current_user)):
        from app.domains.auth.models import UserRole

        # PLATFORM_ADMIN is a super-role that satisfies any role requirement.
        if current_user.role == UserRole.PLATFORM_ADMIN:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {roles}",
            )
        return current_user

    return _check


async def require_platform_admin(current_user=Depends(get_current_user)):
    """Dependency that restricts access exclusively to PLATFORM_ADMIN users."""
    from app.domains.auth.models import UserRole

    if current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )
    return current_user


async def get_session_context(
    x_session_risk: Annotated[str | None, Header()] = None,
    x_maintenance_window: Annotated[str | None, Header()] = None,
    x_geo_velocity_high: Annotated[str | None, Header()] = None,
    x_device_trusted: Annotated[str | None, Header()] = None,
) -> SessionContext:
    return build_session_context(
        session_risk=x_session_risk,
        maintenance_window=x_maintenance_window,
        geo_velocity_high=x_geo_velocity_high,
        device_trusted=x_device_trusted,
    )


@dataclass(slots=True)
class SupportAccessContext:
    actor_user_id: UUID
    effective_org_id: UUID
    support_access_session_id: UUID | None


async def get_support_access_context(
    request: Request,
    current_user=Depends(get_current_user),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    x_support_access_session_id: Annotated[UUID | None, Header(alias="X-Support-Access-Session-Id")] = None,
) -> SupportAccessContext:
    from app.domains.auth.models import UserRole
    from app.domains.admin.service import PlatformAdminService

    actor_user_id = current_user.id
    effective_org_id = current_user.org_id  # may be None for PLATFORM_ADMIN
    support_access_session_id: UUID | None = None

    if x_support_access_session_id is not None:
        if current_user.role != UserRole.PLATFORM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform_admin can use support access sessions.",
            )
        if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Support access is read-only in this MVP.",
            )
        service = PlatformAdminService(db, actor_user_id)
        session = await service.resolve_active_support_access_session(x_support_access_session_id)
        effective_org_id = session.target_org_id
        support_access_session_id = session.id

    request.state.actor_user_id = str(actor_user_id)
    request.state.effective_org_id = str(effective_org_id) if effective_org_id is not None else None
    request.state.support_access_session_id = str(support_access_session_id) if support_access_session_id else None
    return SupportAccessContext(
        actor_user_id=actor_user_id,
        effective_org_id=effective_org_id,
        support_access_session_id=support_access_session_id,
    )


async def get_effective_org_id(
    ctx: Annotated[SupportAccessContext, Depends(get_support_access_context)],
) -> UUID:
    return ctx.effective_org_id
