"""In-memory event broadcaster for SSE notifications."""

from __future__ import annotations

from datetime import datetime
from queue import Full, Queue
from threading import Lock
from typing import Any
from uuid import uuid4


class EventBroadcaster:
    """Thread-safe in-memory pub/sub broadcaster."""

    def __init__(self, queue_size: int = 200):
        self._queue_size = queue_size
        self._subs: dict[str, Queue] = {}
        self._lock = Lock()

    def subscribe(self) -> tuple[str, Queue]:
        subscriber_id = str(uuid4())
        queue: Queue = Queue(maxsize=self._queue_size)
        with self._lock:
            self._subs[subscriber_id] = queue
        return subscriber_id, queue

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subs.pop(subscriber_id, None)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            queues = list(self._subs.values())

        for queue in queues:
            try:
                queue.put_nowait(event)
            except Full:
                # If a subscriber falls behind, drop oldest and enqueue newest.
                try:
                    queue.get_nowait()
                except Exception:
                    pass
                try:
                    queue.put_nowait(event)
                except Exception:
                    pass


broadcaster = EventBroadcaster()


def publish_slot_change(
    *,
    slot_id: str,
    lot_id: str,
    zone_id: str | None,
    is_occupied: bool,
    event_type: str,
    source: str,
    distance_cm: float | None,
) -> None:
    """Publish normalized slot-change notification payload."""
    broadcaster.publish(
        {
            "type": "slot_change",
            "slot_id": slot_id,
            "lot_id": lot_id,
            "zone_id": zone_id,
            "is_occupied": is_occupied,
            "event_type": event_type,
            "source": source,
            "distance_cm": distance_cm,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
