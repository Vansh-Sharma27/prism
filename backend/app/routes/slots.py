"""Parking slots API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

from app import db, limiter
from app.authz import require_roles
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from app.responses import error_response
from app.schemas import slot_status_schema
from app.services.notifications import publish_slot_change

slots_bp = Blueprint("slots", __name__)

MAX_EVENTS_LIMIT = 500


def _require_read_access():
    """Enforce auth unless public read mode is enabled."""
    if current_app.config.get("ALLOW_PUBLIC_READS"):
        return None

    if get_jwt_identity() is None:
        return error_response("Authentication required", 401)

    return None


def _parse_iso_datetime(raw_value: str | None, field_name: str) -> tuple[datetime | None, object | None]:
    if raw_value is None:
        return None, None

    value = raw_value.strip()
    if not value:
        return None, None

    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, error_response(
            f"Invalid {field_name}. Use ISO-8601 datetime.",
            400,
            code="validation_error",
        )

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed, None


def _apply_slot_update(slot: ParkingSlot, data: dict, *, source: str) -> tuple[bool, bool]:
    """Apply a single slot update and emit event/log rows if occupancy changed."""
    touched = False
    changed_occupancy = False

    if "is_occupied" in data:
        incoming_status = data["is_occupied"]
        old_status = slot.is_occupied
        if incoming_status != old_status:
            touched = True
            slot.is_occupied = incoming_status
            changed_occupancy = True
            slot.last_status_change = datetime.utcnow()
            event_type = "entry" if slot.is_occupied else "exit"
            distance_cm = data.get("distance_cm")

            db.session.add(
                ParkingEvent(
                    slot_id=slot.id,
                    event_type=event_type,
                    sensor_distance_cm=distance_cm,
                )
            )
            db.session.add(
                OccupancyLog(
                    slot_id=slot.id,
                    status="occupied" if slot.is_occupied else "vacant",
                    distance_cm=distance_cm,
                )
            )
            publish_slot_change(
                slot_id=slot.id,
                lot_id=slot.lot_id,
                zone_id=slot.zone_id,
                is_occupied=slot.is_occupied,
                event_type=event_type,
                source=source,
                distance_cm=distance_cm,
            )

    if "is_reserved" in data:
        incoming_reserved = data["is_reserved"]
        if incoming_reserved != slot.is_reserved:
            touched = True
            slot.is_reserved = incoming_reserved

    return touched, changed_occupancy


@slots_bp.route("/slots")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_all_slots():
    """Get all parking slots with optional filters."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    lot_id = request.args.get("lot_id")
    status = request.args.get("status")  # available or occupied

    query = ParkingSlot.query

    if lot_id:
        query = query.filter_by(lot_id=lot_id)
    if status == "available":
        query = query.filter_by(is_occupied=False)
    elif status == "occupied":
        query = query.filter_by(is_occupied=True)

    slots = query.all()
    return jsonify({"slots": [slot.to_dict() for slot in slots], "total": len(slots)})


