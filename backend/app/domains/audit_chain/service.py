from __future__ import annotations
import hashlib
import hmac
import json
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domains.audit_chain.models import AuditChainCheckpoint, AuditChainEvent
from app.domains.audit_chain.schemas import AuditCheckpointVerificationOut, AuditVerificationOut


class AuditChainService:
    GENESIS_HASH = "GENESIS"

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _canonical_payload(payload: dict) -> str:
        normalized = AuditChainService._normalize_payload(payload)
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _normalize_payload(payload):
        if isinstance(payload, dict):
            return {str(k): AuditChainService._normalize_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [AuditChainService._normalize_payload(v) for v in payload]
        if isinstance(payload, tuple):
            return [AuditChainService._normalize_payload(v) for v in payload]
        if isinstance(payload, UUID):
            return str(payload)
        if isinstance(payload, datetime):
            return payload.isoformat()
        if isinstance(payload, Enum):
            return payload.value
        return payload

    @staticmethod
    def _build_hash(
        *,
        prev_hash: str,
        org_id: UUID,
        actor_user_id: UUID | None,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict,
        created_at: datetime,
    ) -> str:
        canonical_payload = AuditChainService._canonical_payload(payload)
        actor_value = str(actor_user_id) if actor_user_id else "system"
        base = "|".join(
            [
                prev_hash,
                str(org_id),
                actor_value,
                event_type,
                entity_type,
                entity_id,
                canonical_payload,
                created_at.isoformat(),
            ]
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    async def _latest_for_org(self, org_id: UUID) -> AuditChainEvent | None:
        result = await self.db.execute(
            select(AuditChainEvent)
            .where(AuditChainEvent.org_id == org_id)
            .order_by(AuditChainEvent.created_at.desc(), AuditChainEvent.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def append_event(
        self,
        *,
        org_id: UUID,
        actor_user_id: UUID | None,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict,
    ) -> AuditChainEvent:
        normalized_payload = self._normalize_payload(payload)
        latest = await self._latest_for_org(org_id)
        prev_hash = latest.event_hash if latest else self.GENESIS_HASH
        created_at = datetime.now(timezone.utc)
        event_hash = self._build_hash(
            prev_hash=prev_hash,
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=normalized_payload,
            created_at=created_at,
        )
        event = AuditChainEvent(
            org_id=org_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=normalized_payload,
            prev_hash=prev_hash,
            event_hash=event_hash,
            created_at=created_at,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def list_events(
        self,
        org_id: UUID,
        *,
        event_type: str | None = None,
        event_prefix: str | None = None,
        entity_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditChainEvent]:
        q = select(AuditChainEvent).where(AuditChainEvent.org_id == org_id)
        if event_type:
            q = q.where(AuditChainEvent.event_type == event_type)
        if event_prefix:
            q = q.where(AuditChainEvent.event_type.like(f"{event_prefix}%"))
        if entity_type:
            q = q.where(AuditChainEvent.entity_type == entity_type)
        if created_after:
            q = q.where(AuditChainEvent.created_at >= created_after)
        if created_before:
            q = q.where(AuditChainEvent.created_at <= created_before)
        q = q.order_by(AuditChainEvent.created_at.desc(), AuditChainEvent.id.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def export_events_jsonl(
        self,
        org_id: UUID,
        *,
        event_type: str | None = None,
        event_prefix: str | None = None,
        entity_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> str:
        events = await self.list_events(
            org_id,
            event_type=event_type,
            event_prefix=event_prefix,
            entity_type=entity_type,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )
        lines = []
        for e in events:
            lines.append(
                json.dumps(
                    {
                        "id": str(e.id),
                        "org_id": str(e.org_id),
                        "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                        "event_type": e.event_type,
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id,
                        "payload": e.payload,
                        "prev_hash": e.prev_hash,
                        "event_hash": e.event_hash,
                        "created_at": e.created_at.isoformat(),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        return "\n".join(lines) + ("\n" if lines else "")

    async def verify_chain(self, org_id: UUID) -> AuditVerificationOut:
        result = await self.db.execute(
            select(AuditChainEvent)
            .where(AuditChainEvent.org_id == org_id)
            .order_by(AuditChainEvent.created_at.asc(), AuditChainEvent.id.asc())
        )
        events = list(result.scalars().all())
        prev_hash = self.GENESIS_HASH
        checked_events = 0
        for event in events:
            expected_hash = self._build_hash(
                prev_hash=prev_hash,
                org_id=event.org_id,
                actor_user_id=event.actor_user_id,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                payload=event.payload,
                created_at=event.created_at,
            )
            checked_events += 1
            if event.prev_hash != prev_hash:
                return AuditVerificationOut(
                    is_valid=False,
                    checked_events=checked_events,
                    broken_event_id=event.id,
                    expected_prev_hash=prev_hash,
                    found_prev_hash=event.prev_hash,
                )
            if event.event_hash != expected_hash:
                return AuditVerificationOut(
                    is_valid=False,
                    checked_events=checked_events,
                    broken_event_id=event.id,
                    expected_prev_hash=expected_hash,
                    found_prev_hash=event.event_hash,
                )
            prev_hash = event.event_hash
        return AuditVerificationOut(is_valid=True, checked_events=checked_events)

    @staticmethod
    def _sign_snapshot(snapshot_payload: dict) -> str:
        settings = get_settings()
        canonical = AuditChainService._canonical_payload(snapshot_payload).encode("utf-8")
        return hmac.new(settings.secret_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

    async def create_checkpoint(self, org_id: UUID, generated_by_user_id: UUID | None) -> AuditChainCheckpoint:
        verification = await self.verify_chain(org_id)
        if not verification.is_valid:
            raise ValueError("Cannot checkpoint invalid audit chain")
        latest = await self._latest_for_org(org_id)
        latest_event_hash = latest.event_hash if latest else self.GENESIS_HASH
        count_result = await self.db.execute(select(func.count(AuditChainEvent.id)).where(AuditChainEvent.org_id == org_id))
        checked_events = int(count_result.scalar() or 0)
        now = datetime.now(timezone.utc)
        snapshot_payload = {
            "org_id": str(org_id),
            "checked_events": checked_events,
            "latest_event_hash": latest_event_hash,
            "verified_at": now.isoformat(),
        }
        signature = self._sign_snapshot(snapshot_payload)
        checkpoint = AuditChainCheckpoint(
            org_id=org_id,
            generated_by_user_id=generated_by_user_id,
            latest_event_hash=latest_event_hash,
            checked_events=checked_events,
            snapshot_payload=snapshot_payload,
            snapshot_signature=signature,
            created_at=now,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        await self.db.refresh(checkpoint)
        return checkpoint

    async def list_checkpoints(self, org_id: UUID, *, limit: int = 100, offset: int = 0) -> list[AuditChainCheckpoint]:
        result = await self.db.execute(
            select(AuditChainCheckpoint)
            .where(AuditChainCheckpoint.org_id == org_id)
            .order_by(AuditChainCheckpoint.created_at.desc(), AuditChainCheckpoint.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_checkpoint(self, org_id: UUID, checkpoint_id: UUID) -> AuditChainCheckpoint | None:
        result = await self.db.execute(
            select(AuditChainCheckpoint).where(
                AuditChainCheckpoint.org_id == org_id,
                AuditChainCheckpoint.id == checkpoint_id,
            )
        )
        return result.scalar_one_or_none()

    async def verify_checkpoint(self, org_id: UUID, checkpoint_id: UUID) -> AuditCheckpointVerificationOut:
        checkpoint = await self.get_checkpoint(org_id, checkpoint_id)
        if not checkpoint:
            raise ValueError("Checkpoint not found")
        expected_signature = self._sign_snapshot(checkpoint.snapshot_payload)
        is_signature_valid = hmac.compare_digest(expected_signature, checkpoint.snapshot_signature)
        chain_verification = await self.verify_chain(org_id)
        return AuditCheckpointVerificationOut(
            checkpoint_id=checkpoint.id,
            is_signature_valid=is_signature_valid,
            is_chain_valid=chain_verification.is_valid,
            checked_events=checkpoint.checked_events,
            latest_event_hash=checkpoint.latest_event_hash,
            checkpoint_created_at=checkpoint.created_at,
        )

    async def cleanup_checkpoints(self, org_id: UUID, keep_last: int) -> tuple[int, int]:
        keep_last = max(1, keep_last)
        checkpoints = await self.list_checkpoints(org_id, limit=5000, offset=0)
        if len(checkpoints) <= keep_last:
            return 0, len(checkpoints)
        to_delete = checkpoints[keep_last:]
        for cp in to_delete:
            await self.db.delete(cp)
        await self.db.flush()
        return len(to_delete), keep_last

    async def generate_checkpoints_for_all_orgs(self, *, keep_last: int) -> dict:
        org_rows = await self.db.execute(select(AuditChainEvent.org_id).distinct())
        org_ids = [row[0] for row in org_rows.all() if row[0] is not None]
        created = 0
        cleaned = 0
        for org_id in org_ids:
            try:
                await self.create_checkpoint(org_id, None)
                created += 1
            except ValueError:
                pass
            deleted, _ = await self.cleanup_checkpoints(org_id, keep_last=keep_last)
            cleaned += deleted
        await self.db.commit()
        return {"org_count": len(org_ids), "created_checkpoints": created, "deleted_checkpoints": cleaned}
