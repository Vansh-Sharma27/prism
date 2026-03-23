"""PredictionService for PRISM occupancy prediction.

Loads a trained RandomForest model from disk and provides predictions
for zone-level occupancy. Gracefully degrades to None when no model
is available, allowing the endpoint to fall back to heuristics.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.ml.feature_engineering import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


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

        try:
            self._model = joblib.load(path)
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

        raw_prediction = float(self._model.predict(features)[0])
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

        Returns "filling", "emptying", or "stable".
        """
        diff = predicted_occupancy_pct - current_occupancy_pct
        if diff > threshold:
            return "filling"
        if diff < -threshold:
            return "emptying"
        return "stable"
