from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def build_fingerprint(method: str, path: str, body: bytes) -> str:
    raw = b"|".join([
        method.upper().encode("utf-8"),
        path.encode("utf-8"),
        body,
    ])
    return hashlib.sha256(raw).hexdigest()


def build_scope_key(*, org_id: Any, user_id: Any, operation: str, resource_id: Optional[Any], idempotency_key: str) -> str:
    resource_part = str(resource_id) if resource_id is not None else "-"
    return f"idemp:{org_id}:{user_id}:{operation}:{resource_part}:{idempotency_key}"


async def prepare_request(redis, *, scope_key: str, fingerprint: str, ttl_seconds: int = 24 * 60 * 60) -> tuple[str, Optional[dict[str, Any]]]:
    req_key = f"{scope_key}:req"
    resp_key = f"{scope_key}:resp"

    try:
        existing_fingerprint = await redis.get(req_key)
        if existing_fingerprint is None:
            locked = await redis.set(req_key, fingerprint, nx=True, ex=ttl_seconds)
            if locked:
                return "new", None
            existing_fingerprint = await redis.get(req_key)

        if existing_fingerprint != fingerprint:
            return "conflict", None

        cached = await redis.get(resp_key)
        if cached:
            return "replay", json.loads(cached)

        return "in_progress", None
    except Exception:
        # Fail-open: Redis instability must not block critical mutations.
        return "new", None


async def store_response(
    redis,
    *,
    scope_key: str,
    status_code: int,
    payload: dict[str, Any],
    ttl_seconds: int = 24 * 60 * 60,
) -> None:
    if status_code >= 500:
        return
    resp_key = f"{scope_key}:resp"
    envelope = {
        "status_code": status_code,
        "payload": payload,
    }
    try:
        await redis.set(resp_key, json.dumps(envelope, sort_keys=True), ex=ttl_seconds)
    except Exception:
        # Fail-open: mutation was already processed; cache write is best-effort.
        return
