from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.settings.schemas import FinOpsSettingsOut, FinOpsSettingsUpdate
from app.domains.settings.service import TenantSettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


async def get_org_id_from_user(
    current_user=Depends(get_current_user),
) -> str:
    """Extract org_id from current user."""
    return str(current_user.org_id)


@router.get(
    "/finops",
    response_model=FinOpsSettingsOut,
    summary="Get FinOps settings for current tenant",
)
async def get_finops_settings(
    org_id: Annotated[str, Depends(get_org_id_from_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinOpsSettingsOut:
    """Return the monitored tag key for this organization."""
    from uuid import UUID

    svc = TenantSettingsService(db)
    tag_key = await svc.get_monitored_tag_key(UUID(org_id))
    return FinOpsSettingsOut(monitored_tag_key=tag_key)


@router.put(
    "/finops",
    response_model=FinOpsSettingsOut,
    summary="Update FinOps settings for current tenant",
)
async def update_finops_settings(
    payload: FinOpsSettingsUpdate,
    org_id: Annotated[str, Depends(get_org_id_from_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinOpsSettingsOut:
    """Update the monitored tag key for this organization."""
    from uuid import UUID

    svc = TenantSettingsService(db)
    await svc.set_monitored_tag_key(UUID(org_id), payload.monitored_tag_key)
    await db.commit()
    return FinOpsSettingsOut(monitored_tag_key=payload.monitored_tag_key)


@router.patch(
    "/finops",
    response_model=FinOpsSettingsOut,
    summary="Partially update FinOps settings",
)
async def patch_finops_settings(
    payload: dict,
    org_id: Annotated[str, Depends(get_org_id_from_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinOpsSettingsOut:
    """Partially update FinOps settings (only monitored_tag_key accepted)."""
    from uuid import UUID

    if "monitored_tag_key" in payload:
        raw_value = payload["monitored_tag_key"]
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monitored_tag_key must be a non-empty string",
            )
        # Validate format
        try:
            FinOpsSettingsUpdate(monitored_tag_key=raw_value)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.errors()[0]["msg"],
            )
        svc = TenantSettingsService(db)
        await svc.set_monitored_tag_key(UUID(org_id), raw_value.strip())
        await db.commit()
        return FinOpsSettingsOut(monitored_tag_key=raw_value.strip())

    # Nothing to update
    svc = TenantSettingsService(db)
    tag_key = await svc.get_monitored_tag_key(UUID(org_id))
    return FinOpsSettingsOut(monitored_tag_key=tag_key)