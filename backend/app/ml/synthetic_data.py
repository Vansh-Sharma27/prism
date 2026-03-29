"""Deterministic synthetic training data generator for PRISM ML pipeline.

Generates realistic campus parking occupancy data with temporal patterns:
- Morning rush (8-10 AM): high occupancy
- Midday (11-14): moderate
- Afternoon peak (14-17): high again
- Evening/night: low occupancy
- Weekdays busier than weekends
- Per-zone variation in base utilization
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

# Campus zones with different characteristics
_ZONES = (
    {"zone_id": "campus-zone-a", "lot_id": "campus-main", "total_slots": 50, "base_factor": 1.0},
    {"zone_id": "campus-zone-b", "lot_id": "campus-main", "total_slots": 80, "base_factor": 0.85},
    {"zone_id": "campus-zone-c", "lot_id": "campus-east", "total_slots": 30, "base_factor": 1.1},
    {"zone_id": "campus-zone-d", "lot_id": "campus-east", "total_slots": 60, "base_factor": 0.75},
)

# Time-of-day occupancy curve (hour -> base occupancy percentage)
_HOURLY_CURVE: dict[int, float] = {
    0: 3.0, 1: 2.0, 2: 2.0, 3: 2.0, 4: 2.0, 5: 3.0,
    6: 10.0, 7: 25.0,
    8: 65.0, 9: 78.0, 10: 72.0,
    11: 58.0, 12: 50.0, 13: 48.0,
    14: 62.0, 15: 74.0, 16: 70.0, 17: 55.0,
    18: 35.0, 19: 18.0,
    20: 12.0, 21: 8.0, 22: 5.0, 23: 4.0,
}

# Day-of-week multiplier (0=Monday, 6=Sunday)
_DAY_MULTIPLIER: tuple[float, ...] = (
    1.0,   # Monday
    0.95,  # Tuesday
    1.05,  # Wednesday
    1.0,   # Thursday
    0.90,  # Friday
    0.35,  # Saturday
    0.20,  # Sunday
)

_NOISE_SIGMA = 4.0  # Gaussian noise standard deviation (percentage points)
_INTERVAL_MINUTES = 15  # Data point frequency
_SPAN_DAYS = 28  # 4 weeks of data


def _occupancy_for_time(
    hour: int,
    minute: int,
    day_of_week: int,
    zone_base_factor: float,
    rng: np.random.Generator,
) -> float:
    """Compute a realistic occupancy percentage for a given time and zone."""
    # Interpolate between hourly curve values for smoother transitions
    current_base = _HOURLY_CURVE[hour]
    next_hour = (hour + 1) % 24
    next_base = _HOURLY_CURVE[next_hour]
    fraction = minute / 60.0
    interpolated = current_base + (next_base - current_base) * fraction

    # Apply day-of-week multiplier
    day_mult = _DAY_MULTIPLIER[day_of_week]

    # Apply zone-specific base factor
    raw = interpolated * day_mult * zone_base_factor

    # Add Gaussian noise
    noise = rng.normal(0, _NOISE_SIGMA)
    result = raw + noise

    # Clamp to [0, 100]
    return round(max(0.0, min(100.0, result)), 1)


def generate_synthetic_training_data(
    n_rows: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate deterministic synthetic campus parking training data.

    Args:
        n_rows: Number of rows to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of dicts conforming to CANONICAL_TRAINING_COLUMNS, sorted by timestamp_unix.
    """
    rng = np.random.default_rng(seed)

    # Calculate how many timestamps per zone we need
    n_zones = len(_ZONES)
    rows_per_zone = max(1, math.ceil(n_rows / n_zones))

    # Generate timestamps spanning _SPAN_DAYS at _INTERVAL_MINUTES intervals
    start_dt = datetime(2026, 2, 23, 0, 0, 0, tzinfo=UTC)
    total_intervals = (_SPAN_DAYS * 24 * 60) // _INTERVAL_MINUTES

    # If we need more rows per zone than available intervals, reduce interval
    if rows_per_zone > total_intervals:
        interval_indices = list(range(total_intervals))
        # Repeat to fill
        repeats = math.ceil(rows_per_zone / total_intervals)
        interval_indices = (interval_indices * repeats)[:rows_per_zone]
    else:
        # Sample evenly spaced intervals
        step = total_intervals / rows_per_zone
        interval_indices = [int(i * step) for i in range(rows_per_zone)]

    all_rows: list[dict[str, Any]] = []

    for zone_info in _ZONES:
        zone_id = zone_info["zone_id"]
        lot_id = zone_info["lot_id"]
        total_slots = zone_info["total_slots"]
        base_factor = zone_info["base_factor"]

        for idx in interval_indices:
            dt = start_dt + timedelta(minutes=idx * _INTERVAL_MINUTES)
            hour = dt.hour
            minute = dt.minute
            day_of_week = dt.weekday()

            occ_pct = _occupancy_for_time(hour, minute, day_of_week, base_factor, rng)
            occupied_slots = int(round(occ_pct / 100.0 * total_slots))
            occupied_slots = max(0, min(total_slots, occupied_slots))

            # Recompute pct from integer slots for consistency
            actual_pct = round((occupied_slots / total_slots) * 100, 1) if total_slots > 0 else 0.0

            all_rows.append({
                "timestamp_iso": dt.isoformat(),
                "timestamp_unix": int(dt.timestamp()),
                "lot_id": lot_id,
                "zone_id": zone_id,
                "occupied_slots": occupied_slots,
                "total_slots": total_slots,
                "occupancy_pct": actual_pct,
                "avg_distance_cm": "",
                "coverage_pct": 100.0,
                "source_dataset": "synthetic",
            })

    # Sort by timestamp, then zone for deterministic ordering
    all_rows.sort(key=lambda r: (int(r["timestamp_unix"]), str(r["zone_id"])))

    # Trim to exactly n_rows
    return all_rows[:n_rows]
