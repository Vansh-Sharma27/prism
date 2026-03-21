from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from app.ml.training_data import CANONICAL_TRAINING_COLUMNS, normalize_external_training_rows, validate_canonical_row


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "combine_training_data.py"



def _load_script_module():
    spec = importlib.util.spec_from_file_location("combine_training_data", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module



def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def test_normalize_external_training_rows_rejects_unsupported_schema():
    with pytest.raises(ValueError, match="Unsupported external dataset schema"):
        normalize_external_training_rows(
            [
                {
                    "when": "2026-03-16T09:00:00+00:00",
                    "where": "KLCC North",
                    "cars": "42",
                }
            ]
        )



def test_combine_training_data_merges_prism_and_klcc_rows(tmp_path: Path):
    prism_input = tmp_path / "prism.csv"
    kaggle_input = tmp_path / "klcc.csv"
    output_path = tmp_path / "combined.csv"
    module = _load_script_module()

    _write_csv(
        prism_input,
        list(CANONICAL_TRAINING_COLUMNS),
        [
            {
                "timestamp_iso": "2026-03-16T09:00:00+00:00",
                "timestamp_unix": "1773651600",
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": "1",
                "total_slots": "3",
                "occupancy_pct": "33.3",
                "avg_distance_cm": "83.0",
                "coverage_pct": "100.0",
                "source_dataset": "prism",
            },
            {
                "timestamp_iso": "2026-03-16T09:15:00+00:00",
                "timestamp_unix": "1773652500",
                "lot_id": "lot-a",
                "zone_id": "zone-a-east",
                "occupied_slots": "2",
                "total_slots": "3",
                "occupancy_pct": "66.7",
                "avg_distance_cm": "41.0",
                "coverage_pct": "100.0",
                "source_dataset": "prism",
            },
        ],
    )
    _write_csv(
        kaggle_input,
        ["datetime", "location", "capacity", "available"],
        [
            {
                "datetime": "2026-03-16T08:45:00+00:00",
                "location": "klcc-north",
                "capacity": "200",
                "available": "50",
            },
            {
                "datetime": "2026-03-16T09:30:00+00:00",
                "location": "klcc-south",
                "capacity": "120",
                "available": "30",
            },
        ],
    )

    exit_code = module.main(
        [
            "--prism-input",
            str(prism_input),
            "--kaggle-input",
            str(kaggle_input),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 4
    assert list(rows[0].keys()) == list(CANONICAL_TRAINING_COLUMNS)
    assert [row["timestamp_iso"] for row in rows] == [
        "2026-03-16T08:45:00+00:00",
        "2026-03-16T09:00:00+00:00",
        "2026-03-16T09:15:00+00:00",
        "2026-03-16T09:30:00+00:00",
    ]
    assert rows[0]["lot_id"] == "klcc"
    assert rows[0]["zone_id"] == "klcc-north"
    assert rows[0]["occupied_slots"] == "150"
    assert rows[0]["total_slots"] == "200"
    assert rows[0]["occupancy_pct"] == "75.0"
    assert rows[0]["coverage_pct"] == "100.0"
    assert rows[0]["source_dataset"] == "klcc"
    assert rows[1]["source_dataset"] == "prism"
    assert rows[3]["zone_id"] == "klcc-south"
    assert rows[3]["occupancy_pct"] == "75.0"



def test_validate_canonical_row_catches_missing_columns():
    errors = validate_canonical_row({"timestamp_iso": "2026-03-16T09:00:00+00:00"})
    assert len(errors) == 1
    assert "Missing columns" in errors[0]



def test_validate_canonical_row_catches_out_of_range_occupancy():
    row = {col: "test" for col in CANONICAL_TRAINING_COLUMNS}
    row["occupancy_pct"] = "150.0"
    errors = validate_canonical_row(row)
    assert any("out of range" in e for e in errors)



def test_validate_canonical_row_catches_non_numeric_occupancy():
    row = {col: "test" for col in CANONICAL_TRAINING_COLUMNS}
    row["occupancy_pct"] = "not_a_number"
    errors = validate_canonical_row(row)
    assert any("not numeric" in e for e in errors)



def test_validate_canonical_row_catches_empty_timestamp():
    row = {col: "valid" for col in CANONICAL_TRAINING_COLUMNS}
    row["occupancy_pct"] = "50.0"
    row["timestamp_iso"] = ""
    row["zone_id"] = "zone-a"
    errors = validate_canonical_row(row)
    assert any("timestamp_iso is empty" in e for e in errors)



def test_validate_canonical_row_passes_valid_row():
    row = {col: "valid" for col in CANONICAL_TRAINING_COLUMNS}
    row["occupancy_pct"] = "50.0"
    row["timestamp_iso"] = "2026-03-16T09:00:00+00:00"
    row["zone_id"] = "zone-a"
    errors = validate_canonical_row(row)
    assert errors == []



def test_normalize_external_training_rows_handles_empty_input():
    result = normalize_external_training_rows([])
    assert result == []



def test_normalize_external_training_rows_rejects_non_numeric_capacity():
    with pytest.raises(ValueError, match="non-numeric capacity/available"):
        normalize_external_training_rows(
            [
                {
                    "datetime": "2026-03-16T09:00:00+00:00",
                    "location": "klcc-north",
                    "capacity": "abc",
                    "available": "50",
                }
            ]
        )
