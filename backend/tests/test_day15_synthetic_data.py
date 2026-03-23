"""Tests for the synthetic training data generator (Day 15).

Written FIRST per TDD — these define the contract before any implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.ml.synthetic_data import generate_synthetic_training_data
from app.ml.training_data import CANONICAL_TRAINING_COLUMNS, validate_canonical_row


class TestSyntheticDataSchema:
    """Verify generated data conforms to the canonical training schema."""

    def test_returns_canonical_columns(self):
        rows = generate_synthetic_training_data(n_rows=50, seed=42)
        for row in rows:
            assert set(CANONICAL_TRAINING_COLUMNS).issubset(set(row.keys())), (
                f"Row missing columns: {set(CANONICAL_TRAINING_COLUMNS) - set(row.keys())}"
            )

    def test_validates_all_rows(self):
        rows = generate_synthetic_training_data(n_rows=200, seed=42)
        for i, row in enumerate(rows):
            errors = validate_canonical_row(row)
            assert errors == [], f"Row {i} validation errors: {errors}"

    def test_source_dataset_is_synthetic(self):
        rows = generate_synthetic_training_data(n_rows=50, seed=42)
        for row in rows:
            assert row["source_dataset"] == "synthetic"


class TestSyntheticDataCount:
    """Verify row count and determinism."""

    @pytest.mark.parametrize("n_rows", [50, 200, 1500])
    def test_produces_requested_row_count(self, n_rows: int):
        rows = generate_synthetic_training_data(n_rows=n_rows, seed=42)
        assert len(rows) == n_rows

    def test_deterministic_with_same_seed(self):
        rows_a = generate_synthetic_training_data(n_rows=100, seed=99)
        rows_b = generate_synthetic_training_data(n_rows=100, seed=99)
        assert rows_a == rows_b

    def test_different_seed_produces_different_data(self):
        rows_a = generate_synthetic_training_data(n_rows=100, seed=1)
        rows_b = generate_synthetic_training_data(n_rows=100, seed=2)
        pcts_a = [r["occupancy_pct"] for r in rows_a]
        pcts_b = [r["occupancy_pct"] for r in rows_b]
        assert pcts_a != pcts_b


class TestSyntheticDataRange:
    """Verify occupancy values are within valid bounds."""

    def test_occupancy_pct_in_range(self):
        rows = generate_synthetic_training_data(n_rows=500, seed=42)
        for i, row in enumerate(rows):
            pct = float(row["occupancy_pct"])
            assert 0.0 <= pct <= 100.0, f"Row {i}: occupancy_pct={pct} out of range"

    def test_occupied_slots_lte_total_slots(self):
        rows = generate_synthetic_training_data(n_rows=500, seed=42)
        for i, row in enumerate(rows):
            occupied = int(row["occupied_slots"])
            total = int(row["total_slots"])
            assert 0 <= occupied <= total, (
                f"Row {i}: occupied={occupied} > total={total}"
            )


class TestSyntheticDataCoverage:
    """Verify the data covers multiple zones, days, and hours."""

    def test_covers_multiple_zones(self):
        rows = generate_synthetic_training_data(n_rows=500, seed=42)
        zones = {row["zone_id"] for row in rows}
        assert len(zones) >= 3, f"Only {len(zones)} zones: {zones}"

    def test_covers_all_weekdays(self):
        rows = generate_synthetic_training_data(n_rows=1500, seed=42)
        days = set()
        for row in rows:
            dt = datetime.fromisoformat(str(row["timestamp_iso"]))
            days.add(dt.weekday())
        assert len(days) == 7, f"Missing days of week: {days}"

    def test_covers_business_and_night_hours(self):
        rows = generate_synthetic_training_data(n_rows=1500, seed=42)
        hours = set()
        for row in rows:
            dt = datetime.fromisoformat(str(row["timestamp_iso"]))
            hours.add(dt.hour)
        assert any(h in hours for h in [8, 9, 10]), "No morning rush hours"
        assert any(h in hours for h in [22, 23, 0, 1]), "No night hours"


class TestSyntheticDataTemporalPatterns:
    """Verify realistic temporal occupancy patterns."""

    def test_morning_rush_higher_than_night(self):
        rows = generate_synthetic_training_data(n_rows=1500, seed=42)
        morning = []
        night = []
        for row in rows:
            dt = datetime.fromisoformat(str(row["timestamp_iso"]))
            pct = float(row["occupancy_pct"])
            if 8 <= dt.hour <= 10:
                morning.append(pct)
            elif dt.hour >= 22 or dt.hour <= 5:
                night.append(pct)

        assert morning and night, "Not enough data points for comparison"
        avg_morning = sum(morning) / len(morning)
        avg_night = sum(night) / len(night)
        assert avg_morning > avg_night, (
            f"Morning avg ({avg_morning:.1f}%) should be higher than night ({avg_night:.1f}%)"
        )

    def test_weekday_higher_than_weekend(self):
        rows = generate_synthetic_training_data(n_rows=1500, seed=42)
        weekday_pcts = []
        weekend_pcts = []
        for row in rows:
            dt = datetime.fromisoformat(str(row["timestamp_iso"]))
            pct = float(row["occupancy_pct"])
            if dt.weekday() < 5:
                weekday_pcts.append(pct)
            else:
                weekend_pcts.append(pct)

        assert weekday_pcts and weekend_pcts, "Not enough data for comparison"
        avg_weekday = sum(weekday_pcts) / len(weekday_pcts)
        avg_weekend = sum(weekend_pcts) / len(weekend_pcts)
        assert avg_weekday > avg_weekend, (
            f"Weekday avg ({avg_weekday:.1f}%) should be higher than weekend ({avg_weekend:.1f}%)"
        )

    def test_timestamps_are_sorted(self):
        rows = generate_synthetic_training_data(n_rows=500, seed=42)
        timestamps = [int(row["timestamp_unix"]) for row in rows]
        assert timestamps == sorted(timestamps), "Rows should be sorted by timestamp"
