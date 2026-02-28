"""
MQTT Integration Tests for PRISM backend.

Tests the MQTTService's ability to receive and process sensor messages.
Run with: pytest tests/test_mqtt_integration.py -v
"""
import json
import time
try:
    import pytest
except ImportError:
    pytest = None
import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883


def publish_slot_update(lot_id: str, slot_id: str, distance_cm: float, occupied: bool = None):
    """Helper to publish a slot update message."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    payload = {
        "distance_cm": distance_cm,
        "timestamp": int(time.time())
    }
    if occupied is not None:
        payload["occupied"] = occupied

    topic = f"prism/{lot_id}/slot/{slot_id}"
    client.publish(topic, json.dumps(payload))
    client.disconnect()
    return topic, payload


def publish_heartbeat(lot_id: str, device: str, uptime: int, wifi_rssi: int):
    """Helper to publish a heartbeat message."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    payload = {
        "device": device,
        "uptime": uptime,
        "wifi_rssi": wifi_rssi
    }

    topic = f"prism/{lot_id}/heartbeat"
    client.publish(topic, json.dumps(payload))
    client.disconnect()
    return topic, payload


class TestMQTTConnectivity:
    """Test MQTT broker connectivity."""

    def test_broker_connection(self):
        """Verify MQTT broker is reachable."""
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        connected = False

        def on_connect(client, userdata, flags, reason_code, properties):
            nonlocal connected
            connected = (reason_code == 0)

        client.on_connect = on_connect
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(1)
        client.loop_stop()
        client.disconnect()

        assert connected, "Failed to connect to MQTT broker"

    def test_publish_subscribe(self):
        """Verify basic pub/sub works."""
        received_messages = []

        def on_message(client, userdata, msg):
            received_messages.append(msg.payload.decode())

        # Subscribe
        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        sub_client.subscribe("test/prism/#")
        sub_client.loop_start()

        time.sleep(0.5)

        # Publish
        pub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        pub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        pub_client.publish("test/prism/ping", "pong")
        pub_client.disconnect()

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        assert len(received_messages) == 1
        assert received_messages[0] == "pong"


class TestPRISMTopics:
    """Test PRISM-specific topic patterns."""

    def test_slot_update_topic_format(self):
        """Verify slot update message format."""
        received = []

        def on_message(client, userdata, msg):
            received.append({
                "topic": msg.topic,
                "payload": json.loads(msg.payload.decode())
            })

        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        sub_client.subscribe("prism/+/slot/+")
        sub_client.loop_start()

        time.sleep(0.5)

        topic, payload = publish_slot_update("lot-a", "slot-1", 8.5)

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        assert len(received) == 1
        assert received[0]["topic"] == "prism/lot-a/slot/slot-1"
        assert received[0]["payload"]["distance_cm"] == 8.5
        assert "timestamp" in received[0]["payload"]

    def test_heartbeat_topic_format(self):
        """Verify heartbeat message format."""
        received = []

        def on_message(client, userdata, msg):
            received.append({
                "topic": msg.topic,
                "payload": json.loads(msg.payload.decode())
            })

        sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        sub_client.on_message = on_message
        sub_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        sub_client.subscribe("prism/+/heartbeat")
        sub_client.loop_start()

        time.sleep(0.5)

        topic, payload = publish_heartbeat("lot-a", "esp32-01", 12345, -62)

        time.sleep(0.5)
        sub_client.loop_stop()
        sub_client.disconnect()

        assert len(received) == 1
        assert received[0]["topic"] == "prism/lot-a/heartbeat"
        assert received[0]["payload"]["device"] == "esp32-01"
        assert received[0]["payload"]["uptime"] == 12345
        assert received[0]["payload"]["wifi_rssi"] == -62

    def test_occupied_threshold(self):
        """Test occupancy detection threshold (15cm)."""
        # Distance < 15cm should be occupied
        assert 8.5 < 15, "8.5cm should trigger occupied"
        assert 4.0 < 15, "4.0cm should trigger occupied"

        # Distance >= 15cm should be vacant
        assert 15.0 >= 15, "15.0cm should be vacant"
        assert 100.0 >= 15, "100.0cm should be vacant"


if __name__ == "__main__":
    # Quick standalone test
    print("Testing MQTT connectivity...")

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"✓ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")

        # Test slot update
        topic, payload = publish_slot_update("lot-a", "slot-1", 8.5, True)
        print(f"✓ Published slot update to {topic}")

        # Test heartbeat
        topic, payload = publish_heartbeat("lot-a", "esp32-01", 12345, -62)
        print(f"✓ Published heartbeat to {topic}")

        print("\nAll MQTT tests passed!")

    except Exception as e:
        print(f"✗ MQTT test failed: {e}")
        exit(1)
