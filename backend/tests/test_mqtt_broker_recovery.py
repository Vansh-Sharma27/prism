"""Chaos test for MQTT broker restart recovery."""

from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest

from app import create_app, db
from app.models.parking import ParkingSlot
from app.services.mqtt_service import MQTTService
from seed import seed_campus_data


ROOT = Path(__file__).resolve().parents[1]


def _wait_for(predicate, *, timeout_seconds: float = 20.0, interval_seconds: float = 0.25) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval_seconds)
    return False


def _wait_for_port(host: str, port: int, timeout_seconds: float = 20.0) -> None:
    ok = _wait_for(
        lambda: _can_connect(host, port),
        timeout_seconds=timeout_seconds,
    )
    if not ok:
        raise RuntimeError(f"Timed out waiting for {host}:{port}")


def _can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _publish_slot_update(host: str, port: int, lot_id: str, slot_id: str, *, occupied: bool) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port, 60)
    client.loop_start()
    result = client.publish(
        f"prism/{lot_id}/slot/{slot_id}",
        json.dumps(
            {
                "distance_cm": 8.0 if occupied else 80.0,
                "occupied": occupied,
                "timestamp": int(time.time()),
            }
        ),
    )
    result.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()


def _build_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, realtime_stack):
    db_file = tmp_path / "mqtt_recovery.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "mqtt-recovery-secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "mqtt-recovery-jwt-secret-key-1234567890")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("PRISM_NOTIFICATIONS_BACKEND", "memory")
    monkeypatch.setenv("MQTT_BROKER_HOST", realtime_stack["mqtt_host"])
    monkeypatch.setenv("MQTT_BROKER_PORT", str(realtime_stack["mqtt_port"]))
    monkeypatch.setenv("MQTT_RECONNECT_MIN_DELAY", "1")
    monkeypatch.setenv("MQTT_RECONNECT_MAX_DELAY", "2")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    return app


def _slot_state(app, slot_id: str) -> bool:
    with app.app_context():
        db.session.remove()
        slot = db.session.get(ParkingSlot, slot_id)
        assert slot is not None
        return bool(slot.is_occupied)


@pytest.mark.chaos
def test_mqtt_service_recovers_after_broker_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    realtime_stack,
):
    app = _build_app(tmp_path, monkeypatch, realtime_stack)
    service = MQTTService(app)
    compose_cmd = [
        "docker",
        "compose",
        "-f",
        realtime_stack["compose_file"],
        "-p",
        realtime_stack["project_name"],
    ]

    service.start()
    try:
        assert _wait_for(service.client.is_connected, timeout_seconds=10)

        _publish_slot_update(
            realtime_stack["mqtt_host"],
            realtime_stack["mqtt_port"],
            "lot-a",
            "slot-1",
            occupied=True,
        )
        assert _wait_for(lambda: _slot_state(app, "lot-a-slot-1") is True, timeout_seconds=10)

        subprocess.run([*compose_cmd, "restart", "mosquitto"], cwd=ROOT, check=True, capture_output=True, text=True)
        _wait_for_port(realtime_stack["mqtt_host"], realtime_stack["mqtt_port"])
        assert _wait_for(service.client.is_connected, timeout_seconds=15)

        _publish_slot_update(
            realtime_stack["mqtt_host"],
            realtime_stack["mqtt_port"],
            "lot-a",
            "slot-1",
            occupied=False,
        )
        assert _wait_for(lambda: _slot_state(app, "lot-a-slot-1") is False, timeout_seconds=15)
    finally:
        service.stop()
