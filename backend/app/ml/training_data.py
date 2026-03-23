"""Canonical training-data schema, normalization, and merge helpers for PRISM ML pipeline."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


CANONICAL_TRAINING_COLUMNS: tuple[str, ...] = (
    "timestamp_iso",
    "timestamp_unix",
    "lot_id",
    "zone_id",
    "occupied_slots",
    "total_slots",
    "occupancy_pct",
    "avg_distance_cm",
    "coverage_pct",
    "source_dataset",
)

_REQUIRED_EXTERNAL_COLUMNS_KLCC = {"datetime", "location", "capacity", "available"}


def _parse_iso_to_epoch(iso_str: str) -> int:
    """Parse an ISO-8601 timestamp to Unix seconds, treating naive as UTC."""
    normalized = iso_str.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _normalize_iso(iso_str: str) -> str:
    """Normalize an ISO-8601 timestamp to a consistent UTC format."""
    normalized = iso_str.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def normalize_external_training_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize external (e.g. KLCC) dataset rows into the canonical training schema.

    Supported schemas:
        KLCC: columns datetime, location, capacity, available
    """
    if not rows:
        return []

    columns = set(rows[0].keys())

    if _REQUIRED_EXTERNAL_COLUMNS_KLCC.issubset(columns):
        return _normalize_klcc_rows(rows)

    raise ValueError(
        f"Unsupported external dataset schema. Found columns: {sorted(columns)}. "
        f"Expected KLCC columns: {sorted(_REQUIRED_EXTERNAL_COLUMNS_KLCC)}"
    )


def _normalize_klcc_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize KLCC-format rows into canonical training schema."""
    result: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        try:
            capacity = int(row["capacity"])
            available = int(row["available"])
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Row {i}: non-numeric capacity/available: "
                f"capacity={row.get('capacity')!r}, available={row.get('available')!r}"
            ) from exc
        occupied = max(0, capacity - available)
        occupancy_pct = round((occupied / capacity) * 100, 1) if capacity > 0 else 0.0
        iso_str = _normalize_iso(str(row["datetime"]))
        unix_ts = _parse_iso_to_epoch(str(row["datetime"]))

        result.append(
            {
                "timestamp_iso": iso_str,
                "timestamp_unix": unix_ts,
                "lot_id": "klcc",
                "zone_id": str(row["location"]).strip(),
                "occupied_slots": occupied,
                "total_slots": capacity,
                "occupancy_pct": occupancy_pct,
                "avg_distance_cm": "",
                "coverage_pct": 100.0,
                "source_dataset": "klcc",
            }
        )
    return result


def validate_canonical_row(row: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for a canonical training row."""
    errors: list[str] = []
    missing = set(CANONICAL_TRAINING_COLUMNS) - set(row.keys())
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
        return errors

    try:
        pct = float(row["occupancy_pct"])
        if not (0.0 <= pct <= 100.0):
            errors.append(f"occupancy_pct out of range: {pct}")
    except (TypeError, ValueError):
        errors.append(f"occupancy_pct not numeric: {row['occupancy_pct']}")

    if not str(row["timestamp_iso"]).strip():
        errors.append("timestamp_iso is empty")
    if not str(row["zone_id"]).strip():
        errors.append("zone_id is empty")

    return errors


def _safe_timestamp_unix(row: dict[str, Any]) -> int:
    """Extract timestamp_unix as int, defaulting to 0 for blank/non-numeric values."""
    raw = row.get("timestamp_unix")
    if not raw:
        return 0
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


def merge_training_datasets(
    prism_rows: list[dict[str, Any]],
    external_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge PRISM-exported and external training rows, sorted by timestamp."""
    combined = list(prism_rows) + list(external_rows)
    combined.sort(key=_safe_timestamp_unix)
    return combined


def write_canonical_csv(rows: list[dict[str, Any]], output_path: Path) -> int:
    """Write canonical training rows to a CSV file. Returns row count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CANONICAL_TRAINING_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CANONICAL_TRAINING_COLUMNS})
    return len(rows)


def read_canonical_csv(input_path: Path) -> list[dict[str, Any]]:
    """Read a canonical training CSV file into a list of dicts."""
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)
