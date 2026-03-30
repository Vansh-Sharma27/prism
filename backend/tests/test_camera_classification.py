"""Tests for camera classification service."""

from __future__ import annotations

import pytest

from app.services.camera_classification_service import (
    CameraClassificationService,
    ClassificationResult,
    VehiclePresence,
)


class TestCameraClassificationService:
    """Unit tests for CameraClassificationService."""

    def test_default_backend_is_brightness(self):
        svc = CameraClassificationService()
        assert svc.backend_name == "brightness_heuristic"

    def test_classify_returns_result(self):
        svc = CameraClassificationService()
        # Create a dummy image (bright bytes — should be ABSENT)
        bright_image = bytes([200] * 5000)
        result = svc.classify(bright_image)
        assert isinstance(result, ClassificationResult)
        assert result.method == "brightness_heuristic"
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_dark_image_suggests_present(self):
        svc = CameraClassificationService()
        # Very dark bytes in the middle
        dark_image = bytes([30] * 5000)
        result = svc.classify(dark_image)
        assert result.presence == VehiclePresence.PRESENT
        assert result.confidence > 0.0

    def test_classify_bright_image_suggests_absent(self):
        svc = CameraClassificationService()
        bright_image = bytes([220] * 5000)
        result = svc.classify(bright_image)
        assert result.presence == VehiclePresence.ABSENT
        assert result.confidence > 0.0

    def test_classify_medium_image_uncertain(self):
        svc = CameraClassificationService()
        # Mid-range bytes
        medium_image = bytes([130] * 5000)
        result = svc.classify(medium_image)
        assert result.presence == VehiclePresence.UNCERTAIN

    def test_classify_too_small_image(self):
        svc = CameraClassificationService()
        tiny_image = bytes([50] * 10)
        result = svc.classify(tiny_image)
        assert result.presence == VehiclePresence.UNCERTAIN
        assert result.confidence == 0.0
        assert result.metadata.get("error") == "image_too_small"

    def test_classify_empty_bytes(self):
        svc = CameraClassificationService()
        result = svc.classify(b"")
        assert result.presence == VehiclePresence.UNCERTAIN

    def test_unknown_backend_falls_back(self):
        svc = CameraClassificationService(backend="nonexistent")
        image = bytes([100] * 5000)
        result = svc.classify(image)
        assert result.method == "brightness_heuristic"


class TestCameraEndpointClassification:
    """Integration tests for camera upload with ?classify=true."""

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        from app import create_app, db

        db_file = tmp_path / "camera_classify_test.db"
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
        monkeypatch.setenv("SECRET_KEY", "cam-test-secret-key-1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "cam-test-jwt-secret-1234567890")
        monkeypatch.setenv("PRISM_CAMERA_UPLOAD_TOKEN", "test-token-123")

        app = create_app()
        app.config.update(TESTING=True)

        with app.app_context():
            db.create_all()

        with app.test_client() as c:
            yield c

    def test_upload_without_classify(self, client):
        resp = client.post(
            "/api/v1/camera/upload",
            data=bytes([100] * 1000),
            content_type="image/jpeg",
            headers={
                "X-Camera-ID": "cam-01",
                "X-Camera-Token": "test-token-123",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "classification" not in data

    def test_upload_with_classify(self, client):
        resp = client.post(
            "/api/v1/camera/upload?classify=true",
            data=bytes([100] * 1000),
            content_type="image/jpeg",
            headers={
                "X-Camera-ID": "cam-02",
                "X-Camera-Token": "test-token-123",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "classification" in data
        assert "presence" in data["classification"]
        assert "confidence" in data["classification"]
        assert "method" in data["classification"]

    def test_upload_classify_false_no_classification(self, client):
        resp = client.post(
            "/api/v1/camera/upload?classify=false",
            data=bytes([100] * 1000),
            content_type="image/jpeg",
            headers={
                "X-Camera-ID": "cam-03",
                "X-Camera-Token": "test-token-123",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "classification" not in data
