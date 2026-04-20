from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID


class NotificationRealtimeBroker:
    """In-process pub/sub for workspace notification events.

    This is intentionally lightweight and works well for single-node deployment.
    For horizontal scaling, replace with Redis pub/sub or a dedicated event bus.
    """

    def __init__(self) -> None:
        self._queues_by_org: dict[UUID, set[asyncio.Queue[dict]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, org_id: UUID) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._queues_by_org.setdefault(org_id, set()).add(queue)
        return queue

    async def unsubscribe(self, org_id: UUID, queue: asyncio.Queue[dict]) -> None:
        async with self._lock:
            queues = self._queues_by_org.get(org_id)
            if not queues:
                return
            queues.discard(queue)
            if not queues:
                self._queues_by_org.pop(org_id, None)

    async def publish(self, org_id: UUID, event: dict) -> None:
        async with self._lock:
            queues = list(self._queues_by_org.get(org_id, set()))
        if not queues:
            return

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Keep stream healthy under burst: drop oldest and enqueue latest.
                try:
                    _ = queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # If still full, skip this subscriber.
                    pass

    @staticmethod
    def heartbeat() -> dict:
        return {
            "type": "heartbeat",
            "ts": datetime.now(timezone.utc).isoformat(),
        }


notifications_realtime_broker = NotificationRealtimeBroker()
