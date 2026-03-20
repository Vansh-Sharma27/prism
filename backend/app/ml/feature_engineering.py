"""Feature engineering for PRISM ML occupancy prediction pipeline.

Transforms canonical training data into model-ready features with temporal
encodings, lag features, and rolling statistics grouped by zone.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.ml.training_data import CANONICAL_TRAINING_COLUMNS

# Features added by engineer_features()
FEATURE_COLUMNS: tuple[str, ...] = (
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "occupancy_pct_lag_1",
    "occupancy_pct_lag_2",
    "occupancy_pct_rolling_mean_4",
    "is_klcc_source",
)

_MIN_HISTORY_ROWS = 4  # need 4 prior rows for rolling_mean_4


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add temporal, cyclical, lag, and rolling features to a canonical training DataFrame.

    Returns a new DataFrame without mutating the input.
    Rows without sufficient history (first _MIN_HISTORY_ROWS per zone) are dropped.
    """
    missing = set(CANONICAL_TRAINING_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if df.empty:
        empty = df.copy()
        for col in FEATURE_COLUMNS:
            empty[col] = pd.Series(dtype="float64")
        return empty

    out = df.copy()

    out["_ts"] = pd.to_datetime(out["timestamp_iso"], utc=True)
    out = out.sort_values(["zone_id", "_ts"]).reset_index(drop=True)

    out["hour_of_day"] = out["_ts"].dt.hour
    out["day_of_week"] = out["_ts"].dt.dayofweek
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)

    out["hour_sin"] = out["hour_of_day"].apply(lambda h: math.sin(2 * math.pi * h / 24))
    out["hour_cos"] = out["hour_of_day"].apply(lambda h: math.cos(2 * math.pi * h / 24))
    out["dow_sin"] = out["day_of_week"].apply(lambda d: math.sin(2 * math.pi * d / 7))
    out["dow_cos"] = out["day_of_week"].apply(lambda d: math.cos(2 * math.pi * d / 7))

    out["occupancy_pct"] = pd.to_numeric(out["occupancy_pct"], errors="coerce")
    out["occupancy_pct_lag_1"] = out.groupby("zone_id")["occupancy_pct"].shift(1)
    out["occupancy_pct_lag_2"] = out.groupby("zone_id")["occupancy_pct"].shift(2)
    out["occupancy_pct_rolling_mean_4"] = (
        out.groupby("zone_id")["occupancy_pct"]
        .transform(lambda s: s.shift(1).rolling(window=_MIN_HISTORY_ROWS, min_periods=_MIN_HISTORY_ROWS).mean())
    )

    out["is_klcc_source"] = (out["source_dataset"] == "klcc").astype(int)

    out = out.dropna(subset=["occupancy_pct_rolling_mean_4"]).reset_index(drop=True)
    out = out.drop(columns=["_ts"])

    return out
