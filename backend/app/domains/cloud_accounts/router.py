from __future__ import annotations
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.domains.auth.models import UserRole
from app.domains.cloud_accounts.schemas import (
    CloudAccountCreate,
    CloudAccountOut,
    ConnectorHealthOut,
    ScopeValidationOut,
    SyncStatusOut,
)
from app.domains.cloud_accounts.service import CloudAccountService

router = APIRouter(prefix="/cloud-accounts", tags=["cloud-accounts"])


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


@router.get("", response_model=List[CloudAccountOut])
async def list_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    service = CloudAccountService(db)
    accounts = await service.list_accounts(current_user.org_id)
    return [CloudAccountOut.model_validate(a) for a in accounts]


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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
):
    service = CloudAccountService(db)
    account = await service.get_account(current_user.org_id, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    from app.core.redis import get_redis_pool

    redis = get_redis_pool()
    await redis.lpush("ingestion:queue", str(account_id))
    return SyncStatusOut(account_id=account_id, triggered=True, message="Sync job queued")


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
