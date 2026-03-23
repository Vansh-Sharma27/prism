"""Tests for PredictionService (Day 15).

Written FIRST per TDD — validates prediction service contract including
model loading, prediction clamping, trend computation, and graceful fallback.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.ml.feature_engineering import FEATURE_COLUMNS


@pytest.fixture()
def trained_model_path(tmp_path: Path) -> Path:
    """Train a small model and return its path."""
    from app.ml.train_model import train_occupancy_model

    model_path = tmp_path / "test_model.pkl"
    train_occupancy_model(
        training_csv_path=None,
        output_model_path=model_path,
        synthetic_rows=300,
        seed=42,
    )
    return model_path


class TestPredictionServiceLoading:
    """Verify model loading and availability."""

    def test_loads_model_from_path(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)
        assert service.is_available is True

    def test_graceful_fallback_when_no_model(self, tmp_path: Path):
        from app.services.prediction_service import PredictionService

        nonexistent = tmp_path / "does_not_exist.pkl"
        service = PredictionService(model_path=nonexistent)
        assert service.is_available is False
        result = service.predict(
            target_hour=10,
            target_day_of_week=2,
            current_occupancy_pct=50.0,
        )
        assert result is None

    def test_graceful_fallback_with_none_path(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        assert service.is_available is False


class TestPredictionServicePredict:
    """Verify predictions are valid and responsive to inputs."""

    def test_predict_returns_clamped_float(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)
        result = service.predict(
            target_hour=10,
            target_day_of_week=2,
            current_occupancy_pct=60.0,
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_predict_with_different_hours_varies(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)
        morning = service.predict(target_hour=9, target_day_of_week=1, current_occupancy_pct=50.0)
        night = service.predict(target_hour=23, target_day_of_week=1, current_occupancy_pct=50.0)
        # Morning prediction should generally differ from night
        assert morning != night, "Model should produce different predictions for different hours"

    def test_predict_with_zone_context(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)
        low_occ = service.predict(
            target_hour=10,
            target_day_of_week=2,
            current_occupancy_pct=10.0,
        )
        high_occ = service.predict(
            target_hour=10,
            target_day_of_week=2,
            current_occupancy_pct=90.0,
        )
        # Different current occupancy should influence prediction (via lag features)
        assert low_occ != high_occ, "Lag features should cause different predictions"

    def test_predict_with_previous_occupancy(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)
        result = service.predict(
            target_hour=14,
            target_day_of_week=3,
            current_occupancy_pct=65.0,
            previous_occupancy_pct=55.0,
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_predict_builds_correct_feature_count(self, trained_model_path: Path):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=trained_model_path)

        # Patch the model's predict to capture the input shape
        original_predict = service._model.predict
        captured_inputs = []

        def capture_predict(X):
            captured_inputs.append(X)
            return original_predict(X)

        service._model.predict = capture_predict
        service.predict(target_hour=10, target_day_of_week=2, current_occupancy_pct=50.0)

        assert len(captured_inputs) == 1
        assert captured_inputs[0].shape == (1, len(FEATURE_COLUMNS)), (
            f"Expected {len(FEATURE_COLUMNS)} features, got shape {captured_inputs[0].shape}"
        )


class TestPredictionServiceTrend:
    """Verify trend computation logic."""

    def test_trend_filling(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        trend = service.compute_trend(current_occupancy_pct=40.0, predicted_occupancy_pct=50.0)
        assert trend == "filling"

    def test_trend_clearing(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        trend = service.compute_trend(current_occupancy_pct=60.0, predicted_occupancy_pct=50.0)
        assert trend == "clearing"

    def test_trend_stable(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        trend = service.compute_trend(current_occupancy_pct=50.0, predicted_occupancy_pct=53.0)
        assert trend == "stable"

    def test_trend_at_exact_threshold(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        # At exactly +5.0, should be stable (threshold is >, not >=)
        trend = service.compute_trend(current_occupancy_pct=50.0, predicted_occupancy_pct=55.0)
        assert trend == "stable"

    def test_trend_custom_threshold(self):
        from app.services.prediction_service import PredictionService

        service = PredictionService(model_path=None)
        # With threshold=3, a +4 change should be "filling"
        trend = service.compute_trend(
            current_occupancy_pct=50.0,
            predicted_occupancy_pct=54.0,
            threshold=3.0,
        )
        assert trend == "filling"
