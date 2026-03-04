"""Day 7 end-to-end API flow test for simulated occupancy updates."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from seed import seed_campus_data


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "day7_e2e_flow.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day7-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "day7-jwt-secret")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    with app.test_client() as test_client:
        yield test_client


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return _auth_header(response.get_json()["access_token"])


def test_day7_register_login_and_live_updates_flow(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "day7.student@gla.ac.in",
            "password": "StrongPass123",
        },
    )
    assert register_response.status_code == 201

    headers = _login(client, "day7.student@gla.ac.in", "StrongPass123")
    admin_headers = _login(client, "admin@prism.local", "Admin@12345")

    lots_response = client.get("/api/v1/lots", headers=headers)
    assert lots_response.status_code == 200
    lots_payload = lots_response.get_json()
    assert lots_payload["total"] >= 1

    summary_before = client.get("/api/v1/lots/summary", headers=headers)
    assert summary_before.status_code == 200
    occupied_before = summary_before.get_json()["occupied_slots"]

    slots_response = client.get("/api/v1/slots?lot_id=lot-a&status=available", headers=headers)
    assert slots_response.status_code == 200
    slots_payload = slots_response.get_json()
    assert slots_payload["total"] >= 1
    slot_id = slots_payload["slots"][0]["id"]

    update_response = client.put(
        f"/api/v1/slots/{slot_id}/status",
        headers=admin_headers,
        json={"is_occupied": True},
    )
    assert update_response.status_code == 200
    update_payload = update_response.get_json()
    assert update_payload["slot"]["is_occupied"] is True
    assert update_payload["changed"] is True

    events_response = client.get("/api/v1/events?lot_id=lot-a&limit=20", headers=headers)
    assert events_response.status_code == 200
    events_payload = events_response.get_json()
    assert events_payload["total"] >= 1
    assert any(
        event["slot_id"] == slot_id and event["event_type"] == "entry"
        for event in events_payload["events"]
    )

    summary_after = client.get("/api/v1/lots/summary", headers=headers)
    assert summary_after.status_code == 200
    occupied_after = summary_after.get_json()["occupied_slots"]
    assert occupied_after == occupied_before + 1
