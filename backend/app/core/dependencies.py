from __future__ import annotations
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.policy import SessionContext, build_session_context
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
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
        return UUID(payload["sub"])
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.domains.auth.models import UserRole, WorkspaceLifecycleState
    from app.domains.auth.service import AuthService

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
