"""Regression tests for simulator lot selection defaults."""

from __future__ import annotations

import pytest

from mqtt_simulator import resolve_lot_ids


def test_defaults_to_all_configured_lots_when_no_flags_provided():
    lot_ids = resolve_lot_ids(single_lot=None, lots_csv=None)
    assert lot_ids == ["lot-a", "lot-b"]


def test_single_lot_flag_is_respected():
    lot_ids = resolve_lot_ids(single_lot="lot-b", lots_csv=None)
    assert lot_ids == ["lot-b"]


def test_multi_lot_flag_is_parsed_and_deduplicated():
    lot_ids = resolve_lot_ids(single_lot=None, lots_csv="lot-a, lot-b,lot-a")
    assert lot_ids == ["lot-a", "lot-b"]


def test_invalid_multi_lot_value_raises_value_error():
    with pytest.raises(ValueError, match="no valid lot IDs"):
        resolve_lot_ids(single_lot=None, lots_csv=",")
