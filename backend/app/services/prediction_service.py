"""PredictionService for PRISM occupancy prediction.

Loads a trained RandomForest model from disk and provides predictions
for zone-level occupancy. Gracefully degrades to None when no model
is available, allowing the endpoint to fall back to heuristics.
"""

from __future__ import annotations

import hashlib
import logging
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.ml.feature_engineering import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


def _compute_file_sha256(path: Path) -> str:
    """Return hex SHA-256 digest for a file, reading in 64 KiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_model_integrity(model_path: Path) -> bool:
    """Verify model file SHA-256 against its sidecar .sha256 file.

    Returns True if no sidecar exists (backwards compat) or if hash matches.
    Returns False if sidecar exists but hash does not match.
    """
    hash_path = model_path.with_suffix(model_path.suffix + ".sha256")
    if not hash_path.exists():
        logger.info("PredictionService: no .sha256 sidecar found, skipping integrity check")
        return True

    try:
        raw = hash_path.read_text().strip()
        if not raw:
            logger.error("PredictionService: .sha256 sidecar is empty at %s", hash_path)
            return False
        expected_hash = raw.split()[0].lower()
    except (IndexError, OSError, UnicodeDecodeError) as exc:
        logger.error("PredictionService: failed to read .sha256 sidecar at %s — %s", hash_path, exc)
        return False

    try:
        actual_hash = _compute_file_sha256(model_path)
    except OSError as exc:
        logger.error("PredictionService: failed to read model file for hashing at %s — %s", model_path, exc)
        return False

    if actual_hash != expected_hash:
        logger.error(
            "PredictionService: integrity check FAILED — expected %s, got %s",
            expected_hash,
            actual_hash,
        )
        return False

    logger.info("PredictionService: SHA-256 integrity check passed")
    return True


class PredictionService:
    """Stateless prediction service backed by a persisted ML model.

    After initialization, no instance attributes are mutated.
    """

    def __init__(self, model_path: Path | str | None = None) -> None:
        self._model: Any = None

        if model_path is None:
            logger.info("PredictionService: no model path provided, predictions unavailable")
            return

        path = Path(model_path)
        if not path.exists():
            logger.warning("PredictionService: model file not found at %s", path)
            return

        if not _verify_model_integrity(path):
            logger.error("PredictionService: refusing to load model with failed integrity check")
            return

        try:
            loaded = joblib.load(path)
            if not isinstance(loaded, RandomForestRegressor):
                logger.error(
                    "PredictionService: loaded object is %s, expected RandomForestRegressor",
                    type(loaded).__name__,
                )
                return
            self._model = loaded
            logger.info("PredictionService: loaded model from %s", path)
        except Exception:
            logger.exception("PredictionService: failed to load model from %s", path)
            self._model = None

    @property
    def is_available(self) -> bool:
        """Whether a trained model is loaded and ready for predictions."""
        return self._model is not None

    def predict(
        self,
        *,
        target_hour: int,
        target_day_of_week: int,
        current_occupancy_pct: float,
        previous_occupancy_pct: float | None = None,
        is_klcc_source: bool = False,
    ) -> float | None:
        """Predict zone-level occupancy percentage.

        Args:
            target_hour: Hour of day (0-23).
            target_day_of_week: Day of week (0=Monday, 6=Sunday).
            current_occupancy_pct: Most recent known occupancy (0-100).
            previous_occupancy_pct: Second-most recent occupancy (optional).
            is_klcc_source: Whether this zone is from the KLCC dataset.

        Returns:
            Predicted occupancy percentage clamped to [0.0, 100.0],
            or None if no model is loaded.
        """
        if not self.is_available:
            return None

        # H2: Input range validation
        if not (0 <= target_hour <= 23):
            logger.warning("predict: target_hour %s out of range 0-23", target_hour)
            return None
        if not (0 <= target_day_of_week <= 6):
            logger.warning("predict: target_day_of_week %s out of range 0-6", target_day_of_week)
            return None
        if not (0.0 <= current_occupancy_pct <= 100.0):
            logger.warning("predict: current_occupancy_pct %s out of range 0-100", current_occupancy_pct)
            return None
        if previous_occupancy_pct is not None and not (0.0 <= previous_occupancy_pct <= 100.0):
            logger.warning("predict: previous_occupancy_pct %s out of range 0-100", previous_occupancy_pct)
            return None

        prev_pct = previous_occupancy_pct if previous_occupancy_pct is not None else current_occupancy_pct

        # Build feature array matching FEATURE_COLUMNS order exactly
        features = np.array(
            [
                float(target_hour),                                          # hour_of_day
                float(target_day_of_week),                                   # day_of_week
                1.0 if target_day_of_week >= 5 else 0.0,                     # is_weekend
                math.sin(2 * math.pi * target_hour / 24),                    # hour_sin
                math.cos(2 * math.pi * target_hour / 24),                    # hour_cos
                math.sin(2 * math.pi * target_day_of_week / 7),             # dow_sin
                math.cos(2 * math.pi * target_day_of_week / 7),             # dow_cos
                float(current_occupancy_pct),                                # occupancy_pct_lag_1
                float(prev_pct),                                             # occupancy_pct_lag_2
                (float(current_occupancy_pct) + float(prev_pct)) / 2.0,     # occupancy_pct_rolling_mean_4
                1.0 if is_klcc_source else 0.0,                              # is_klcc_source
            ],
            dtype=np.float64,
        ).reshape(1, -1)

        try:
            raw_prediction = float(self._model.predict(features)[0])
        except Exception:
            logger.exception("predict: model.predict() failed, returning None")
            return None
        clamped = max(0.0, min(100.0, raw_prediction))
        return round(clamped, 1)

    def compute_trend(
        self,
        *,
        current_occupancy_pct: float,
        predicted_occupancy_pct: float,
        threshold: float = 5.0,
    ) -> str:
        """Compute occupancy trend based on current vs predicted.

        Returns "filling", "clearing", or "stable".
        """
        diff = predicted_occupancy_pct - current_occupancy_pct
        if diff > threshold:
            return "filling"
        if diff < -threshold:
            return "clearing"
        return "stable"
