from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from seed import seed_campus_data


def _build_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, redis_url: str):
    db_file = tmp_path / "notifications_redis.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "notifications-secret-key-123456789")
    monkeypatch.setenv("JWT_SECRET_KEY", "notifications-jwt-secret-key-123456")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("PRISM_REDIS_URL", redis_url)
    monkeypatch.setenv("PRISM_NOTIFICATIONS_BACKEND", "redis")
    monkeypatch.setenv("PRISM_NOTIFICATIONS_REDIS_CHANNEL", "prism:test-notifications")

    app = create_app()
    app.config.update(TESTING=True, SSE_HEARTBEAT_INTERVAL_SECONDS=1)
    return app


def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.redis
def test_sse_stream_receives_slot_changes_published_from_another_app_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    realtime_stack,
    redis_client,
):
    app_stream = _build_app(tmp_path, monkeypatch, realtime_stack["redis_url"])
    app_mutator = _build_app(tmp_path, monkeypatch, realtime_stack["redis_url"])

    with app_stream.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    stream_client = app_stream.test_client()
    mutator_client = app_mutator.test_client()
    admin_headers = _auth_headers(stream_client, "admin@prism.local", "Admin@12345")

    stream = stream_client.get(
        "/api/v1/notifications/stream?lot_id=lot-a",
        headers=admin_headers,
        buffered=False,
    )
    assert stream.status_code == 200
    assert "event: connected" in next(stream.response).decode("utf-8")

    update_response = mutator_client.put(
        "/api/v1/slots/lot-a-slot-2/status",
        headers=admin_headers,
        json={"is_occupied": True, "distance_cm": 8.0},
    )
    assert update_response.status_code == 200

    found_slot_change = False
    for _ in range(4):
        chunk = next(stream.response).decode("utf-8")
        if "event: slot_change" in chunk and '"slot_id": "lot-a-slot-2"' in chunk:
            found_slot_change = True
            break

    stream.close()
    assert found_slot_change


@pytest.mark.redis
def test_failed_slot_update_commit_does_not_publish_sse_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    realtime_stack,
    redis_client,
):
    app = _build_app(tmp_path, monkeypatch, realtime_stack["redis_url"])

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    client = app.test_client()
    admin_headers = _auth_headers(client, "admin@prism.local", "Admin@12345")

    stream = client.get(
        "/api/v1/notifications/stream?lot_id=lot-a",
        headers=admin_headers,
        buffered=False,
    )
    assert stream.status_code == 200
    assert "event: connected" in next(stream.response).decode("utf-8")

    original_commit = db.session.commit

    def failing_commit():
        db.session.rollback()
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(db.session, "commit", failing_commit)

    response = client.put(
        "/api/v1/slots/lot-a-slot-2/status",
        headers=admin_headers,
        json={"is_occupied": True, "distance_cm": 7.5},
    )
    assert response.status_code == 500

    observed_chunks = [next(stream.response).decode("utf-8") for _ in range(2)]
    stream.close()

    assert all("event: slot_change" not in chunk for chunk in observed_chunks)
    monkeypatch.setattr(db.session, "commit", original_commit)
