#!/usr/bin/env python3
"""Combine PRISM-exported training data with external Kaggle (KLCC) dataset.

Reads a PRISM canonical CSV and an external CSV, normalizes the external data
into the canonical schema, merges them chronologically, and writes the
combined output.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "combined_training.csv"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.training_data import (  # noqa: E402
    merge_training_datasets,
    normalize_external_training_rows,
    read_canonical_csv,
    write_canonical_csv,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine PRISM training export with external Kaggle dataset"
    )
    parser.add_argument(
        "--prism-input",
        required=True,
        help="Path to PRISM canonical training CSV",
    )
    parser.add_argument(
        "--kaggle-input",
        required=True,
        help="Path to external Kaggle (KLCC) CSV",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Output combined CSV path (default: {DEFAULT_OUTPUT})",
    )
    return parser


def _read_external_csv(path: Path) -> list[dict[str, Any]]:
    """Read an external CSV into a list of dicts."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Accepts optional argv for testability."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    prism_path = Path(args.prism_input).expanduser().resolve()
    kaggle_path = Path(args.kaggle_input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not prism_path.exists():
        print(f"Error: PRISM input file not found: {prism_path}")
        return 1
    if not kaggle_path.exists():
        print(f"Error: Kaggle input file not found: {kaggle_path}")
        return 1

    prism_rows = read_canonical_csv(prism_path)
    external_raw = _read_external_csv(kaggle_path)

    try:
        external_normalized = normalize_external_training_rows(external_raw)
    except ValueError as exc:
        print(f"Error normalizing external dataset: {exc}")
        return 1

    combined = merge_training_datasets(prism_rows, external_normalized)
    count = write_canonical_csv(combined, output_path)
    print(f"Combined {count} training rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
