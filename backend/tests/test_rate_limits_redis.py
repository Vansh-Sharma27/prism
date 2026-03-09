from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from seed import seed_campus_data


def _build_app(db_file: Path, redis_url: str):
    import os

    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["SECRET_KEY"] = "redis-rate-limit-secret-key-123456"
    os.environ["JWT_SECRET_KEY"] = "redis-rate-limit-jwt-secret-key-123"
    os.environ["PRISM_ALLOW_PUBLIC_READS"] = "false"
    os.environ["PRISM_ALLOW_PRIVILEGED_SELF_REGISTER"] = "false"
    os.environ["PRISM_RATE_LIMIT_AUTH_LOGIN"] = "3 per minute"
    os.environ["PRISM_RATE_LIMIT_STORAGE_URI"] = redis_url
    os.environ["PRISM_NOTIFICATIONS_BACKEND"] = "memory"

    return create_app()


@pytest.mark.redis
def test_login_rate_limit_is_shared_across_app_instances(
    tmp_path: Path,
    realtime_stack,
    redis_client,
):
    db_file = tmp_path / "shared-rate-limits.db"
    redis_url = realtime_stack["redis_url"]

    app_one = _build_app(db_file, redis_url)
    app_two = _build_app(db_file, redis_url)

    with app_one.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    client_one = app_one.test_client()
    client_two = app_two.test_client()
    headers = {"X-Forwarded-For": "203.0.113.10"}

    responses = [
        client_one.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "admin@prism.local", "password": "wrong-password"},
        ),
        client_one.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "admin@prism.local", "password": "wrong-password"},
        ),
        client_two.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "admin@prism.local", "password": "wrong-password"},
        ),
        client_two.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "admin@prism.local", "password": "wrong-password"},
        ),
    ]

    assert [response.status_code for response in responses[:3]] == [401, 401, 401]
    assert responses[3].status_code == 429
