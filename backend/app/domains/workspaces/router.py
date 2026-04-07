from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.domains.audit_chain.service import AuditChainService
from app.domains.auth.models import UserRole, WorkspaceLifecycleState
from app.domains.auth.service import AuthService
from app.domains.workspaces.schemas import WorkspaceLifecycleUpdate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# Valid lifecycle state transitions
_ALLOWED_TRANSITIONS: dict[WorkspaceLifecycleState, set[WorkspaceLifecycleState]] = {
    WorkspaceLifecycleState.ACTIVE: {WorkspaceLifecycleState.SUSPENDED},
    WorkspaceLifecycleState.SUSPENDED: {WorkspaceLifecycleState.ACTIVE, WorkspaceLifecycleState.ARCHIVED},
    WorkspaceLifecycleState.ARCHIVED: set(),
}


@router.get("/me", response_model=WorkspaceOut)
async def get_my_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
):
    """Return lifecycle details of the caller's workspace."""
    service = AuthService(db)
    org = await service.get_org(current_user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceOut.model_validate(org)


@router.put("/{org_id}/status", response_model=WorkspaceOut)
async def update_workspace_status(
    org_id: UUID,
    req: WorkspaceLifecycleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(require_roles(UserRole.ADMIN)),
):
    """Transition a workspace lifecycle state (ADMIN only).

    Allowed transitions:
        ACTIVE → SUSPENDED
        SUSPENDED → ACTIVE | ARCHIVED
        ARCHIVED → (terminal, no transitions)
    """
    service = AuthService(db)
    org = await service.get_org(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Admins can only manage their own org
    if org.id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to manage this workspace")

    allowed = _ALLOWED_TRANSITIONS.get(org.lifecycle_state, set())
    if req.lifecycle_state not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transition from '{org.lifecycle_state.value}' to '{req.lifecycle_state.value}' is not allowed. "
                f"Allowed targets: {[s.value for s in allowed] or 'none (terminal state)'}."
            ),
        )

    if req.lifecycle_state == WorkspaceLifecycleState.SUSPENDED:
        if not req.reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A reason is required when suspending a workspace.",
            )
        org.suspended_at = datetime.now(timezone.utc)
        org.suspended_reason = req.reason
    else:
        org.suspended_at = None
        org.suspended_reason = None

    prev_state = org.lifecycle_state.value
    org.lifecycle_state = req.lifecycle_state
    await db.flush()
    await db.refresh(org)

    audit = AuditChainService(db)
    await audit.append_event(
        org_id=org.id,
        actor_user_id=current_user.id,
        event_type="workspace.lifecycle_changed",
        entity_type="organization",
        entity_id=str(org.id),
        payload={
            "from": prev_state,
            "to": req.lifecycle_state.value,
            "reason": req.reason,
        },
    )

    return WorkspaceOut.model_validate(org)
