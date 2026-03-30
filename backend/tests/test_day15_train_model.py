"""Tests for the ML model training pipeline (Day 15).

Written FIRST per TDD — validates the training script contract.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pytest


class TestTrainModel:
    """Verify the training pipeline produces a valid, performant model."""

    def test_produces_pkl_file(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=300,
            seed=42,
        )
        assert output_path.exists(), "Model file was not created"
        assert output_path.stat().st_size > 0, "Model file is empty"

    def test_r2_above_threshold(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        metrics = train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=1500,
            seed=42,
        )
        assert metrics["r2"] >= 0.85, f"R² = {metrics['r2']:.4f} is below the 0.85 threshold"

    def test_outputs_metrics_dict(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        metrics = train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=300,
            seed=42,
        )
        required_keys = {"r2", "mae", "n_train", "n_test", "feature_importances"}
        assert required_keys.issubset(set(metrics.keys())), f"Missing keys: {required_keys - set(metrics.keys())}"
        assert isinstance(metrics["r2"], float)
        assert isinstance(metrics["mae"], float)
        assert isinstance(metrics["n_train"], int)
        assert isinstance(metrics["n_test"], int)
        assert isinstance(metrics["feature_importances"], dict)

    def test_saved_model_is_loadable(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=300,
            seed=42,
        )
        model = joblib.load(output_path)
        assert hasattr(model, "predict"), "Loaded model lacks .predict method"

    def test_handles_insufficient_data(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            train_occupancy_model(
                training_csv_path=None,
                output_model_path=output_path,
                synthetic_rows=5,
                seed=42,
            )

    def test_mae_is_reasonable(self, tmp_path: Path):
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        metrics = train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=1500,
            seed=42,
        )
        # MAE should be below 10 percentage points for a good model
        assert metrics["mae"] < 10.0, f"MAE = {metrics['mae']:.2f}% is too high (expected < 10%)"

    def test_feature_importances_match_feature_columns(self, tmp_path: Path):
        from app.ml.feature_engineering import FEATURE_COLUMNS
        from app.ml.train_model import train_occupancy_model

        output_path = tmp_path / "model.pkl"
        metrics = train_occupancy_model(
            training_csv_path=None,
            output_model_path=output_path,
            synthetic_rows=300,
            seed=42,
        )
        fi_keys = set(metrics["feature_importances"].keys())
        expected_keys = set(FEATURE_COLUMNS)
        assert fi_keys == expected_keys, (
            f"Feature importance keys mismatch: extra={fi_keys - expected_keys}, missing={expected_keys - fi_keys}"
        )
