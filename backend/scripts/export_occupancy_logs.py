#!/usr/bin/env python3
"""Export occupancy logs from the PRISM database to CSV for ML training."""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "day6_occupancy_logs.csv"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from app.models.parking import OccupancyLog, ParkingSlot  # noqa: E402


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO8601 timestamp string into a datetime object."""
    if not value:
        return None

    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO8601 timestamp: {value}") from exc


def to_epoch_seconds(ts: datetime) -> int:
    """Convert datetime to unix seconds, assuming UTC for naive datetimes."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    return int(ts.timestamp())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export occupancy_logs joined with parking_slots to CSV"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--lot-id",
        default=None,
        help="Optional lot_id filter",
    )
    parser.add_argument(
        "--slot-id",
        default=None,
        help="Optional slot_id filter",
    )
    parser.add_argument(
        "--start",
        type=parse_iso8601,
        default=None,
        help="Optional inclusive start timestamp (ISO8601)",
    )
    parser.add_argument(
        "--end",
        type=parse_iso8601,
        default=None,
        help="Optional inclusive end timestamp (ISO8601)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of rows to export",
    )
    return parser


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    args = build_parser().parse_args()

    if args.limit is not None and args.limit <= 0:
        print("Error: --limit must be greater than 0")
        return 2

    app = create_app()

    with app.app_context():
        query = (
            OccupancyLog.query.join(ParkingSlot, OccupancyLog.slot_id == ParkingSlot.id)
            .with_entities(OccupancyLog, ParkingSlot)
        )

        if args.lot_id:
            query = query.filter(ParkingSlot.lot_id == args.lot_id)
        if args.slot_id:
            query = query.filter(OccupancyLog.slot_id == args.slot_id)
        if args.start:
            query = query.filter(OccupancyLog.timestamp >= args.start)
        if args.end:
            query = query.filter(OccupancyLog.timestamp <= args.end)

        query = query.order_by(OccupancyLog.timestamp.asc())

        if args.limit is not None:
            query = query.limit(args.limit)

        rows = query.all()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "timestamp_iso",
                "timestamp_unix",
                "slot_id",
                "lot_id",
                "zone_id",
                "slot_number",
                "status",
                "is_occupied",
                "distance_cm",
                "hour_of_day",
                "day_of_week",
            ]
        )

        for log, slot in rows:
            timestamp = log.timestamp
            epoch = to_epoch_seconds(timestamp)
            timestamp_utc = datetime.fromtimestamp(epoch, tz=timezone.utc)

            writer.writerow(
                [
                    timestamp_utc.isoformat(),
                    epoch,
                    log.slot_id,
                    slot.lot_id,
                    slot.zone_id or "",
                    slot.slot_number,
                    log.status,
                    int(log.status == "occupied"),
                    log.distance_cm if log.distance_cm is not None else "",
                    timestamp_utc.hour,
                    timestamp_utc.weekday(),
                ]
            )

    print(f"Exported {len(rows)} occupancy log rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
