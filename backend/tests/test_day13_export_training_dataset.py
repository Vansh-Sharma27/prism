from __future__ import annotations

import csv
import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import SensorReading
from seed import seed_campus_data

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_training_dataset.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("export_training_dataset", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def seeded_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "day13_export.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "day13-export-secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "day13-export-jwt-secret-key-123456")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_campus_data(admin_email="admin@prism.local", admin_password="Admin@12345")
        db.session.add_all(
            [
                SensorReading(
                    slot_id="lot-a-slot-1",
                    distance_cm=90.0,
                    is_occupied=False,
                    timestamp=datetime(2026, 3, 16, 10, 2, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-2",
                    distance_cm=10.0,
                    is_occupied=True,
                    timestamp=datetime(2026, 3, 16, 10, 3, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-3",
                    distance_cm=20.0,
                    is_occupied=True,
                    timestamp=datetime(2026, 3, 16, 10, 14, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-1",
                    distance_cm=95.0,
                    is_occupied=False,
                    timestamp=datetime(2026, 3, 16, 10, 16, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-2",
                    distance_cm=85.0,
                    is_occupied=False,
                    timestamp=datetime(2026, 3, 16, 10, 20, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-3",
                    distance_cm=11.0,
                    is_occupied=True,
                    timestamp=datetime(2026, 3, 16, 10, 27, 0),
                ),
                SensorReading(
                    slot_id="lot-a-slot-1",
                    distance_cm=9.0,
                    is_occupied=True,
                    timestamp=datetime(2026, 3, 16, 10, 29, 0),
                ),
            ]
        )
        db.session.commit()

    return app


def test_export_training_dataset_writes_bucketed_zone_rows(seeded_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output_path = tmp_path / "training_export.csv"
    module = _load_script_module()

    with seeded_app.app_context():
        exit_code = module.main(
            [
                "--output",
                str(output_path),
                "--lot-id",
                "lot-a",
                "--bucket-minutes",
                "15",
            ]
        )

    assert exit_code == 0
    assert output_path.exists()

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["timestamp_iso"] for row in rows] == [
        "2026-03-16T10:00:00+00:00",
        "2026-03-16T10:15:00+00:00",
    ]
    assert [row["zone_id"] for row in rows] == ["zone-a-east", "zone-a-east"]
    assert rows[0]["occupied_slots"] == "2"
    assert rows[0]["total_slots"] == "3"
    assert rows[0]["occupancy_pct"] == "66.7"
    assert rows[0]["avg_distance_cm"] == "40.0"
    assert rows[0]["coverage_pct"] == "100.0"
    assert rows[0]["source_dataset"] == "prism"

    assert rows[1]["occupied_slots"] == "2"
    assert rows[1]["total_slots"] == "3"
    assert rows[1]["occupancy_pct"] == "66.7"
    assert rows[1]["avg_distance_cm"] == "35.0"
    assert rows[1]["coverage_pct"] == "100.0"


def test_export_training_dataset_rejects_invalid_bucket_minutes(seeded_app, tmp_path: Path):
    output_path = tmp_path / "invalid.csv"
    module = _load_script_module()

    with seeded_app.app_context():
        exit_code = module.main(
            [
                "--output",
                str(output_path),
                "--bucket-minutes",
                "0",
            ]
        )

    assert exit_code == 2
    assert not output_path.exists()
