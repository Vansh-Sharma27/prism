"""ML model training pipeline for PRISM occupancy prediction.

Loads existing training data, generates synthetic data, combines them,
engineers features, trains a RandomForestRegressor, evaluates, and saves.

Usage:
    python -m app.ml.train_model
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from app.ml.feature_engineering import FEATURE_COLUMNS, engineer_features
from app.ml.synthetic_data import generate_synthetic_training_data
from app.ml.training_data import (
    CANONICAL_TRAINING_COLUMNS,
    merge_training_datasets,
    read_canonical_csv,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TRAINING_CSV = _PROJECT_ROOT / "data" / "combined_training.csv"
_DEFAULT_MODEL_PATH = _PROJECT_ROOT / "ml" / "models" / "occupancy_predictor.pkl"
_MIN_ROWS_AFTER_FEATURES = 20


def train_occupancy_model(
    training_csv_path: Path | None = None,
    output_model_path: Path | None = None,
    synthetic_rows: int = 1500,
    seed: int = 42,
) -> dict[str, Any]:
    """Train a Random Forest model for zone-level occupancy prediction.

    Args:
        training_csv_path: Path to existing CSV training data (optional).
        output_model_path: Where to save the trained .pkl model.
        synthetic_rows: Number of synthetic rows to generate.
        seed: Random seed for reproducibility.

    Returns:
        Dict with evaluation metrics: r2, mae, n_train, n_test, feature_importances.

    Raises:
        ValueError: If insufficient data after feature engineering.
    """
    csv_path = training_csv_path or _DEFAULT_TRAINING_CSV
    model_path = output_model_path or _DEFAULT_MODEL_PATH

    # Load existing training data if available
    existing_rows: list[dict[str, Any]] = []
    if csv_path.exists():
        existing_rows = read_canonical_csv(csv_path)

    # Generate synthetic data
    synthetic = generate_synthetic_training_data(n_rows=synthetic_rows, seed=seed)

    # Combine datasets
    combined = merge_training_datasets(existing_rows, synthetic)

    # Convert to DataFrame
    df = pd.DataFrame(combined, columns=list(CANONICAL_TRAINING_COLUMNS))

    # Engineer features
    df_features = engineer_features(df)

    if len(df_features) < _MIN_ROWS_AFTER_FEATURES:
        raise ValueError(
            f"Insufficient training data: {len(df_features)} rows after feature "
            f"engineering (minimum {_MIN_ROWS_AFTER_FEATURES} required). "
            f"Increase synthetic_rows or add more real data."
        )

    # Prepare features and target
    # Re-sort by global timestamp for proper temporal holdout split
    # (engineer_features sorts by zone_id + time; we need time-only order)
    df_features = df_features.sort_values(
        by="timestamp_unix",
        key=lambda col: pd.to_numeric(col, errors="coerce").fillna(0),
    ).reset_index(drop=True)
    X = df_features[list(FEATURE_COLUMNS)].values.astype(np.float64)
    y = df_features["occupancy_pct"].values.astype(np.float64)

    # Time-series aware split: last 20% for testing (no shuffling)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    # Train Random Forest
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))

    # Feature importances
    feature_importances = {
        name: round(float(imp), 6)
        for name, imp in zip(FEATURE_COLUMNS, model.feature_importances_, strict=False)
    }

    # Save model
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    # Save SHA-256 sidecar for integrity verification on load
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    hash_path = model_path.with_suffix(model_path.suffix + ".sha256")
    hash_path.write_text(sha256_hash.hexdigest() + "\n")

    return {
        "r2": round(r2, 4),
        "mae": round(mae, 2),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "feature_importances": feature_importances,
    }


if __name__ == "__main__":
    print("PRISM ML Training Pipeline")
    print("=" * 50)
    metrics = train_occupancy_model()
    print(f"R² Score:  {metrics['r2']:.4f}")
    print(f"MAE:       {metrics['mae']:.2f}%")
    print(f"Train set: {metrics['n_train']} rows")
    print(f"Test set:  {metrics['n_test']} rows")
    print()
    print("Feature Importances:")
    sorted_fi = sorted(
        metrics["feature_importances"].items(), key=lambda x: x[1], reverse=True
    )
    for name, importance in sorted_fi:
        print(f"  {name:35s} {importance:.4f}")
    print()
    print(f"Model saved to: {_DEFAULT_MODEL_PATH}")
    sys.exit(0)
