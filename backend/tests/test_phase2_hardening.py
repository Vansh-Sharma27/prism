"""Security/reliability hardening tests for Phase 2 backend APIs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from app.models.user import User
from seed import seed_campus_data


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "phase2_hardening.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "phase2-secret-key-1234567890-abcde")
    monkeypatch.setenv("JWT_SECRET_KEY", "phase2-jwt-secret-key-1234567890")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_RATE_LIMIT_AUTH_LOGIN", "3 per minute")
    monkeypatch.setenv("PRISM_RATE_LIMIT_AUTH_REGISTER", "5 per minute")

    app = create_app()
    app.config.update(TESTING=True, SSE_HEARTBEAT_INTERVAL_SECONDS=1)

    with app.app_context():
        db.drop_all()
        db.create_all()

        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

        student = User(email="student@prism.local", role="student")
        student.set_password("Student@12345")
        db.session.add(student)

        faculty = User(email="faculty@prism.local", role="faculty")
        faculty.set_password("Faculty@12345")
        db.session.add(faculty)

        fixed_events = [
            ParkingEvent(
                slot_id="lot-a-slot-1",
                event_type="entry",
                sensor_distance_cm=7.1,
                timestamp=datetime(2026, 3, 1, 10, 0, 0),
            ),
            ParkingEvent(
                slot_id="lot-a-slot-1",
                event_type="exit",
                sensor_distance_cm=86.0,
                timestamp=datetime(2026, 3, 1, 11, 0, 0),
            ),
            ParkingEvent(
                slot_id="lot-b-slot-1",
                event_type="entry",
                sensor_distance_cm=6.8,
                timestamp=datetime(2026, 3, 1, 12, 0, 0),
            ),
        ]
        db.session.add_all(fixed_events)

        db.session.add(
            OccupancyLog(
                slot_id="lot-a-slot-1",
                status="occupied",
                distance_cm=7.1,
                timestamp=datetime(2026, 3, 1, 10, 0, 0),
            )
        )

        db.session.commit()

    with app.test_client() as test_client:
        yield test_client


def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_login_rate_limit_returns_429_with_error_envelope(client):
    statuses = []
    for _ in range(4):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "student@prism.local", "password": "wrong-password"},
        )
        statuses.append(response.status_code)

    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429

    body = response.get_json()
    assert body["error"]
    assert body["code"]
    assert body["request_id"]


def test_student_cannot_mutate_slot_status(client):
    headers = _auth_headers(client, "student@prism.local", "Student@12345")

    response = client.put(
        "/api/v1/slots/lot-a-slot-1/status",
        headers=headers,
        json={"is_occupied": True},
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"] == "Insufficient role permissions"
    assert payload["code"] == "forbidden"


def test_batch_status_update_supports_partial_failures(client):
    admin_headers = _auth_headers(client, "admin@prism.local", "Admin@12345")

    response = client.put(
        "/api/v1/slots/status/batch",
        headers=admin_headers,
        json={
            "updates": [
                {"slot_id": "lot-a-slot-1", "is_occupied": True, "distance_cm": 7.5},
                {"slot_id": "lot-a-slot-2", "is_reserved": True},
                {"slot_id": "", "is_occupied": True},
                {"slot_id": "missing-slot", "is_occupied": True},
                {"slot_id": "lot-a-slot-3"},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["summary"] == {
        "requested": 5,
        "updated": 2,
        "unchanged": 0,
        "failed": 3,
    }
    assert len(payload["results"]) == 5

    slot_response = client.get("/api/v1/slots/lot-a-slot-1", headers=admin_headers)
    assert slot_response.status_code == 200
    assert slot_response.get_json()["is_occupied"] is True


def test_manual_slot_update_refreshes_telemetry_for_admin_sensor_health(client):
    admin_headers = _auth_headers(client, "admin@prism.local", "Admin@12345")

    update_response = client.put(
        "/api/v1/slots/lot-a-slot-2/status",
        headers=admin_headers,
        json={"distance_cm": 11.4, "is_occupied": True},
    )
    assert update_response.status_code == 200

    with client.application.app_context():
        slot = db.session.get(ParkingSlot, "lot-a-slot-2")
        assert slot is not None
        assert slot.last_telemetry_at is not None
        assert slot.last_distance_cm == pytest.approx(11.4)

    sensors_response = client.get("/api/v1/admin/sensors?offline_after_seconds=600", headers=admin_headers)
    assert sensors_response.status_code == 200
    sensors = {row["sensor_id"]: row for row in sensors_response.get_json()["sensors"]}

    assert sensors["lot-a-sensor-2"]["status"] == "online"
    assert sensors["lot-a-sensor-2"]["last_distance_cm"] == pytest.approx(11.4)


def test_event_filter_queries_are_deterministic(client):
    headers = _auth_headers(client, "faculty@prism.local", "Faculty@12345")
    query = (
        "/api/v1/events?lot_id=lot-a&event_type=entry"
        "&start=2026-03-01T09:00:00&end=2026-03-01T10:30:00&limit=10"
    )

    first = client.get(query, headers=headers)
    second = client.get(query, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json() == second.get_json()

    payload = first.get_json()
    assert payload["total"] == 1
    assert payload["events"][0]["slot_id"] == "lot-a-slot-1"
    assert payload["events"][0]["event_type"] == "entry"


def test_sse_stream_requires_authentication(client):
    response = client.get("/api/v1/notifications/stream")
    assert response.status_code == 401


def test_sse_stream_delivers_slot_change_events(client):
    admin_headers = _auth_headers(client, "admin@prism.local", "Admin@12345")

    stream = client.get(
        "/api/v1/notifications/stream?lot_id=lot-a",
        headers=admin_headers,
        buffered=False,
    )

    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers.get("Content-Type", "")

    connected_chunk = next(stream.response).decode("utf-8")
    assert "event: connected" in connected_chunk

    with client.application.test_client() as mutator:
        update_response = mutator.put(
            "/api/v1/slots/lot-a-slot-2/status",
            headers=admin_headers,
            json={"is_occupied": True, "distance_cm": 8.0},
        )
        assert update_response.status_code == 200

    found_slot_change = False
    for _ in range(6):
        chunk = next(stream.response).decode("utf-8")
        if "event: slot_change" in chunk and '"slot_id": "lot-a-slot-2"' in chunk:
            found_slot_change = True
            break

    stream.close()
    assert found_slot_change
