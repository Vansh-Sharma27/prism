#!/usr/bin/env python3
"""Export PRISM sensor readings as zone-level time-bucketed training data.

Reads SensorReading joined with ParkingSlot/Zone, aggregates to fixed time
buckets, and writes a canonical training CSV.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "prism_training_export.csv"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app, db  # noqa: E402
from app.ml.training_data import CANONICAL_TRAINING_COLUMNS, write_canonical_csv  # noqa: E402
from app.models.parking import ParkingSlot, SensorReading, Zone  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export PRISM sensor readings as zone-level bucketed training data"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--lot-id",
        default=None,
        help="Optional lot_id filter",
    )
    parser.add_argument(
        "--bucket-minutes",
        type=int,
        default=15,
        help="Time bucket size in minutes (default: 15)",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Optional inclusive start timestamp (ISO8601)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional inclusive end timestamp (ISO8601)",
    )
    return parser


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _bucket_key(ts: datetime, bucket_minutes: int) -> datetime:
    """Round a timestamp down to the start of its bucket."""
    minute_floor = (ts.minute // bucket_minutes) * bucket_minutes
    return ts.replace(minute=minute_floor, second=0, microsecond=0)


def _aggregate_readings_to_zone_buckets(
    readings: Sequence[Any],
    bucket_minutes: int,
) -> list[dict[str, Any]]:
    """Aggregate SensorReading rows into zone-level time buckets.

    For each bucket, takes the latest reading per slot, then computes
    zone-level occupancy percentage, average distance, and coverage.
    """
    # Step 1: collect latest reading per (zone_id, bucket, slot_id)
    zone_total_slots: dict[str, int] = {}

    # Pre-compute zone slot counts and slot metadata in bulk (avoids N+1 queries)
    for zone in Zone.query.all():
        count = zone.slots.count()
        zone_total_slots[zone.id] = count

    slot_lookup: dict[str, ParkingSlot] = {
        slot.id: slot for slot in ParkingSlot.query.all()
    }

    latest_per_slot: dict[tuple[str, datetime, str], dict[str, Any]] = {}  # (zone_id, bucket, slot_id) -> data

    for reading in readings:
        slot = slot_lookup.get(reading.slot_id)
        if slot is None or slot.zone_id is None:
            continue

        bucket = _bucket_key(reading.timestamp, bucket_minutes)
        key = (slot.zone_id, bucket, reading.slot_id)

        existing = latest_per_slot.get(key)
        if existing is None or reading.timestamp > existing["timestamp"]:
            latest_per_slot[key] = {
                "timestamp": reading.timestamp,
                "lot_id": slot.lot_id,
                "zone_id": slot.zone_id,
                "slot_id": reading.slot_id,
                "is_occupied": reading.is_occupied,
                "distance_cm": reading.distance_cm,
            }

    # Step 2: aggregate to zone-bucket level
    zone_buckets: dict[tuple[str, datetime], list[dict[str, Any]]] = {}
    for (zone_id, bucket, _slot_id), data in latest_per_slot.items():
        zone_bucket_key = (zone_id, bucket)
        zone_buckets.setdefault(zone_bucket_key, []).append(data)

    # Step 3: compute zone-level stats per bucket
    rows: list[dict[str, Any]] = []
    for (zone_id, bucket), slot_data_list in sorted(zone_buckets.items()):
        total = zone_total_slots.get(zone_id, len(slot_data_list))
        occupied = sum(1 for d in slot_data_list if d["is_occupied"])
        distances = [d["distance_cm"] for d in slot_data_list if d["distance_cm"] is not None]
        avg_distance = round(sum(distances) / len(distances), 1) if distances else 0.0
        coverage = round((len(slot_data_list) / total) * 100, 1) if total > 0 else 0.0
        occupancy_pct = round((occupied / total) * 100, 1) if total > 0 else 0.0

        bucket_utc = bucket.replace(tzinfo=timezone.utc) if bucket.tzinfo is None else bucket
        rows.append(
            {
                "timestamp_iso": bucket_utc.isoformat(),
                "timestamp_unix": int(bucket_utc.timestamp()),
                "lot_id": slot_data_list[0]["lot_id"],
                "zone_id": zone_id,
                "occupied_slots": occupied,
                "total_slots": total,
                "occupancy_pct": occupancy_pct,
                "avg_distance_cm": avg_distance,
                "coverage_pct": coverage,
                "source_dataset": "prism",
            }
        )

    rows.sort(key=lambda r: (r["timestamp_iso"], r["zone_id"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    """Entry point. Accepts optional argv for testability."""
    load_dotenv(BACKEND_DIR / ".env")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.bucket_minutes <= 0:
        print("Error: --bucket-minutes must be greater than 0")
        return 2

    app = create_app()

    with app.app_context():
        query = SensorReading.query.order_by(SensorReading.timestamp.asc())

        if args.lot_id:
            slot_ids = [
                s.id for s in ParkingSlot.query.filter_by(lot_id=args.lot_id).all()
            ]
            query = query.filter(SensorReading.slot_id.in_(slot_ids))

        start = _parse_iso(args.start)
        if start:
            query = query.filter(SensorReading.timestamp >= start)
        end = _parse_iso(args.end)
        if end:
            query = query.filter(SensorReading.timestamp <= end)

        readings = query.all()
        rows = _aggregate_readings_to_zone_buckets(readings, args.bucket_minutes)

    output_path = Path(args.output).expanduser().resolve()
    count = write_canonical_csv(rows, output_path)
    print(f"Exported {count} zone-bucket rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
