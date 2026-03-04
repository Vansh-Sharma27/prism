"""MQTT service for receiving slot telemetry from sensors/simulator."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC_PATTERN = "prism/+/slot/+"  # prism/{lot_id}/slot/{slot_id}
HEARTBEAT_TOPIC_PATTERN = "prism/+/heartbeat"

# Sensor threshold (cm) - below this = occupied
OCCUPANCY_THRESHOLD = float(os.getenv("PRISM_OCCUPANCY_THRESHOLD_CM", 15))


class MQTTService:
    """Handles MQTT connection lifecycle and sensor message processing."""

    def __init__(self, app=None):
        self.app = app
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.reconnect_min_delay = max(1, int(os.getenv("MQTT_RECONNECT_MIN_DELAY", 1)))
        self.reconnect_max_delay = max(
            self.reconnect_min_delay,
            int(os.getenv("MQTT_RECONNECT_MAX_DELAY", 30)),
        )
        self._reconnect_attempt = 0

        self.client.reconnect_delay_set(
            min_delay=self.reconnect_min_delay,
            max_delay=self.reconnect_max_delay,
        )

        self.client.on_connect = self._on_connect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _next_backoff_seconds(self) -> int:
        return min(
            self.reconnect_max_delay,
            self.reconnect_min_delay * (2 ** max(0, self._reconnect_attempt - 1)),
        )

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Called when connected to MQTT broker."""
        self._reconnect_attempt = 0
        logger.info(
            "MQTT connected | reason_code=%s broker=%s port=%s",
            reason_code,
            MQTT_BROKER,
            MQTT_PORT,
        )
        client.subscribe(MQTT_TOPIC_PATTERN)
        client.subscribe(HEARTBEAT_TOPIC_PATTERN)
        logger.info(
            "MQTT subscribed | slot_topic=%s heartbeat_topic=%s",
            MQTT_TOPIC_PATTERN,
            HEARTBEAT_TOPIC_PATTERN,
        )

    def _on_connect_fail(self, client, userdata):
        """Called when client connection attempt fails."""
        self._reconnect_attempt += 1
        logger.warning(
            "MQTT connect failed | reconnect_attempt=%s next_backoff_seconds=%s broker=%s port=%s",
            self._reconnect_attempt,
            self._next_backoff_seconds(),
            MQTT_BROKER,
            MQTT_PORT,
        )

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Called when disconnected from MQTT broker."""
        if reason_code == 0:
            logger.info("MQTT disconnected cleanly")
            return

        self._reconnect_attempt += 1
        logger.warning(
            "MQTT disconnected unexpectedly | reason_code=%s reconnect_attempt=%s next_backoff_seconds=%s broker=%s port=%s",
            reason_code,
            self._reconnect_attempt,
            self._next_backoff_seconds(),
            MQTT_BROKER,
            MQTT_PORT,
        )

    def _on_message(self, client, userdata, msg):
        """Process incoming MQTT messages."""
        topic_parts = msg.topic.split("/")

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("MQTT payload parse failure | topic=%s error=%s", msg.topic, exc)
            return

        try:
            if len(topic_parts) == 3 and topic_parts[2] == "heartbeat":
                lot_id = topic_parts[1]
                self._handle_heartbeat(lot_id, payload)
                return

            if len(topic_parts) == 4 and topic_parts[2] == "slot":
                lot_id = topic_parts[1]
                slot_topic_id = topic_parts[3]
                self._handle_slot_update(lot_id, slot_topic_id, payload)
                return

            logger.warning("MQTT topic pattern mismatch | topic=%s", msg.topic)
        except Exception:
            logger.exception("MQTT message processing failed | topic=%s", msg.topic)

    def _resolve_slot_db_id(self, lot_id: str, slot_topic_id: str) -> str:
        if slot_topic_id.startswith(f"{lot_id}-"):
            return slot_topic_id
        return f"{lot_id}-{slot_topic_id}"

    def _handle_slot_update(self, lot_id: str, slot_topic_id: str, payload: dict[str, Any]):
        """Process slot status update from sensor topic."""
        raw_distance = payload.get("distance_cm")
        if raw_distance is None:
            logger.warning(
                "MQTT slot update ignored: missing distance_cm | lot_id=%s slot_topic_id=%s payload=%s",
                lot_id,
                slot_topic_id,
                payload,
            )
            return

        try:
            distance = float(raw_distance)
        except (TypeError, ValueError):
            logger.warning(
                "MQTT slot update ignored: invalid distance_cm | lot_id=%s slot_topic_id=%s value=%s",
                lot_id,
                slot_topic_id,
                raw_distance,
            )
            return

        if "occupied" in payload and isinstance(payload["occupied"], bool):
            is_occupied = payload["occupied"]
        else:
            is_occupied = distance < OCCUPANCY_THRESHOLD

        slot_id = self._resolve_slot_db_id(lot_id, slot_topic_id)

        logger.info(
            "MQTT slot update | lot_id=%s slot_id=%s distance_cm=%.2f occupied=%s",
            lot_id,
            slot_id,
            distance,
            is_occupied,
        )

        if not self.app:
            return

        with self.app.app_context():
            from app import db
            from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot, SensorReading
            from app.services.notifications import publish_slot_change

            slot = db.session.get(ParkingSlot, slot_id)
            if slot is None:
                logger.warning(
                    "MQTT slot update dropped: slot not found | lot_id=%s slot_id=%s",
                    lot_id,
                    slot_id,
                )
                return

            old_status = slot.is_occupied
            slot.is_occupied = is_occupied

            if old_status != is_occupied:
                slot.last_status_change = datetime.utcnow()
                event_type = "entry" if is_occupied else "exit"
                db.session.add(
                    ParkingEvent(
                        slot_id=slot.id,
                        event_type=event_type,
                        sensor_distance_cm=distance,
                    )
                )
                publish_slot_change(
                    slot_id=slot.id,
                    lot_id=slot.lot_id,
                    zone_id=slot.zone_id,
                    is_occupied=slot.is_occupied,
                    event_type=event_type,
                    source="mqtt",
                    distance_cm=distance,
                )

            db.session.add(
                SensorReading(
                    slot_id=slot.id,
                    distance_cm=distance,
                    is_occupied=is_occupied,
                )
            )
            db.session.add(
                OccupancyLog(
                    slot_id=slot.id,
                    status="occupied" if is_occupied else "vacant",
                    distance_cm=distance,
                )
            )

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.exception(
                    "MQTT slot update commit failed | lot_id=%s slot_id=%s",
                    lot_id,
                    slot_id,
                )

    def _handle_heartbeat(self, lot_id: str, payload: dict[str, Any]):
        """Process device heartbeat."""
        logger.info(
            "MQTT heartbeat | lot_id=%s device=%s status=%s uptime=%s wifi_rssi=%s",
            lot_id,
            payload.get("device"),
            payload.get("status", "online"),
            payload.get("uptime"),
            payload.get("wifi_rssi"),
        )

    def start(self):
        """Connect to broker and start processing."""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            logger.info(
                "MQTT service started | broker=%s port=%s reconnect_min_delay=%s reconnect_max_delay=%s",
                MQTT_BROKER,
                MQTT_PORT,
                self.reconnect_min_delay,
                self.reconnect_max_delay,
            )
        except Exception:
            logger.exception("MQTT startup failed | broker=%s port=%s", MQTT_BROKER, MQTT_PORT)

    def stop(self):
        """Stop MQTT processing."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT service stopped")
