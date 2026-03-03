"""Tests for Day 7 campus seeding command."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app, db
from app.models.parking import ParkingLot, ParkingSlot, Zone
from app.models.user import User


@pytest.fixture()
def seeded_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "seed_campus_test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "seed-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "seed-jwt-secret")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    return app


def test_seed_campus_cli_creates_expected_baseline(seeded_app):
    runner = seeded_app.test_cli_runner()
    result = runner.invoke(
        args=[
            "seed-campus",
            "--admin-email",
            "admin@prism.local",
            "--admin-password",
            "Admin@12345",
        ]
    )

    assert result.exit_code == 0
    assert "Campus seed completed:" in result.output

    with seeded_app.app_context():
        assert ParkingLot.query.count() == 2
        assert Zone.query.count() == 4
        assert ParkingSlot.query.count() == 12

        lot_a = db.session.get(ParkingLot, "lot-a")
        assert lot_a is not None
        assert lot_a.total_slots == 6

        admin = User.query.filter_by(email="admin@prism.local").first()
        assert admin is not None
        assert admin.role == "admin"
        assert admin.check_password("Admin@12345")


def test_seed_campus_cli_is_idempotent(seeded_app):
    runner = seeded_app.test_cli_runner()
    first = runner.invoke(args=["seed-campus"])
    second = runner.invoke(args=["seed-campus"])

    assert first.exit_code == 0
    assert second.exit_code == 0

    with seeded_app.app_context():
        assert ParkingLot.query.count() == 2
        assert Zone.query.count() == 4
        assert ParkingSlot.query.count() == 12

        admin = User.query.filter_by(email="admin@prism.local").first()
        assert admin is not None
        assert admin.role == "admin"
