"""
Parking lots API endpoints.
"""

import re

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy import case, func

from app import db, limiter
from app.authz import require_roles
from app.models.parking import ParkingLot, ParkingSlot
from app.responses import error_response
from app.schemas import lot_schema

lots_bp = Blueprint("lots", __name__)

LOT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


def _require_read_access():
    """Enforce auth unless public read mode is enabled."""
    if current_app.config.get("ALLOW_PUBLIC_READS"):
        return None

    if get_jwt_identity() is None:
        return error_response("Authentication required", 401)

    return None


@lots_bp.route("/lots")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_all_lots():
    """Get all parking lots with availability summary."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    lots = ParkingLot.query.all()
    return jsonify({"lots": [lot.to_dict() for lot in lots], "total": len(lots)})


@lots_bp.route("/lots/<lot_id>")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_lot(lot_id):
    """Get a specific parking lot with slot details."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    if not LOT_ID_PATTERN.fullmatch(lot_id):
        return error_response("Invalid lot_id format", 400, code="validation_error")

    lot = db.session.get(ParkingLot, lot_id)
    if lot is None:
        return error_response("Lot not found", 404)
    lot_dict = lot.to_dict()
    lot_dict["slots"] = [slot.to_dict() for slot in lot.slots]
    return jsonify(lot_dict)


@lots_bp.route("/lots", methods=["POST"])
@require_roles("faculty", "admin", error_message="Insufficient role permissions")
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_MUTATION", "60 per minute"))
def create_lot():
    """Create a new parking lot."""
    try:
        data = lot_schema.load(request.get_json())
    except ValidationError as err:
        return error_response("Validation failed", 400, code="validation_error", details=err.messages)

    if ParkingLot.query.filter_by(id=data["id"]).first():
        return error_response("Lot id already exists", 409, code="conflict")

    lot = ParkingLot(
        id=data["id"],
        name=data["name"],
        location=data.get("location"),
        total_slots=data.get("total_slots", 0),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    db.session.add(lot)
    db.session.commit()
    return jsonify(lot.to_dict()), 201


@lots_bp.route("/lots/summary")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_lots_summary():
    """Get summary statistics for all lots."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    lots = ParkingLot.query.all()

    # Single aggregated query to get available counts per lot (replaces N+1)
    availability_rows = (
        db.session.query(
            ParkingSlot.lot_id,
            func.count(ParkingSlot.id).label("total"),
            func.coalesce(
                func.sum(case((ParkingSlot.is_occupied == False, 1), else_=0)),  # noqa: E712
                0,
            ).label("available"),
        )
        .group_by(ParkingSlot.lot_id)
        .all()
    )
    avail_map = {row.lot_id: int(row.available) for row in availability_rows}

    total_slots = sum(lot.total_slots for lot in lots)
    available = sum(avail_map.get(lot.id, 0) for lot in lots)

    return jsonify(
        {
            "total_lots": len(lots),
            "total_slots": total_slots,
            "available_slots": available,
            "occupied_slots": total_slots - available,
            "occupancy_rate": round((total_slots - available) / total_slots * 100, 1) if total_slots > 0 else 0,
        }
    )
