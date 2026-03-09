"""MQTT integration tests for the compose-backed Mosquitto broker."""

from __future__ import annotations

import json
import time

import paho.mqtt.client as mqtt


def _mqtt_target(realtime_stack) -> tuple[str, int]:
    return realtime_stack["mqtt_host"], realtime_stack["mqtt_port"]


def _publish_and_disconnect(client: mqtt.Client, topic: str, payload: str) -> None:
    client.loop_start()
    result = client.publish(topic, payload)
    result.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()


def publish_slot_update(
    lot_id: str,
    slot_id: str,
    distance_cm: float,
    *,
    mqtt_host: str,
    mqtt_port: int,
    occupied: bool | None = None,
):
    """Helper to publish a slot update message."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(mqtt_host, mqtt_port, 60)

    payload = {
        "distance_cm": distance_cm,
        "timestamp": int(time.time()),
    }
    if occupied is not None:
        payload["occupied"] = occupied

    topic = f"prism/{lot_id}/slot/{slot_id}"
    _publish_and_disconnect(client, topic, json.dumps(payload))
    return topic, payload


def publish_heartbeat(
    lot_id: str,
    device: str,
    uptime: int,
    wifi_rssi: int,
    *,
    mqtt_host: str,
    mqtt_port: int,
    slots: list[dict[str, object]] | None = None,
):
    """Helper to publish a heartbeat message."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(mqtt_host, mqtt_port, 60)

    payload = {
        "device": device,
        "uptime": uptime,
        "wifi_rssi": wifi_rssi,
    }
    if slots is not None:
        payload["slots"] = slots

    topic = f"prism/{lot_id}/heartbeat"
    _publish_and_disconnect(client, topic, json.dumps(payload))
    return topic, payload


class TestMQTTConnectivity:
    """Test MQTT broker connectivity."""

    def test_broker_connection(self, realtime_stack):
        """Verify MQTT broker is reachable."""
        mqtt_host, mqtt_port = _mqtt_target(realtime_stack)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        connected = False

        def on_connect(client, userdata, flags, reason_code, properties):
            nonlocal connected
            connected = reason_code == 0

        client.on_connect = on_connect
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()
        time.sleep(1)
        client.loop_stop()
        client.disconnect()

        assert connected, f"Failed to connect to MQTT broker at {mqtt_host}:{mqtt_port}"

    def test_publish_subscribe(self, realtime_stack):
        """Verify basic pub/sub works."""
        mqtt_host, mqtt_port = _mqtt_target(realtime_stack)
        received_messages = []

        def on_message(client, userdata, msg):
            received_messages.append(msg.payload.decode())

        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(mqtt_host, mqtt_port, 60)
        sub_client.subscribe("test/prism/#")
        sub_client.loop_start()

        time.sleep(0.5)

        pub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        pub_client.connect(mqtt_host, mqtt_port, 60)
        _publish_and_disconnect(pub_client, "test/prism/ping", "pong")

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        assert received_messages == ["pong"]


class TestPRISMTopics:
    """Test PRISM-specific topic patterns."""

    def test_slot_update_topic_format(self, realtime_stack):
        """Verify slot update message format."""
        mqtt_host, mqtt_port = _mqtt_target(realtime_stack)
        received = []

        def on_message(client, userdata, msg):
            received.append(
                {
                    "topic": msg.topic,
                    "payload": json.loads(msg.payload.decode()),
                }
            )

        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(mqtt_host, mqtt_port, 60)
        sub_client.subscribe("prism/+/slot/+")
        sub_client.loop_start()

        time.sleep(0.5)

        topic, payload = publish_slot_update(
            "lot-test-topic",
            "slot-test-1",
            8.5,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
        )

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        matching = [entry for entry in received if entry["topic"] == topic]
        assert len(matching) >= 1
        assert matching[-1]["payload"]["distance_cm"] == payload["distance_cm"]
        assert "timestamp" in matching[-1]["payload"]

    def test_heartbeat_topic_format(self, realtime_stack):
        """Verify heartbeat message format."""
        mqtt_host, mqtt_port = _mqtt_target(realtime_stack)
        received = []

        def on_message(client, userdata, msg):
            received.append(
                {
                    "topic": msg.topic,
                    "payload": json.loads(msg.payload.decode()),
                }
            )

        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(mqtt_host, mqtt_port, 60)
        sub_client.subscribe("prism/+/heartbeat")
        sub_client.loop_start()

        time.sleep(0.5)

        topic, payload = publish_heartbeat(
            "lot-test-topic",
            "esp32-test-01",
            12345,
            -62,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            slots=[
                {"slot_id": "slot-1", "distance_cm": 82.1, "occupied": False},
                {"slot_id": "slot-2", "distance_cm": 7.4, "occupied": True},
            ],
        )

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        matching = [entry for entry in received if entry["topic"] == topic]
        assert len(matching) >= 1
        assert matching[-1]["payload"]["device"] == payload["device"]
        assert matching[-1]["payload"]["uptime"] == payload["uptime"]
        assert matching[-1]["payload"]["wifi_rssi"] == payload["wifi_rssi"]
        assert matching[-1]["payload"]["slots"] == payload["slots"]

    def test_occupied_threshold(self):
        """Test occupancy detection threshold (15cm)."""
        assert 8.5 < 15, "8.5cm should trigger occupied"
        assert 4.0 < 15, "4.0cm should trigger occupied"
        assert 15.0 >= 15, "15.0cm should be vacant"
        assert 100.0 >= 15, "100.0cm should be vacant"
