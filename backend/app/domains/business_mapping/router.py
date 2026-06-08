from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.schemas import Page, PageParams
from app.domains.business_mapping.models import BusinessRuleType
from app.domains.business_mapping.schemas import (
    BusinessRuleCreate,
    BusinessRuleOut,
    BusinessRuleUpdate,
)
from app.domains.business_mapping.service import BusinessRulesService

router = APIRouter(prefix="/business/rules", tags=["business-mapping"])


@router.get(
    "",
    response_model=Page[BusinessRuleOut],
    summary="List business rules",
)
async def list_business_rules(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
    params: Annotated[PageParams, Depends(PageParams)],
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    rule_type: BusinessRuleType | None = Query(default=None, description="Filter by rule type"),
) -> Page[BusinessRuleOut]:
    """List all business rules for the current organization."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    items, total = await svc.list_rules(params, is_active=is_active, rule_type=rule_type)
    return Page.of(items, total, params)


@router.get(
    "/{rule_id}",
    response_model=BusinessRuleOut,
    summary="Get a business rule",
)
async def get_business_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
) -> BusinessRuleOut:
    """Get a single business rule by ID."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    rule = await svc.get_rule(rule_id)
    return BusinessRuleOut.model_validate(rule)


@router.post(
    "",
    response_model=BusinessRuleOut,
    status_code=201,
    summary="Create a business rule",
)
async def create_business_rule(
    payload: BusinessRuleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
) -> BusinessRuleOut:
    """Create a new business rule."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    rule = await svc.create_rule(
        name=payload.name,
        rule_type=payload.rule_type,
        criteria_field=payload.criteria_field,
        criteria_operator=payload.criteria_operator,
        criteria_value=payload.criteria_value,
        destination_team=payload.destination_team,
        description=payload.description,
        destination_cost_center=payload.destination_cost_center,
        priority=payload.priority,
    )
    await db.commit()
    return BusinessRuleOut.model_validate(rule)


@router.put(
    "/{rule_id}",
    response_model=BusinessRuleOut,
    summary="Update a business rule",
)
async def update_business_rule(
    rule_id: UUID,
    payload: BusinessRuleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
) -> BusinessRuleOut:
    """Update an existing business rule."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    rule = await svc.update_rule(rule_id, **updates)
    await db.commit()
    return BusinessRuleOut.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=204,
    summary="Delete a business rule",
)
async def delete_business_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
):
    """Delete a business rule."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    await svc.delete_rule(rule_id)
    await db.commit()


@router.post(
    "/{rule_id}/activate",
    response_model=BusinessRuleOut,
    summary="Activate a business rule",
)
async def activate_business_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
) -> BusinessRuleOut:
    """Activate a business rule."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    rule = await svc.activate_rule(rule_id)
    await db.commit()
    return BusinessRuleOut.model_validate(rule)


@router.post(
    "/{rule_id}/deactivate",
    response_model=BusinessRuleOut,
    summary="Deactivate a business rule",
)
async def deactivate_business_rule(
    rule_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[object, Depends(get_current_user)],
) -> BusinessRuleOut:
    """Deactivate a business rule."""
    svc = BusinessRulesService(db, current_user.org_id, current_user.id)
    rule = await svc.deactivate_rule(rule_id)
    await db.commit()
    return BusinessRuleOut.model_validate(rule)