@slots_bp.route("/slots/<slot_id>")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_slot(slot_id):
    """Get a specific parking slot."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        return error_response("Slot not found", 404)

    return jsonify(slot.to_dict())


@slots_bp.route("/slots/<slot_id>/status", methods=["PUT"])
@require_roles("faculty", "admin", error_message="Insufficient role permissions")
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_MUTATION", "60 per minute"))
def update_slot_status(slot_id):
    """Update slot occupancy status from authorized operators/services."""
    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        return error_response("Slot not found", 404)

    payload = request.get_json(silent=True) or {}
    try:
        data = slot_status_schema.load(payload)
    except ValidationError as err:
        return error_response("Validation failed", 400, code="validation_error", details=err.messages)

    touched, changed_occupancy = _apply_slot_update(slot, data, source="api")
    db.session.commit()

    return jsonify(
        {
            "slot": slot.to_dict(),
            "changed": changed_occupancy,
            "updated": touched,
        }
    )


@slots_bp.route("/slots/status/batch", methods=["PUT"])
@require_roles("faculty", "admin", error_message="Insufficient role permissions")
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_MUTATION", "60 per minute"))
def batch_update_slot_status():
    """Apply a batch of slot state updates with per-item results."""
    payload = request.get_json(silent=True) or {}
    updates = payload.get("updates")

    if not isinstance(updates, list) or len(updates) == 0:
        return error_response(
            "updates must be a non-empty array",
            400,
            code="validation_error",
        )

    results = []
    updated = 0
    unchanged = 0
    failed = 0

    for index, item in enumerate(updates):
        if not isinstance(item, dict):
            failed += 1
            results.append(
                {
                    "index": index,
                    "status": "error",
                    "error": "Each update item must be an object",
                }
            )
            continue

        slot_id = item.get("slot_id")
        if not isinstance(slot_id, str) or not slot_id.strip():
            failed += 1
            results.append(
                {
                    "index": index,
                    "status": "error",
                    "error": "slot_id is required",
                }
            )
            continue

        slot = db.session.get(ParkingSlot, slot_id)
        if slot is None:
            failed += 1
            results.append(
                {
                    "index": index,
                    "slot_id": slot_id,
                    "status": "error",
                    "error": "Slot not found",
                }
            )
            continue

        update_payload = {
            key: item[key]
            for key in ("is_occupied", "is_reserved", "distance_cm")
            if key in item
        }

        if not update_payload:
            failed += 1
            results.append(
                {
                    "index": index,
                    "slot_id": slot_id,
                    "status": "error",
                    "error": "No mutable fields provided",
                }
            )
            continue

        try:
            data = slot_status_schema.load(update_payload)
        except ValidationError as err:
            failed += 1
            results.append(
                {
                    "index": index,
                    "slot_id": slot_id,
                    "status": "error",
                    "error": "Validation failed",
                    "details": err.messages,
                }
            )
            continue

        touched, changed_occupancy = _apply_slot_update(slot, data, source="api_batch")
        if touched:
            updated += 1
        else:
            unchanged += 1

        results.append(
            {
                "index": index,
                "slot_id": slot_id,
                "status": "updated" if touched else "no_change",
                "changed": changed_occupancy,
            }
        )

    db.session.commit()

    summary = {
        "requested": len(updates),
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
    }

    return jsonify({"results": results, "summary": summary})


@slots_bp.route("/slots/<slot_id>/events")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_slot_events(slot_id):
    """Get recent events for a slot."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    requested_limit = request.args.get("limit", 50, type=int)
    limit = max(1, min(requested_limit, MAX_EVENTS_LIMIT))
    events = (
        ParkingEvent.query.filter_by(slot_id=slot_id)
        .order_by(ParkingEvent.timestamp.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"events": [event.to_dict() for event in events]})


@slots_bp.route("/events")
@jwt_required(optional=True)
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_READ_HEAVY", "120 per minute"))
def get_all_events():
    """Get recent events across all slots, with optional filters."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    requested_limit = request.args.get("limit", 100, type=int)
    limit = max(1, min(requested_limit, MAX_EVENTS_LIMIT))

    lot_id = request.args.get("lot_id")
    slot_id = request.args.get("slot_id")
    event_type = request.args.get("event_type")

    start_at, start_err = _parse_iso_datetime(request.args.get("start"), "start")
    if start_err:
        return start_err
    end_at, end_err = _parse_iso_datetime(request.args.get("end"), "end")
    if end_err:
        return end_err

    if event_type and event_type not in {"entry", "exit"}:
        return error_response(
            "Invalid event_type. Use entry or exit.",
            400,
            code="validation_error",
        )

    if start_at and end_at and start_at > end_at:
        return error_response(
            "start must be before end",
            400,
            code="validation_error",
        )

    query = ParkingEvent.query.options(joinedload(ParkingEvent.slot).joinedload(ParkingSlot.lot))

    if lot_id:
        query = query.join(ParkingSlot).filter(ParkingSlot.lot_id == lot_id)

    if slot_id:
        query = query.filter(ParkingEvent.slot_id == slot_id)

    if event_type:
        query = query.filter(ParkingEvent.event_type == event_type)

    if start_at:
        query = query.filter(ParkingEvent.timestamp >= start_at)

    if end_at:
        query = query.filter(ParkingEvent.timestamp <= end_at)

    events = query.order_by(ParkingEvent.timestamp.desc()).limit(limit).all()

    payload = []
    for event in events:
        slot = event.slot
        lot = slot.lot if slot else None
        payload.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "slot_id": event.slot_id,
                "slot_number": slot.slot_number if slot else None,
                "lot_id": slot.lot_id if slot else None,
                "lot_name": lot.name if lot else None,
                "sensor_distance_cm": event.sensor_distance_cm,
            }
        )

    return jsonify({"events": payload, "total": len(payload)})
