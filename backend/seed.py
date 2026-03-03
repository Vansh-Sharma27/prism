"""Campus data seeding utilities and Flask CLI command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import click
from flask import Flask

from app import db
from app.models.parking import ParkingLot, ParkingSlot, Zone
from app.models.user import User


@dataclass(frozen=True)
class CampusLotSeed:
    """Seed template for one campus lot."""

    lot: dict[str, Any]
    zones: list[dict[str, Any]]
    slots: list[dict[str, Any]]


SEED_DATA: tuple[CampusLotSeed, ...] = (
    CampusLotSeed(
        lot={
            "id": "lot-a",
            "name": "Academic Block A",
            "location": "North Campus - Academic Complex",
            "latitude": 27.4921,
            "longitude": 77.6752,
        },
        zones=[
            {
                "id": "zone-a-east",
                "name": "East Wing",
                "walk_times": {"Library": 3, "Admin Block": 5, "Cafeteria": 4},
            },
            {
                "id": "zone-a-west",
                "name": "West Wing",
                "walk_times": {"Library": 4, "Admin Block": 6, "Cafeteria": 3},
            },
        ],
        slots=[
            {"id": "lot-a-slot-1", "zone_id": "zone-a-east", "slot_number": 1, "slot_type": "standard"},
            {"id": "lot-a-slot-2", "zone_id": "zone-a-east", "slot_number": 2, "slot_type": "standard"},
            {"id": "lot-a-slot-3", "zone_id": "zone-a-east", "slot_number": 3, "slot_type": "ev"},
            {"id": "lot-a-slot-4", "zone_id": "zone-a-west", "slot_number": 4, "slot_type": "standard"},
            {"id": "lot-a-slot-5", "zone_id": "zone-a-west", "slot_number": 5, "slot_type": "handicapped"},
            {"id": "lot-a-slot-6", "zone_id": "zone-a-west", "slot_number": 6, "slot_type": "standard"},
        ],
    ),
    CampusLotSeed(
        lot={
            "id": "lot-b",
            "name": "Innovation Center Lot",
            "location": "South Campus - Innovation Corridor",
            "latitude": 27.4912,
            "longitude": 77.6761,
        },
        zones=[
            {
                "id": "zone-b-north",
                "name": "North Deck",
                "walk_times": {"Innovation Lab": 2, "Seminar Hall": 4, "Cafeteria": 6},
            },
            {
                "id": "zone-b-south",
                "name": "South Deck",
                "walk_times": {"Innovation Lab": 3, "Seminar Hall": 3, "Cafeteria": 5},
            },
        ],
        slots=[
            {"id": "lot-b-slot-1", "zone_id": "zone-b-north", "slot_number": 1, "slot_type": "standard"},
            {"id": "lot-b-slot-2", "zone_id": "zone-b-north", "slot_number": 2, "slot_type": "standard"},
            {"id": "lot-b-slot-3", "zone_id": "zone-b-north", "slot_number": 3, "slot_type": "ev"},
            {"id": "lot-b-slot-4", "zone_id": "zone-b-south", "slot_number": 4, "slot_type": "standard"},
            {"id": "lot-b-slot-5", "zone_id": "zone-b-south", "slot_number": 5, "slot_type": "handicapped"},
            {"id": "lot-b-slot-6", "zone_id": "zone-b-south", "slot_number": 6, "slot_type": "standard"},
        ],
    ),
)


def _upsert_lot(seed: CampusLotSeed) -> tuple[ParkingLot, bool]:
    lot_id = seed.lot["id"]
    lot = db.session.get(ParkingLot, lot_id)
    created = lot is None

    if created:
        lot = ParkingLot(id=lot_id)
        db.session.add(lot)

    lot.name = seed.lot["name"]
    lot.location = seed.lot["location"]
    lot.latitude = seed.lot["latitude"]
    lot.longitude = seed.lot["longitude"]
    lot.total_slots = len(seed.slots)
    return lot, created


def _upsert_zones(lot_id: str, zones: list[dict[str, Any]]) -> tuple[int, int]:
    created_count = 0
    updated_count = 0

    for zone_data in zones:
        zone = db.session.get(Zone, zone_data["id"])
        created = zone is None

        if created:
            zone = Zone(id=zone_data["id"], lot_id=lot_id)
            db.session.add(zone)
            created_count += 1
        else:
            updated_count += 1

        zone.lot_id = lot_id
        zone.name = zone_data["name"]
        zone.walk_times = zone_data["walk_times"]

    return created_count, updated_count


def _upsert_slots(lot_id: str, slots: list[dict[str, Any]]) -> tuple[int, int]:
    created_count = 0
    updated_count = 0

    for slot_data in slots:
        slot = db.session.get(ParkingSlot, slot_data["id"])
        created = slot is None

        if created:
            slot = ParkingSlot(id=slot_data["id"], lot_id=lot_id, is_occupied=False, is_reserved=False)
            db.session.add(slot)
            created_count += 1
        else:
            updated_count += 1

        slot.lot_id = lot_id
        slot.zone_id = slot_data["zone_id"]
        slot.slot_number = slot_data["slot_number"]
        slot.slot_type = slot_data["slot_type"]
        slot.sensor_id = f"{lot_id}-sensor-{slot_data['slot_number']}"

    return created_count, updated_count


def _upsert_admin_user(admin_email: str, admin_password: str) -> bool:
    normalized_email = admin_email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()
    created = user is None

    if created:
        user = User(email=normalized_email, role="admin")
        db.session.add(user)

    user.role = "admin"
    user.set_password(admin_password)
    return created


def seed_campus_data(admin_email: str, admin_password: str) -> dict[str, int]:
    """Create or update baseline campus entities for local development."""
    db.create_all()

    summary = {
        "lots_created": 0,
        "lots_updated": 0,
        "zones_created": 0,
        "zones_updated": 0,
        "slots_created": 0,
        "slots_updated": 0,
        "admin_users_created": 0,
        "admin_users_updated": 0,
    }

    for lot_seed in SEED_DATA:
        _, lot_created = _upsert_lot(lot_seed)
        if lot_created:
            summary["lots_created"] += 1
        else:
            summary["lots_updated"] += 1

        zones_created, zones_updated = _upsert_zones(lot_seed.lot["id"], lot_seed.zones)
        slots_created, slots_updated = _upsert_slots(lot_seed.lot["id"], lot_seed.slots)

        summary["zones_created"] += zones_created
        summary["zones_updated"] += zones_updated
        summary["slots_created"] += slots_created
        summary["slots_updated"] += slots_updated

    admin_created = _upsert_admin_user(admin_email=admin_email, admin_password=admin_password)
    if admin_created:
        summary["admin_users_created"] += 1
    else:
        summary["admin_users_updated"] += 1

    db.session.commit()
    return summary


def register_seed_command(app: Flask) -> None:
    """Attach seeding command to Flask CLI."""

    @app.cli.command("seed-campus")
    @click.option(
        "--admin-email",
        default="admin@prism.local",
        show_default=True,
        help="Admin email created or updated by the seeder.",
    )
    @click.option(
        "--admin-password",
        default="Admin@12345",
        show_default=False,
        help="Admin password used for the seeded admin account.",
    )
    def seed_campus(admin_email: str, admin_password: str) -> None:
        """Seed lots, zones, slots, and admin user for PRISM campus."""
        summary = seed_campus_data(admin_email=admin_email, admin_password=admin_password)
        click.echo("Campus seed completed:")
        for key, value in summary.items():
            click.echo(f"- {key}: {value}")
