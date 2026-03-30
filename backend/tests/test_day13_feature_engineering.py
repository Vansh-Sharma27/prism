from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from app.ml.feature_engineering import FEATURE_COLUMNS, engineer_features
from app.ml.training_data import CANONICAL_TRAINING_COLUMNS


def _build_training_frame() -> pd.DataFrame:
    """Build a 5-row-per-zone canonical training frame with consistent counts.

    Zone zone-a-east (prism): occupancy climbs 0% -> 33% -> 33% -> 67% -> 100%
    Zone zone-b-south (klcc): occupancy climbs 0% -> 33% -> 33% -> 33% -> 67%
    """
    return pd.DataFrame(
        [
            {
                "timestamp_iso": "2026-03-16T09:00:00+00:00",
                "timestamp_unix": 1773651600,
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": 0,
                "total_slots": 3,
                "occupancy_pct": 0.0,
                "avg_distance_cm": 95.0,
                "coverage_pct": 100.0,
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T09:15:00+00:00",
                "timestamp_unix": 1773652500,
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": 1,
                "total_slots": 3,
                "occupancy_pct": 33.3,
                "avg_distance_cm": 71.0,
                "coverage_pct": 100.0,
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T09:30:00+00:00",
                "timestamp_unix": 1773653400,
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": 1,
                "total_slots": 3,
                "occupancy_pct": 33.3,
                "avg_distance_cm": 60.0,
                "coverage_pct": 100.0,
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T09:45:00+00:00",
                "timestamp_unix": 1773654300,
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": 2,
                "total_slots": 3,
                "occupancy_pct": 66.7,
                "avg_distance_cm": 35.0,
                "coverage_pct": 100.0,
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T10:00:00+00:00",
                "timestamp_unix": 1773655200,
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": 3,
                "total_slots": 3,
                "occupancy_pct": 100.0,
                "avg_distance_cm": 9.0,
                "coverage_pct": 100.0,
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T09:00:00+00:00",
                "timestamp_unix": 1773651600,
                "lot_id": "lot-b",
                "zone_id": "zone-b-south",
                "occupied_slots": 0,
                "total_slots": 3,
                "occupancy_pct": 0.0,
                "avg_distance_cm": 95.0,
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            },
            {
                "timestamp_iso": "2026-03-16T09:15:00+00:00",
                "timestamp_unix": 1773652500,
                "lot_id": "lot-b",
                "zone_id": "zone-b-south",
                "occupied_slots": 1,
                "total_slots": 3,
                "occupancy_pct": 33.3,
                "avg_distance_cm": 81.0,
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            },
            {
                "timestamp_iso": "2026-03-16T09:30:00+00:00",
                "timestamp_unix": 1773653400,
                "lot_id": "lot-b",
                "zone_id": "zone-b-south",
                "occupied_slots": 1,
                "total_slots": 3,
                "occupancy_pct": 33.3,
                "avg_distance_cm": 71.0,
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            },
            {
                "timestamp_iso": "2026-03-16T09:45:00+00:00",
                "timestamp_unix": 1773654300,
                "lot_id": "lot-b",
                "zone_id": "zone-b-south",
                "occupied_slots": 1,
                "total_slots": 3,
                "occupancy_pct": 33.3,
                "avg_distance_cm": 61.0,
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            },
            {
                "timestamp_iso": "2026-03-16T10:00:00+00:00",
                "timestamp_unix": 1773655200,
                "lot_id": "lot-b",
                "zone_id": "zone-b-south",
                "occupied_slots": 2,
                "total_slots": 3,
                "occupancy_pct": 66.7,
                "avg_distance_cm": 51.0,
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            },
        ]
    )


def test_engineer_features_adds_temporal_and_history_features_without_mutation():
    frame = _build_training_frame()
    original = deepcopy(frame.to_dict(orient="records"))

    features = engineer_features(frame)

    assert frame.to_dict(orient="records") == original
    assert list(features.columns[: len(CANONICAL_TRAINING_COLUMNS)]) == list(CANONICAL_TRAINING_COLUMNS)
    assert set(FEATURE_COLUMNS).issubset(features.columns)
    assert len(features) == 2

    east = features.loc[features["zone_id"] == "zone-a-east"].iloc[0]
    south = features.loc[features["zone_id"] == "zone-b-south"].iloc[0]

    # zone-a-east last row: 100%, lag_1=66.7, lag_2=33.3, rolling_mean_4=(0+33.3+33.3+66.7)/4=33.325
    assert east["timestamp_iso"] == "2026-03-16T10:00:00+00:00"
    assert east["hour_of_day"] == 10
    assert east["day_of_week"] == 0  # Monday
    assert east["is_weekend"] == 0
    assert east["occupancy_pct_lag_1"] == pytest.approx(66.7)
    assert east["occupancy_pct_lag_2"] == pytest.approx(33.3)
    assert east["occupancy_pct_rolling_mean_4"] == pytest.approx(33.325)
    assert east["is_klcc_source"] == 0
    assert east["hour_sin"] == pytest.approx(0.5, abs=1e-4)
    assert east["hour_cos"] == pytest.approx(-0.8660254, abs=1e-4)

    # zone-b-south last row: 66.7%, lag_1=33.3, lag_2=33.3, rolling_mean_4=(0+33.3+33.3+33.3)/4=24.975
    assert south["occupancy_pct_lag_1"] == pytest.approx(33.3)
    assert south["occupancy_pct_lag_2"] == pytest.approx(33.3)
    assert south["occupancy_pct_rolling_mean_4"] == pytest.approx(24.975)
    assert south["is_klcc_source"] == 1


def test_engineer_features_rejects_missing_required_columns():
    frame = pd.DataFrame(
        [
            {
                "timestamp_iso": "2026-03-16T09:00:00+00:00",
                "zone_id": "zone-a-east",
                "occupancy_pct": 20.0,
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        engineer_features(frame)


def test_engineer_features_returns_empty_frame_for_empty_input():
    frame = pd.DataFrame(columns=CANONICAL_TRAINING_COLUMNS)

    features = engineer_features(frame)

    assert features.empty
    assert set(CANONICAL_TRAINING_COLUMNS).issubset(features.columns)
    assert set(FEATURE_COLUMNS).issubset(features.columns)
