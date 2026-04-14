from __future__ import annotations

from datetime import datetime
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
    ActivityEventCreate,
    ActivityEventOut,
    AlertRecordOut,
    NotificationAlertRuleOut,
    NotificationAlertRuleUpdate,
    NotificationSlackConfigOut,
    NotificationSlackConfigUpdate,
    AlertStatusPatch,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    UnreadCountOut,
)
from app.domains.notifications.service import NotificationsService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/rules/{category}", response_model=NotificationAlertRuleOut)
async def get_alert_rule(
    category: AlertCategory,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
) -> NotificationAlertRuleOut:
    svc = NotificationsService(db)
    rule = await svc.get_alert_rule(current_user.org_id, category)
    return NotificationAlertRuleOut.model_validate(rule)


@router.put("/rules/{category}", response_model=NotificationAlertRuleOut)
async def upsert_alert_rule(
    category: AlertCategory,
    body: NotificationAlertRuleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLATFORM_ADMIN)),
) -> NotificationAlertRuleOut:
    svc = NotificationsService(db)
    rule = await svc.upsert_alert_rule(
        org_id=current_user.org_id,
        category=category,
        enabled=body.enabled,
        min_severity=body.min_severity,
        event_type_prefix=body.event_type_prefix,
    )
    return NotificationAlertRuleOut.model_validate(rule)


@router.post("/activity-events", response_model=ActivityEventOut, status_code=status.HTTP_201_CREATED)
async def create_activity_event(
    req: ActivityEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER, UserRole.PLATFORM_ADMIN)),
) -> ActivityEventOut:
    svc = NotificationsService(db)
    event = await svc.create_activity_event(
        org_id=current_user.org_id,
        provider=req.provider,
        event_type=req.event_type,
        severity=req.severity,
        title=req.title,
        body=req.body,
        service=req.service,
        resource_id=req.resource_id,
        account_id=req.account_id,
        extra_metadata=req.extra_metadata,
        occurred_at=req.occurred_at,
    )
    return ActivityEventOut.model_validate(event)


@router.get("/activity-events", response_model=Page[ActivityEventOut])
async def list_activity_events(
    event_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    service: Optional[str] = Query(default=None),
    occurred_from: Optional[datetime] = Query(default=None),
    occurred_to: Optional[datetime] = Query(default=None),
    page_params: PageParams = Depends(PageParams),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user=Depends(get_current_user),
) -> Page[ActivityEventOut]:
    svc = NotificationsService(db)
    items, total = await svc.list_activity_events(
        org_id=current_user.org_id,
        event_type=event_type,
        resource_id=resource_id,
        service=service,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=page_params.limit,
        offset=page_params.offset,
    )
    return Page.of([ActivityEventOut.model_validate(e) for e in items], total, page_params)


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    category: Optional[AlertCategory] = Query(default=None),
) -> UnreadCountOut:
    svc = NotificationsService(db)
    counts = await svc.unread_count(
        org_id=current_user.org_id,
        user_id=current_user.id,
        category=category,
    )
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
