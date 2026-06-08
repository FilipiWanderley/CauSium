from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import PageParams
from app.domains.business_mapping.models import (
    BusinessAudit,
    BusinessAuditAction,
    BusinessRule,
    BusinessRuleType,
    CriteriaOperator,
)


class BusinessRulesService:
    """Service for managing business mapping rules."""

    def __init__(self, db: AsyncSession, org_id: UUID, user_id: UUID) -> None:
        self.db = db
        self.org_id = org_id
        self.user_id = user_id

    async def list_rules(
        self,
        params: PageParams,
        *,
        is_active: bool | None = None,
        rule_type: BusinessRuleType | None = None,
    ) -> tuple[list[BusinessRule], int]:
        """List business rules with pagination and filtering."""
        filters = [BusinessRule.org_id == self.org_id]

        if is_active is not None:
            filters.append(BusinessRule.is_active == is_active)

        if rule_type is not None:
            filters.append(BusinessRule.rule_type == rule_type)

        count_result = await self.db.execute(
            select(func.count(BusinessRule.id)).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(BusinessRule)
            .where(*filters)
            .order_by(BusinessRule.priority.asc(), BusinessRule.name.asc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(items_result.scalars().all()), total

    async def get_rule(self, rule_id: UUID) -> BusinessRule:
        """Get a single business rule by ID."""
        result = await self.db.execute(
            select(BusinessRule).where(
                and_(
                    BusinessRule.id == rule_id,
                    BusinessRule.org_id == self.org_id,
                )
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Business rule not found")
        return rule

    async def create_rule(
        self,
        name: str,
        rule_type: BusinessRuleType,
        criteria_field: str,
        criteria_operator: CriteriaOperator,
        criteria_value: str,
        destination_team: str,
        *,
        description: str | None = None,
        destination_cost_center: str | None = None,
        priority: int = 100,
    ) -> BusinessRule:
        """Create a new business rule."""
        rule = BusinessRule(
            org_id=self.org_id,
            name=name,
            description=description,
            rule_type=rule_type,
            criteria_field=criteria_field,
            criteria_operator=criteria_operator,
            criteria_value=criteria_value,
            destination_team=destination_team,
            destination_cost_center=destination_cost_center,
            priority=priority,
            created_by=self.user_id,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)

        await self._audit(
            entity_id=rule.id,
            action=BusinessAuditAction.RULE_CREATED,
            new_value=self._rule_to_dict(rule),
        )

        return rule

    async def update_rule(
        self,
        rule_id: UUID,
        **updates: Any,
    ) -> BusinessRule:
        """Update an existing business rule."""
        rule = await self.get_rule(rule_id)

        old_value = self._rule_to_dict(rule)

        for field, value in updates.items():
            if value is not None and hasattr(rule, field):
                setattr(rule, field, value)

        rule.updated_at = datetime.now(timezone.utc)
        rule.updated_by = self.user_id

        await self.db.flush()
        await self.db.refresh(rule)

        await self._audit(
            entity_id=rule.id,
            action=BusinessAuditAction.RULE_UPDATED,
            old_value=old_value,
            new_value=self._rule_to_dict(rule),
        )

        return rule

    async def delete_rule(self, rule_id: UUID) -> None:
        """Delete a business rule."""
        rule = await self.get_rule(rule_id)

        old_value = self._rule_to_dict(rule)

        await self._audit(
            entity_id=rule.id,
            action=BusinessAuditAction.RULE_DELETED,
            old_value=old_value,
        )

        await self.db.delete(rule)
        await self.db.flush()

    async def activate_rule(self, rule_id: UUID) -> BusinessRule:
        """Activate a business rule."""
        rule = await self.get_rule(rule_id)

        if rule.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Rule is already active")

        old_value = self._rule_to_dict(rule)
        rule.is_active = True
        rule.updated_at = datetime.now(timezone.utc)
        rule.updated_by = self.user_id

        await self.db.flush()
        await self.db.refresh(rule)

        await self._audit(
            entity_id=rule.id,
            action=BusinessAuditAction.RULE_ACTIVATED,
            old_value=old_value,
            new_value=self._rule_to_dict(rule),
        )

        return rule

    async def deactivate_rule(self, rule_id: UUID) -> BusinessRule:
        """Deactivate a business rule."""
        rule = await self.get_rule(rule_id)

        if not rule.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Rule is already inactive")

        old_value = self._rule_to_dict(rule)
        rule.is_active = False
        rule.updated_at = datetime.now(timezone.utc)
        rule.updated_by = self.user_id

        await self.db.flush()
        await self.db.refresh(rule)

        await self._audit(
            entity_id=rule.id,
            action=BusinessAuditAction.RULE_DEACTIVATED,
            old_value=old_value,
            new_value=self._rule_to_dict(rule),
        )

        return rule

    async def list_audit_log(
        self,
        params: PageParams,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[BusinessAudit], int]:
        """List audit log entries with filtering."""
        filters = [BusinessAudit.org_id == self.org_id]

        if entity_type is not None:
            filters.append(BusinessAudit.entity_type == entity_type)

        if entity_id is not None:
            filters.append(BusinessAudit.entity_id == entity_id)

        if start_date is not None:
            filters.append(BusinessAudit.created_at >= start_date)

        if end_date is not None:
            filters.append(BusinessAudit.created_at <= end_date)

        count_result = await self.db.execute(
            select(func.count(BusinessAudit.id)).where(*filters)
        )
        total = count_result.scalar_one()

        items_result = await self.db.execute(
            select(BusinessAudit)
            .where(*filters)
            .order_by(BusinessAudit.created_at.desc())
            .limit(params.limit)
            .offset(params.offset)
        )
        return list(items_result.scalars().all()), total

    async def _audit(
        self,
        *,
        entity_id: UUID,
        action: BusinessAuditAction,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
    ) -> None:
        """Create an audit log entry."""
        audit = BusinessAudit(
            org_id=self.org_id,
            entity_type="rule",
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            user_id=self.user_id,
        )
        self.db.add(audit)
        await self.db.flush()

    def _rule_to_dict(self, rule: BusinessRule) -> dict[str, Any]:
        """Convert a rule to a dictionary for audit logging."""
        return {
            "id": str(rule.id),
            "org_id": str(rule.org_id),
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type.value if hasattr(rule.rule_type, "value") else rule.rule_type,
            "criteria_field": rule.criteria_field,
            "criteria_operator": rule.criteria_operator.value if hasattr(rule.criteria_operator, "value") else rule.criteria_operator,
            "criteria_value": rule.criteria_value,
            "destination_team": rule.destination_team,
            "destination_cost_center": rule.destination_cost_center,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "created_by": str(rule.created_by),
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            "updated_by": str(rule.updated_by) if rule.updated_by else None,
        }
