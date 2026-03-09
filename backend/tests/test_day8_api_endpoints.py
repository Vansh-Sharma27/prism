"""Tests for Day 8 prediction/recommendation/admin endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from seed import seed_campus_data


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "day8_endpoints.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day8-secret-key-1234567890-abcdef")
    monkeypatch.setenv("JWT_SECRET_KEY", "day8-jwt-secret-key-1234567890-abcd")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

        now = datetime.utcnow()
        samples = [
            ("lot-a-slot-1", "occupied", 7.2, now - timedelta(hours=1)),
            ("lot-a-slot-2", "vacant", 88.4, now - timedelta(hours=2)),
            ("lot-a-slot-3", "occupied", 9.1, now - timedelta(hours=3)),
            ("lot-b-slot-2", "occupied", 6.8, now - timedelta(days=1, hours=1)),
            ("lot-b-slot-3", "vacant", 102.3, now - timedelta(days=1, hours=2)),
        ]

        for slot_id, status, distance, ts in samples:
            slot = db.session.get(ParkingSlot, slot_id)
            assert slot is not None
            slot.is_occupied = status == "occupied"
            slot.last_status_change = ts
            slot.last_telemetry_at = ts
            slot.last_distance_cm = distance
            db.session.add(
                OccupancyLog(
                    slot_id=slot_id,
                    status=status,
                    distance_cm=distance,
                    timestamp=ts,
                )
            )
            db.session.add(
                ParkingEvent(
                    slot_id=slot_id,
                    event_type="entry" if status == "occupied" else "exit",
                    sensor_distance_cm=distance,
                    timestamp=ts,
                )
            )
        db.session.commit()

    with app.test_client() as test_client:
        yield test_client


def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _register_student(client, email: str = "day8.student@gla.ac.in", password: str = "StrongPass123") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201


def test_prediction_endpoint_returns_zone_forecast_for_authenticated_user(client):
    _register_student(client)
    headers = _auth_headers(client, "day8.student@gla.ac.in", "StrongPass123")

    response = client.get(
        "/api/v1/lots/lot-a/predict?day=wednesday&time=10:00",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["lot_id"] == "lot-a"
    assert payload["predicted_for"] == {"day": "wednesday", "time": "10:00"}
    assert payload["model"]["status"] == "mock"
    assert len(payload["zones"]) >= 1
    assert "predicted_occupancy_pct" in payload["zones"][0]


def test_recommendation_requires_destination_query_param(client):
    _register_student(client, email="day8.student2@gla.ac.in")
    headers = _auth_headers(client, "day8.student2@gla.ac.in", "StrongPass123")

    response = client.get("/api/v1/lots/lot-a/recommend", headers=headers)
    assert response.status_code == 400
    assert response.get_json()["error"] == "destination query parameter is required"


def test_recommendation_returns_mock_ranked_zone(client):
    _register_student(client, email="day8.student3@gla.ac.in")
    headers = _auth_headers(client, "day8.student3@gla.ac.in", "StrongPass123")

    response = client.get(
        "/api/v1/lots/lot-a/recommend?destination=Library&day=thursday&time=16:30",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["destination"] == "Library"
    assert payload["recommended_zone"] is not None
    assert payload["engine"]["status"] == "mock"


def test_admin_endpoints_reject_non_admin_user(client):
    _register_student(client, email="day8.student4@gla.ac.in")
    headers = _auth_headers(client, "day8.student4@gla.ac.in", "StrongPass123")

    sensors = client.get("/api/admin/sensors", headers=headers)
    analytics = client.get("/api/admin/analytics", headers=headers)

    assert sensors.status_code == 403
    assert analytics.status_code == 403
    assert sensors.get_json()["error"] == "Admin access required"


def test_admin_endpoints_return_sensor_and_analytics_payload_for_admin(client):
    headers = _auth_headers(client, "admin@prism.local", "Admin@12345")

    sensors = client.get("/api/admin/sensors?offline_after_seconds=120", headers=headers)
    assert sensors.status_code == 200
    sensors_payload = sensors.get_json()
    assert sensors_payload["summary"]["total_sensors"] >= 1
    assert len(sensors_payload["sensors"]) >= 1
    assert "uptime_24h_pct" in sensors_payload["sensors"][0]
    assert 0.0 <= sensors_payload["sensors"][0]["uptime_24h_pct"] <= 100.0

    analytics = client.get("/api/admin/analytics?days=7", headers=headers)
    assert analytics.status_code == 200
    analytics_payload = analytics.get_json()
    assert analytics_payload["window_days"] == 7
    assert "daily_occupancy_average" in analytics_payload
    assert "peak_hour" in analytics_payload
    assert "zone_utilization_comparison" in analytics_payload
    assert len(analytics_payload["hourly_event_distribution"]) == 24
