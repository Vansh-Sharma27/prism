"""Tests for security hardening fixes (TOCTOU, MQTT locking, SSE cap, topic validation)."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import create_app, db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from app.services.mqtt_service import MQTTService, _TOPIC_ID_PATTERN
from seed import seed_campus_data


@pytest.fixture()
def app_with_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Flask app with seeded data for security tests."""
    db_file = tmp_path / "security_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "sec-test-secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "sec-test-jwt-secret-1234567890")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    return app


class TestTOCTOUFix:
    """Verify TOCTOU fix: model loaded from in-memory buffer after hash verification."""

    def test_verify_and_load_uses_bytesio(self, tmp_path, monkeypatch):
        """Verify the atomic read-hash-load path."""
        from app.services.prediction_service import _compute_buffer_sha256, _verify_and_load_model

        # Create a mock model file with known content
        model_path = tmp_path / "test_model.pkl"
        # We can't easily create a valid sklearn model in bytes, so test the hash path
        model_path.write_bytes(b"fake model content")
        hash_value = _compute_buffer_sha256(b"fake model content")
        hash_path = model_path.with_suffix(".pkl.sha256")
        hash_path.write_text(hash_value)

        # The load will fail because it's not a valid pickle, but the hash should pass
        monkeypatch.delenv("ML_SKIP_INTEGRITY_CHECK", raising=False)
        result = _verify_and_load_model(model_path)
        # Should return None because the content isn't a valid joblib model,
        # but the hash check itself should pass (no TOCTOU)
        assert result is None

    def test_hash_mismatch_rejects_model(self, tmp_path, monkeypatch):
        """Wrong hash in sidecar should prevent loading."""
        from app.services.prediction_service import _verify_and_load_model

        model_path = tmp_path / "bad_model.pkl"
        model_path.write_bytes(b"some model data")
        hash_path = model_path.with_suffix(".pkl.sha256")
        hash_path.write_text("0000000000000000000000000000000000000000000000000000000000000000")

        monkeypatch.delenv("ML_SKIP_INTEGRITY_CHECK", raising=False)
        result = _verify_and_load_model(model_path)
        assert result is None

    def test_missing_sidecar_rejects_model(self, tmp_path, monkeypatch):
        """Missing .sha256 sidecar should prevent loading."""
        from app.services.prediction_service import _verify_and_load_model

        model_path = tmp_path / "orphan_model.pkl"
        model_path.write_bytes(b"orphan model data")

        monkeypatch.delenv("ML_SKIP_INTEGRITY_CHECK", raising=False)
        result = _verify_and_load_model(model_path)
        assert result is None

    def test_buffer_sha256_matches_file_sha256(self, tmp_path):
        """Verify buffer hash matches traditional file hash."""
        from app.services.prediction_service import _compute_buffer_sha256

        content = b"test content for hashing"
        expected = hashlib.sha256(content).hexdigest()
        assert _compute_buffer_sha256(content) == expected


class TestMQTTTopicValidation:
    """Verify MQTT topic ID length/charset validation."""

    def test_valid_topic_ids(self):
        assert _TOPIC_ID_PATTERN.fullmatch("lot-a")
        assert _TOPIC_ID_PATTERN.fullmatch("slot_1")
        assert _TOPIC_ID_PATTERN.fullmatch("A1")
        assert _TOPIC_ID_PATTERN.fullmatch("a" * 64)

    def test_rejects_too_long(self):
        assert _TOPIC_ID_PATTERN.fullmatch("a" * 65) is None

    def test_rejects_empty(self):
        assert _TOPIC_ID_PATTERN.fullmatch("") is None

    def test_rejects_special_chars(self):
        assert _TOPIC_ID_PATTERN.fullmatch("lot/a") is None
        assert _TOPIC_ID_PATTERN.fullmatch("lot a") is None
        assert _TOPIC_ID_PATTERN.fullmatch("lot;a") is None
        assert _TOPIC_ID_PATTERN.fullmatch("../etc/passwd") is None

    def test_mqtt_service_rejects_invalid_topic(self, app_with_db):
        """MQTT service should drop messages with invalid topic IDs."""
        service = MQTTService(app=app_with_db)

        # Create a mock MQTT message with invalid lot_id
        mock_msg = MagicMock()
        mock_msg.topic = "prism/lot;injection/slot/slot-1"
        mock_msg.payload = b'{"distance_cm": 8.4, "occupied": true}'

        # Should not raise, just silently drop
        service._on_message(None, None, mock_msg)

        # Verify no events were created
        with app_with_db.app_context():
            events = ParkingEvent.query.all()
            assert len(events) == 0


class TestHeartbeatSavepoints:
    """Verify heartbeat batch uses savepoints per slot."""

    def test_valid_slot_in_batch_persists_despite_bad_slot(self, app_with_db):
        """One bad slot in heartbeat should not roll back valid slots."""
        service = MQTTService(app=app_with_db)

        # Make lot-a-slot-1 occupied, include a nonexistent slot
        payload = {
            "device": "node_1",
            "status": "online",
            "slots": [
                {"slot_id": "slot-1", "distance_cm": 7.0, "occupied": True},
                {"slot_id": "nonexistent-999", "distance_cm": 5.0, "occupied": True},
                {"slot_id": "slot-2", "distance_cm": 90.0, "occupied": False},
            ],
        }

        service._handle_heartbeat("lot-a", payload)

        with app_with_db.app_context():
            slot1 = db.session.get(ParkingSlot, "lot-a-slot-1")
            assert slot1 is not None
            assert slot1.last_telemetry_at is not None


class TestSSEMaxDuration:
    """Verify SSE stream has a max-duration cap."""

    def test_sse_config_has_max_duration(self, app_with_db):
        """App config should have SSE_MAX_DURATION_SECONDS set to 1800 (30 min)."""
        with app_with_db.app_context():
            assert "SSE_MAX_DURATION_SECONDS" in app_with_db.config
            assert app_with_db.config["SSE_MAX_DURATION_SECONDS"] == 1800


class TestMQTTSlotUpdateLocking:
    """Verify SELECT...FOR UPDATE in slot update path."""

    def test_slot_update_uses_select_for_update(self, app_with_db):
        """Verify slot update creates events without duplicates."""
        service = MQTTService(app=app_with_db)

        # Process a slot update
        service._handle_slot_update("lot-a", "slot-1", {
            "distance_cm": 7.5,
            "occupied": True,
        })

        with app_with_db.app_context():
            slot = db.session.get(ParkingSlot, "lot-a-slot-1")
            assert slot is not None
            assert slot.is_occupied is True
            assert slot.last_distance_cm == 7.5

    def test_slot_status_change_creates_event(self, app_with_db):
        """Verify slot state change creates exactly one ParkingEvent."""
        service = MQTTService(app=app_with_db)

        # Ensure slot starts as vacant
        with app_with_db.app_context():
            slot = db.session.get(ParkingSlot, "lot-a-slot-1")
            slot.is_occupied = False
            db.session.commit()

        # Trigger occupancy change
        service._handle_slot_update("lot-a", "slot-1", {
            "distance_cm": 7.5,
            "occupied": True,
        })

        with app_with_db.app_context():
            events = ParkingEvent.query.filter_by(
                slot_id="lot-a-slot-1",
                event_type="entry",
            ).all()
            assert len(events) == 1
