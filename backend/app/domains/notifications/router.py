from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.notifications.models import AlertCategory, AlertStatus
from app.domains.notifications.schemas import (
    AlertRecordOut,
    NotificationSlackConfigOut,
    NotificationSlackConfigUpdate,
    AlertStatusPatch,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    NotificationsNewOut,
    UnreadCountOut,
)
from app.domains.notifications.service import NotificationsService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> UnreadCountOut:
    svc = NotificationsService(db)
    counts = await svc.unread_count(current_user.org_id, current_user.id)
    return UnreadCountOut(**counts)


@router.get("", response_model=Page[AlertRecordOut])
async def list_notifications(
    category: Optional[AlertCategory] = Query(default=None),
    status: Optional[AlertStatus] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> Page[AlertRecordOut]:
    svc = NotificationsService(db)
    alerts, total = await svc.list(
        org_id=current_user.org_id,
        user_id=current_user.id,
        category=category,
        status=status,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([AlertRecordOut.model_validate(a) for a in alerts], total, page_params)


@router.get("/new", response_model=NotificationsNewOut)
async def list_new_notifications(
    category: Optional[AlertCategory] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> NotificationsNewOut:
    svc = NotificationsService(db)
    counts = await svc.unread_count(
        org_id=current_user.org_id,
        user_id=current_user.id,
        category=category,
    )
    alerts, total = await svc.list(
        org_id=current_user.org_id,
        user_id=current_user.id,
        category=category,
        status=AlertStatus.UNREAD,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return NotificationsNewOut(
        unread=counts["unread"],
        critical=counts["critical"],
        total=total,
        items=[AlertRecordOut.model_validate(a) for a in alerts],
    )


@router.patch("/mark-all-read", response_model=dict)
async def mark_all_read(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    svc = NotificationsService(db)
    affected = await svc.mark_all_read(current_user.org_id, current_user.id)
    return {"marked_read": affected}


@router.patch("/{alert_id}", response_model=AlertRecordOut)
async def patch_alert(
    alert_id: UUID,
    body: AlertStatusPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> AlertRecordOut:
    svc = NotificationsService(db)
    alert = await svc.set_status(current_user.org_id, alert_id, body.status)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return AlertRecordOut.model_validate(alert)


@router.get("/preferences", response_model=NotificationPreferenceOut)
async def get_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> NotificationPreferenceOut:
    svc = NotificationsService(db)
    pref = await svc.get_preference(current_user.org_id, current_user.id)
    return NotificationPreferenceOut.model_validate(pref)


@router.put("/preferences", response_model=NotificationPreferenceOut)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> NotificationPreferenceOut:
    svc = NotificationsService(db)
    pref = await svc.upsert_preference(
        org_id=current_user.org_id,
        user_id=current_user.id,
        in_app_enabled=body.in_app_enabled,
        email_enabled=body.email_enabled,
        slack_enabled=body.slack_enabled,
        frequency=body.frequency,
        categories=body.categories,
    )
    return NotificationPreferenceOut.model_validate(pref)


@router.get("/slack-config", response_model=NotificationSlackConfigOut)
async def get_slack_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
) -> NotificationSlackConfigOut:
    svc = NotificationsService(db)
    cfg = await svc.get_slack_config(current_user.org_id)
    return NotificationSlackConfigOut(
        enabled=cfg.enabled,
        webhook_configured=bool(cfg.webhook_encrypted),
    )


@router.put("/slack-config", response_model=NotificationSlackConfigOut)
async def update_slack_config(
    body: NotificationSlackConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
) -> NotificationSlackConfigOut:
    svc = NotificationsService(db)
    try:
        cfg = await svc.upsert_slack_config(
            org_id=current_user.org_id,
            enabled=body.enabled,
            webhook_url=body.webhook_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return NotificationSlackConfigOut(
        enabled=cfg.enabled,
        webhook_configured=bool(cfg.webhook_encrypted),
    )
