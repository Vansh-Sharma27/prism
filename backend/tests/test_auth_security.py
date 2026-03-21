"""Security-focused tests for authentication routes."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from app.models.user import User


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "auth_security_test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890-abcdef")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcd")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        yield test_client


def test_register_rejects_privileged_role_by_default(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@gla.ac.in",
            "password": "StrongPass123",
            "role": "admin",
        },
    )

    assert response.status_code == 403
    body = response.get_json()
    assert body["error"] == "Self-registration only supports student role"


def test_register_allows_privileged_role_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "auth_privileged_enabled.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890-abcdef")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcd")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "true")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "faculty@gla.ac.in",
                "password": "StrongPass123",
                "role": "faculty",
            },
        )

        assert response.status_code == 201
        payload = response.get_json()
        assert payload["user"]["role"] == "faculty"


def test_register_normalizes_email_and_defaults_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Student@GLA.ac.in",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 201

    with client.application.app_context():
        user = User.query.filter_by(email="student@gla.ac.in").first()
        assert user is not None
        assert user.role == "student"
