"""Integration tests for the updated /predict endpoint with ML model (Day 15).

Tests both ML-backed prediction and heuristic fallback behavior.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from seed import seed_campus_data


@pytest.fixture()
def _trained_model(tmp_path: Path):
    """Train a model and set the env var for the app to pick up."""
    from app.ml.train_model import train_occupancy_model

    model_path = tmp_path / "test_model.pkl"
    train_occupancy_model(
        training_csv_path=None,
        output_model_path=model_path,
        synthetic_rows=300,
        seed=42,
    )
    return model_path


@pytest.fixture()
def client_with_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _trained_model: Path):
    """Flask test client with a trained ML model loaded."""
    db_file = tmp_path / "day15_predict.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day15-secret-key-1234567890-abcdef")
    monkeypatch.setenv("JWT_SECRET_KEY", "day15-jwt-secret-key-1234567890-ab")
    monkeypatch.setenv("ML_MODEL_PATH", str(_trained_model))

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

        now = datetime.utcnow()
        for slot_id, status, dist in [
            ("lot-a-slot-1", "occupied", 7.2),
            ("lot-a-slot-2", "vacant", 88.4),
            ("lot-a-slot-3", "occupied", 9.1),
        ]:
            slot = db.session.get(ParkingSlot, slot_id)
            if slot:
                slot.is_occupied = status == "occupied"
                slot.last_status_change = now
                slot.last_telemetry_at = now
                slot.last_distance_cm = dist
        db.session.commit()

    with app.test_client() as c:
        yield c


@pytest.fixture()
def client_without_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Flask test client with no ML model (fallback mode)."""
    db_file = tmp_path / "day15_fallback.db"
    # Use a path within the project root so H1 containment check passes,
    # but pointing to a non-existent file so PredictionService has no model.
    project_root = Path(__file__).resolve().parents[1].parent
    fake_model = project_root / "ml" / "models" / "nonexistent_test_model.pkl"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day15-secret-key-1234567890-abcdef")
    monkeypatch.setenv("JWT_SECRET_KEY", "day15-jwt-secret-key-1234567890-ab")
    monkeypatch.setenv("ML_MODEL_PATH", str(fake_model))

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")

    with app.test_client() as c:
        yield c


def _auth_headers(client, email: str = "student@gla.ac.in", password: str = "StrongPass123") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class TestPredictEndpointWithModel:
    """Verify ML-backed prediction when model is loaded."""

    def test_uses_ml_model_when_available(self, client_with_model):
        headers = _auth_headers(client_with_model)
        resp = client_with_model.get(
            "/api/v1/lots/lot-a/predict?day=wednesday&time=10:00",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["model"]["status"] == "active"
        assert data["model"]["version"] == "day15-rf-v1"
        assert data["model"]["type"] == "RandomForest"

    def test_predictions_include_trend(self, client_with_model):
        headers = _auth_headers(client_with_model, email="s2@gla.ac.in")
        resp = client_with_model.get(
            "/api/v1/lots/lot-a/predict?day=monday&time=09:00",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        for zone in data["zones"]:
            assert "trend" in zone
            assert zone["trend"] in ("filling", "clearing", "stable")

    def test_predictions_have_valid_range(self, client_with_model):
        headers = _auth_headers(client_with_model, email="s3@gla.ac.in")
        resp = client_with_model.get(
            "/api/v1/lots/lot-a/predict?day=friday&time=15:00",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        for zone in data["zones"]:
            assert 0.0 <= zone["predicted_occupancy_pct"] <= 100.0


class TestPredictEndpointFallback:
    """Verify heuristic fallback when model is unavailable."""

    def test_falls_back_to_heuristic(self, client_without_model):
        headers = _auth_headers(client_without_model, email="fb1@gla.ac.in")
        resp = client_without_model.get(
            "/api/v1/lots/lot-a/predict?day=wednesday&time=10:00",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["model"]["status"] == "heuristic_fallback"

    def test_fallback_still_returns_valid_predictions(self, client_without_model):
        headers = _auth_headers(client_without_model, email="fb2@gla.ac.in")
        resp = client_without_model.get(
            "/api/v1/lots/lot-a/predict?day=thursday&time=14:00",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["zones"]) >= 1
        for zone in data["zones"]:
            assert "predicted_occupancy_pct" in zone
            assert "trend" in zone
