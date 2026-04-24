from __future__ import annotations
import asyncio
import json
from datetime import date, timedelta
from typing import Annotated, List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.idempotency import build_fingerprint, build_scope_key, prepare_request, store_response
from app.core.redis import get_redis_pool
from app.core.schemas import Page, PageParams
from app.domains.auth.models import UserRole
from app.domains.notifications.models import AlertCategory, AlertSeverity
from app.domains.notifications.service import NotificationsService
from app.domains.cloud_accounts.schemas import (
    CloudAccountCreate,
    CloudAccountOut,
    ConnectorSyncStatusOut,
    ConnectorHealthOut,
    ScopeValidationOut,
    SyncStatusOut,
)
from app.domains.cloud_accounts.service import CloudAccountService
from app.core.logging import get_logger

router = APIRouter(prefix="/cloud-accounts", tags=["cloud-accounts"])
log = get_logger(__name__)


async def _run_inline_sync_pipeline(org_id: UUID, account_id: UUID, lookback_days: int) -> None:
    from app.domains.cloud_ledger.service import CloudLedgerService
    from app.domains.decision_engine.service import DecisionEngineService

    async with async_session_factory() as db:
        account_service = CloudAccountService(db)
        account = await account_service.get_account(org_id, account_id)
        if not account:
            log.warning(
                "cloud_account.inline_sync.account_not_found",
                org_id=str(org_id),
                account_id=str(account_id),
            )
            return

        end = date.today()
        start = end - timedelta(days=lookback_days)
        ledger = CloudLedgerService(db)
        result = await ledger.ingest_account(org_id, account_id, start, end)

        opportunities_generated = 0
        try:
            decision_engine = DecisionEngineService(db)
            opportunities = await decision_engine.generate_opportunities_for_account(org_id, account_id)
            opportunities_generated = len(opportunities)
        except Exception as exc:
            log.warning(
                "cloud_account.inline_sync.scoring_failed",
                org_id=str(org_id),
                account_id=str(account_id),
                error=str(exc),
            )

        await NotificationsService(db).create_realtime_alert(
            org_id=org_id,
            category=AlertCategory.ACTIVITY,
            severity=AlertSeverity.INFO if result.status == "ok" else AlertSeverity.WARNING,
            event_type="cloud_account.sync.completed" if result.status == "ok" else "cloud_account.sync.warning",
            title=f"Sync finished for {account.display_name}",
            body=(
                f"Costs: {result.cost_records}, events: {result.event_records}, inventory: {result.inventory_records}, opportunities: {opportunities_generated}"
                if result.status == "ok"
                else (result.message or "Sync finished with partial errors.")
            ),
            source_type="cloud_account_sync",
            source_id=f"{account_id}:{lookback_days}:inline",
            extra_metadata={
                "account_id": str(account_id),
                "provider": account.provider.value if hasattr(account.provider, "value") else str(account.provider),
                "lookback_days": lookback_days,
                "mode": "inline",
            },
        )
        await db.commit()


@router.post("", response_model=CloudAccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    req: CloudAccountCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = CloudAccountService(db)
    try:
        account = await service.create_account(current_user.org_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await service.audit_create(current_user.org_id, current_user.id, account)
    return CloudAccountOut.model_validate(account)


@router.get("", response_model=Page[CloudAccountOut])
async def list_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    page_params: PageParams = Depends(PageParams),
):
    service = CloudAccountService(db)
    accounts, total = await service.list_accounts(
        current_user.org_id, limit=page_params.limit, offset=page_params.offset
    )
    return Page.of([CloudAccountOut.model_validate(a) for a in accounts], total, page_params)


@router.get("/sync-status", response_model=List[ConnectorSyncStatusOut])
async def get_sync_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = CloudAccountService(db)
    return await service.list_sync_status(current_user.org_id)


@router.get("/{account_id}", response_model=CloudAccountOut)
async def get_account(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = CloudAccountService(db)
    account = await service.get_account(current_user.org_id, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return CloudAccountOut.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    service = CloudAccountService(db)
    deleted = await service.delete_account(current_user.org_id, account_id, actor_user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")


@router.post("/{account_id}/health-check", response_model=ConnectorHealthOut)
async def run_health_check(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = CloudAccountService(db)
    account = await service.get_account(current_user.org_id, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    health = await service.run_health_check(account)
    return ConnectorHealthOut.model_validate(health)


@router.get("/{account_id}/health", response_model=List[ConnectorHealthOut])
async def get_health_history(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = CloudAccountService(db)
    history = await service.get_health_history(account_id)
    return [ConnectorHealthOut.model_validate(h) for h in history]


@router.post("/{account_id}/sync", response_model=SyncStatusOut)
async def trigger_sync(
    account_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
    lookback_days: int = Query(default=90, ge=7, le=90),
    sync_mode: Literal["queued", "inline"] = Query(default="inline"),
):
    service = CloudAccountService(db)
    account = await service.get_account(current_user.org_id, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    redis = get_redis_pool()

    scope_key = None
    if idempotency_key:
        scope_key = build_scope_key(
            org_id=current_user.org_id,
            user_id=current_user.id,
            operation="cloud_accounts.sync",
            resource_id=account_id,
            idempotency_key=idempotency_key,
        )
        state, cached = await prepare_request(
            redis,
            scope_key=scope_key,
            fingerprint=build_fingerprint(request.method, request.url.path, await request.body()),
        )
        if state == "replay" and cached is not None:
            return JSONResponse(status_code=cached["status_code"], content=cached["payload"])
        if state == "conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key already used with a different request payload",
            )
        if state == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request with this Idempotency-Key is still being processed",
            )

    if sync_mode == "inline":
        asyncio.create_task(
            _run_inline_sync_pipeline(current_user.org_id, account_id, lookback_days)
        )
        out = SyncStatusOut(
            account_id=account_id,
            triggered=True,
            message=f"Sync started inline ({lookback_days} days).",
        )
    else:
        payload = json.dumps(
            {
                "org_id": str(current_user.org_id),
                "account_id": str(account_id),
                "lookback_days": lookback_days,
            }
        )
        await redis.lpush("ingestion:queue", payload)
        await NotificationsService(db).create_realtime_alert(
            org_id=current_user.org_id,
            category=AlertCategory.ACTIVITY,
            severity=AlertSeverity.INFO,
            event_type="cloud_account.sync.queued",
            title=f"Sync queued for {account.display_name}",
            body=f"Ingestion requested for last {lookback_days} days.",
            source_type="cloud_account_sync",
            source_id=f"{account_id}:{lookback_days}",
            extra_metadata={
                "account_id": str(account_id),
                "provider": account.provider.value if hasattr(account.provider, "value") else str(account.provider),
                "lookback_days": lookback_days,
                "mode": "queued",
            },
        )
        out = SyncStatusOut(
            account_id=account_id,
            triggered=True,
            message=f"Sync job queued ({lookback_days} days)",
        )
    if scope_key:
        await store_response(
            redis,
            scope_key=scope_key,
            status_code=status.HTTP_200_OK,
            payload=out.model_dump(mode="json"),
        )
    return out


@router.post("/{account_id}/validate", response_model=ScopeValidationOut)
async def validate_account_scopes(
    account_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    """SP-CL03: Validate minimum credential scopes before operational usage."""
    service = CloudAccountService(db)
    account = await service.get_account(current_user.org_id, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    result = await service.validate_account_scopes(account)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.message)

    return ScopeValidationOut(
        account_id=account.id,
        provider=account.provider,
        ok=True,
        message=result.message,
        validated_scopes=result.validated_scopes,
        scopes_validated_at=account.scopes_validated_at,
    )
