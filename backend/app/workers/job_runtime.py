from __future__ import annotations

import json
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerting import AlertSeverity, send_alert
from app.core.logging import get_logger
from app.domains.admin.models import DlqMessage

log = get_logger(__name__)

MAX_RETRIES = 3
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


@dataclass
class QueueJob:
    queue_name: str
    org_id: UUID | None
    account_id: UUID | None
    lookback_days: int | None
    payload: str


def parse_job(queue_name: str, raw_payload: str) -> QueueJob:
    """Parse queue payload supporting both legacy and new formats.

    Legacy format: raw account_id string
    New format: {"org_id": "...", "account_id": "..."}
    """
    try:
        data = json.loads(raw_payload)
        org_id = UUID(data["org_id"]) if data.get("org_id") else None
        account_id = UUID(data["account_id"]) if data.get("account_id") else None
        lookback_days_raw = data.get("lookback_days")
        lookback_days = int(lookback_days_raw) if lookback_days_raw is not None else None
        return QueueJob(
            queue_name=queue_name,
            org_id=org_id,
            account_id=account_id,
            lookback_days=lookback_days,
            payload=raw_payload,
        )
    except Exception:
        try:
            account_id = UUID(raw_payload)
        except Exception:
            # Best-effort fallback for malformed JSON payloads that still contain a UUID.
            match = UUID_PATTERN.search(raw_payload)
            account_id = UUID(match.group(0)) if match else None
        return QueueJob(
            queue_name=queue_name,
            org_id=None,
            account_id=account_id,
            lookback_days=None,
            payload=raw_payload,
        )


def retry_key(queue_name: str, payload: str) -> str:
    return f"retry:{queue_name}:{payload}"


async def push_to_dlq(
    db: AsyncSession,
    *,
    queue_name: str,
    payload: str,
    org_id: UUID | None,
    account_id: UUID | None,
    error_message: str,
    retry_count: int,
) -> DlqMessage:
    msg = DlqMessage(
        queue_name=queue_name,
        org_id=org_id,
        account_id=account_id,
        original_payload=payload,
        error_message=error_message,
        retry_count=retry_count,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    log.error(
        "worker.dlq.pushed",
        queue_name=queue_name,
        dlq_id=str(msg.id),
        org_id=str(org_id) if org_id else None,
        account_id=str(account_id) if account_id else None,
        retry_count=retry_count,
    )
    send_alert(
        subject=f"Job moved to DLQ: {queue_name}",
        body=(
            f"A job in queue '{queue_name}' exhausted retries ({retry_count}) and was moved to the DLQ.\n"
            f"Error: {error_message[:300]}\n"
            f"Org: {org_id}, Account: {account_id}"
        ),
        severity=AlertSeverity.HIGH,
        source=f"worker.dlq.{queue_name}",
        context={"queue_name": queue_name, "dlq_id": str(msg.id), "retry_count": retry_count},
    )
    return msg
