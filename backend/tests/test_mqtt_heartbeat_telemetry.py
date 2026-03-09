"""Regression tests for heartbeat-driven slot telemetry freshness."""

from __future__ import annotations

import json
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest

from app import create_app, db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from app.services.mqtt_service import MQTTService
from seed import seed_campus_data


def _wait_for(predicate, *, timeout_seconds: float = 10.0, interval_seconds: float = 0.25) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval_seconds)
    return False


def _publish_heartbeat(
    host: str,
    port: int,
    lot_id: str,
    *,
    device: str,
    slots: list[dict[str, object]],
) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port, 60)
    client.loop_start()
    result = client.publish(
        f"prism/{lot_id}/heartbeat",
        json.dumps(
            {
                "device": device,
                "uptime": int(time.time()),
                "wifi_rssi": -58,
                "slots": slots,
            }
        ),
    )
    result.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()


def _build_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, realtime_stack):
    db_file = tmp_path / "mqtt_heartbeat.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "mqtt-heartbeat-secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "mqtt-heartbeat-jwt-secret-key-1234567890")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("PRISM_NOTIFICATIONS_BACKEND", "memory")
    monkeypatch.setenv("MQTT_BROKER_HOST", realtime_stack["mqtt_host"])
    monkeypatch.setenv("MQTT_BROKER_PORT", str(realtime_stack["mqtt_port"]))

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    return app


def _login_admin(client) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@prism.local", "password": "Admin@12345"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


def test_heartbeat_snapshots_refresh_slot_telemetry_without_fake_churn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    realtime_stack,
):
    app = _build_app(tmp_path, monkeypatch, realtime_stack)
    service = MQTTService(app)

    service.start()
    try:
        assert _wait_for(service.client.is_connected)

        _publish_heartbeat(
            realtime_stack["mqtt_host"],
            realtime_stack["mqtt_port"],
            "lot-a",
            device="esp32-01",
            slots=[
                {"slot_id": "slot-1", "distance_cm": 84.2, "occupied": False},
                {"slot_id": "slot-2", "distance_cm": 8.1, "occupied": True},
                {"slot_id": "slot-3", "status": "offline"},
            ],
        )

        def _telemetry_written() -> bool:
            with app.app_context():
                db.session.remove()
                slot_1 = db.session.get(ParkingSlot, "lot-a-slot-1")
                slot_2 = db.session.get(ParkingSlot, "lot-a-slot-2")
                return bool(slot_1 and slot_1.last_telemetry_at and slot_2 and slot_2.last_telemetry_at)

        assert _wait_for(_telemetry_written)

        with app.app_context():
            db.session.remove()
            slot_1 = db.session.get(ParkingSlot, "lot-a-slot-1")
            slot_2 = db.session.get(ParkingSlot, "lot-a-slot-2")
            slot_3 = db.session.get(ParkingSlot, "lot-a-slot-3")

            assert slot_1 is not None and slot_2 is not None and slot_3 is not None
            assert slot_1.last_telemetry_at is not None
            assert slot_1.last_distance_cm == pytest.approx(84.2)
            assert slot_1.is_occupied is False

            assert slot_2.last_telemetry_at is not None
            assert slot_2.last_distance_cm == pytest.approx(8.1)
            assert slot_2.is_occupied is True

            assert slot_3.last_telemetry_at is None

            assert OccupancyLog.query.filter_by(slot_id="lot-a-slot-1").count() == 0
            assert ParkingEvent.query.filter_by(slot_id="lot-a-slot-2", event_type="entry").count() == 1

        with app.test_client() as client:
            headers = _login_admin(client)
            response = client.get("/api/v1/admin/sensors?offline_after_seconds=90", headers=headers)

        assert response.status_code == 200
        payload = response.get_json()
        sensors = {row["sensor_id"]: row for row in payload["sensors"]}

        assert sensors["lot-a-sensor-1"]["status"] == "online"
        assert sensors["lot-a-sensor-1"]["slots"][0]["telemetry_status"] == "online"
        assert sensors["lot-a-sensor-1"]["last_distance_cm"] == pytest.approx(84.2)
        assert sensors["lot-a-sensor-3"]["status"] == "offline"
    finally:
        service.stop()


def test_slot_updates_refresh_telemetry_without_writing_duplicate_occupancy_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    realtime_stack,
):
    app = _build_app(tmp_path, monkeypatch, realtime_stack)
    service = MQTTService(app)

    service.start()
    try:
        assert _wait_for(service.client.is_connected)

        _publish_heartbeat(
            realtime_stack["mqtt_host"],
            realtime_stack["mqtt_port"],
            "lot-a",
            device="esp32-02",
            slots=[
                {"slot_id": "slot-1", "distance_cm": 82.0, "occupied": False},
            ],
        )

        def _baseline_written() -> bool:
            with app.app_context():
                db.session.remove()
                slot = db.session.get(ParkingSlot, "lot-a-slot-1")
                return bool(slot and slot.last_telemetry_at)

        assert _wait_for(_baseline_written)

        with app.app_context():
            db.session.remove()
            baseline_logs = OccupancyLog.query.filter_by(slot_id="lot-a-slot-1").count()
            baseline_events = ParkingEvent.query.filter_by(slot_id="lot-a-slot-1").count()

        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        publisher.connect(realtime_stack["mqtt_host"], realtime_stack["mqtt_port"], 60)
        publisher.loop_start()
        result = publisher.publish(
            "prism/lot-a/slot/slot-1",
            json.dumps(
                {
                    "distance_cm": 79.5,
                    "occupied": False,
                    "timestamp": int(time.time()),
                }
            ),
        )
        result.wait_for_publish(timeout=5)
        publisher.loop_stop()
        publisher.disconnect()

        def _telemetry_refreshed() -> bool:
            with app.app_context():
                db.session.remove()
                slot = db.session.get(ParkingSlot, "lot-a-slot-1")
                return bool(slot and slot.last_distance_cm == pytest.approx(79.5))

        assert _wait_for(_telemetry_refreshed)

        with app.app_context():
            db.session.remove()
            slot = db.session.get(ParkingSlot, "lot-a-slot-1")
            assert slot is not None
            assert slot.last_distance_cm == pytest.approx(79.5)
            assert slot.is_occupied is False
            assert OccupancyLog.query.filter_by(slot_id="lot-a-slot-1").count() == baseline_logs
            assert ParkingEvent.query.filter_by(slot_id="lot-a-slot-1").count() == baseline_events
    finally:
        service.stop()
