"""Notification broker abstractions for SSE slot-change events."""

from __future__ import annotations

import json
from datetime import datetime
from queue import Empty, Full, Queue
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

import redis
from flask import current_app


class NotificationSubscription(Protocol):
    def get(self, timeout: int) -> dict[str, Any] | None:
        ...

    def close(self) -> None:
        ...


class NotificationBroker(Protocol):
    def publish(self, event: dict[str, Any]) -> None:
        ...

    def subscribe(self) -> NotificationSubscription:
        ...


class InMemorySubscription:
    def __init__(self, broker: "InMemoryNotificationBroker", subscriber_id: str, queue: Queue):
        self._broker = broker
        self._subscriber_id = subscriber_id
        self._queue = queue

    def get(self, timeout: int) -> dict[str, Any] | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def close(self) -> None:
        self._broker.unsubscribe(self._subscriber_id)


class InMemoryNotificationBroker:
    """Thread-safe in-memory pub/sub broker for tests and local fallbacks."""

    def __init__(self, queue_size: int = 200):
        self._queue_size = queue_size
        self._subs: dict[str, Queue] = {}
        self._lock = Lock()

    def subscribe(self) -> NotificationSubscription:
        subscriber_id = str(uuid4())
        queue: Queue = Queue(maxsize=self._queue_size)
        with self._lock:
            self._subs[subscriber_id] = queue
        return InMemorySubscription(self, subscriber_id, queue)

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
                try:
                    queue.get_nowait()
                except Exception:
                    pass
                try:
                    queue.put_nowait(event)
                except Exception:
                    pass


class RedisSubscription:
    def __init__(self, pubsub: redis.client.PubSub):
        self._pubsub = pubsub

    def get(self, timeout: int) -> dict[str, Any] | None:
        message = self._pubsub.get_message(timeout=timeout)
        if not message:
            return None
        data = message.get("data")
        if not data:
            return None
        return json.loads(data)

    def close(self) -> None:
        self._pubsub.close()


class RedisNotificationBroker:
    """Redis pub/sub broker for multi-instance SSE fan-out."""

    def __init__(self, redis_url: str, channel: str):
        self._channel = channel
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def publish(self, event: dict[str, Any]) -> None:
        self._client.publish(self._channel, json.dumps(event))

    def subscribe(self) -> NotificationSubscription:
        pubsub = self._client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self._channel)
        return RedisSubscription(pubsub)


def configure_notification_broker(app) -> None:
    backend = app.config.get("NOTIFICATIONS_BACKEND", "redis")
    if backend == "memory":
        broker: NotificationBroker = InMemoryNotificationBroker()
    elif backend == "redis":
        broker = RedisNotificationBroker(
            app.config["REDIS_URL"],
            app.config["NOTIFICATIONS_REDIS_CHANNEL"],
        )
    else:
        raise ValueError(f"Unsupported notifications backend: {backend}")

    app.extensions["notification_broker"] = broker


def get_notification_broker() -> NotificationBroker:
    return current_app.extensions["notification_broker"]


def build_slot_change_event(
    *,
    slot_id: str,
    lot_id: str,
    zone_id: str | None,
    is_occupied: bool,
    event_type: str,
    source: str,
    distance_cm: float | None,
) -> dict[str, Any]:
    return {
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


def publish_notification_event(event: dict[str, Any]) -> None:
    get_notification_broker().publish(event)


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
    publish_notification_event(
        build_slot_change_event(
            slot_id=slot_id,
            lot_id=lot_id,
            zone_id=zone_id,
            is_occupied=is_occupied,
            event_type=event_type,
            source=source,
            distance_cm=distance_cm,
        )
    )
