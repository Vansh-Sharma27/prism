"""Tests for Day 10 camera ingest endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from seed import seed_campus_data


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "day10_camera_endpoint.db"
    upload_dir = tmp_path / "uploads"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day10-camera-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "day10-camera-jwt-secret")
    monkeypatch.setenv("PRISM_ALLOW_PUBLIC_READS", "false")
    monkeypatch.setenv("PRISM_ALLOW_PRIVILEGED_SELF_REGISTER", "false")
    monkeypatch.setenv("PRISM_CAMERA_UPLOAD_TOKEN", "camera-shared-token")
    monkeypatch.setenv("PRISM_CAMERA_UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("PRISM_CAMERA_UPLOAD_MAX_BYTES", "16")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    with app.test_client() as test_client:
        yield test_client


def _headers(
    *,
    token: str = "camera-shared-token",
    camera_id: str = "esp32-cam-a",
    content_type: str = "image/jpeg",
) -> dict[str, str]:
    return {
        "X-Camera-Token": token,
        "X-Camera-ID": camera_id,
        "Content-Type": content_type,
    }


def test_upload_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/camera/upload",
        data=b"image",
        headers=_headers(token="wrong-token"),
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid camera ingest token"


def test_upload_validates_camera_id_and_content_type(client):
    missing_id = client.post(
        "/api/v1/camera/upload",
        data=b"image",
        headers={
            "X-Camera-Token": "camera-shared-token",
            "Content-Type": "image/jpeg",
        },
    )
    assert missing_id.status_code == 400
    assert missing_id.get_json()["error"] == "X-Camera-ID header is required"

    invalid_id = client.post(
        "/api/v1/camera/upload",
        data=b"image",
        headers=_headers(camera_id="bad camera id"),
    )
    assert invalid_id.status_code == 400
    assert invalid_id.get_json()["error"] == "Invalid X-Camera-ID format"

    unsupported_type = client.post(
        "/api/v1/camera/upload",
        data=b"image",
        headers=_headers(content_type="application/octet-stream"),
    )
    assert unsupported_type.status_code == 415
    assert "Unsupported media type" in unsupported_type.get_json()["error"]


def test_upload_rejects_payload_larger_than_configured_limit(client):
    response = client.post(
        "/api/v1/camera/upload",
        data=b"0123456789abcdefg",
        headers=_headers(content_type="image/png"),
    )

    assert response.status_code == 413
    assert "exceeds max size" in response.get_json()["error"]


def test_upload_persists_image_and_returns_metadata(client):
    payload = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    response = client.post(
        "/api/v1/camera/upload",
        data=payload,
        headers=_headers(content_type="image/jpeg"),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "received"
    assert body["camera_id"] == "esp32-cam-a"
    assert body["bytes_received"] == len(payload)
    assert body["content_type"] == "image/jpeg"
    assert body["filename"].endswith(".jpg")
    assert body["uploaded_at"]

    upload_path = Path(client.application.config["CAMERA_UPLOAD_DIR"]) / body["filename"]
    assert upload_path.exists()
    assert upload_path.read_bytes() == payload
