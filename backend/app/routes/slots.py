"""
Parking slots API endpoints.
"""
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload
from app import db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot
from app.schemas import slot_status_schema

slots_bp = Blueprint('slots', __name__)

MAX_EVENTS_LIMIT = 500

def _require_read_access():
    """Enforce auth unless public read mode is enabled."""
    if current_app.config.get('ALLOW_PUBLIC_READS'):
        return None

    if get_jwt_identity() is None:
        return jsonify({"error": "Authentication required"}), 401

    return None


@slots_bp.route('/slots')
@jwt_required(optional=True)
def get_all_slots():
    """Get all parking slots with optional filters."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    lot_id = request.args.get('lot_id')
    status = request.args.get('status')  # 'available' or 'occupied'
    
    query = ParkingSlot.query
    
    if lot_id:
        query = query.filter_by(lot_id=lot_id)
    if status == 'available':
        query = query.filter_by(is_occupied=False)
    elif status == 'occupied':
        query = query.filter_by(is_occupied=True)
    
    slots = query.all()
    return jsonify({
        'slots': [slot.to_dict() for slot in slots],
        'total': len(slots)
    })


@slots_bp.route('/slots/<slot_id>')
@jwt_required(optional=True)
def get_slot(slot_id):
    """Get a specific parking slot."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    slot = ParkingSlot.query.get_or_404(slot_id)
    return jsonify(slot.to_dict())


@slots_bp.route('/slots/<slot_id>/status', methods=['PUT'])
@jwt_required()
def update_slot_status(slot_id):
    """Update slot occupancy status (called by MQTT subscriber)."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    try:
        data = slot_status_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"error": "Validation failed", "details": err.messages}), 400
    
    if 'is_occupied' in data:
        old_status = slot.is_occupied
        slot.is_occupied = data['is_occupied']
        
        # Record event if status changed
        if old_status != slot.is_occupied:
            from datetime import datetime
            slot.last_status_change = datetime.utcnow()
            event = ParkingEvent(
                slot_id=slot_id,
                event_type='entry' if slot.is_occupied else 'exit',
                sensor_distance_cm=data.get('distance_cm')
            )
            db.session.add(event)
            db.session.add(
                OccupancyLog(
                    slot_id=slot_id,
                    status='occupied' if slot.is_occupied else 'vacant',
                    distance_cm=data.get('distance_cm')
                )
            )
    
    db.session.commit()
    return jsonify(slot.to_dict())


@slots_bp.route('/slots/<slot_id>/events')
@jwt_required(optional=True)
def get_slot_events(slot_id):
    """Get recent events for a slot."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    requested_limit = request.args.get('limit', 50, type=int)
    limit = max(1, min(requested_limit, MAX_EVENTS_LIMIT))
    events = ParkingEvent.query.filter_by(slot_id=slot_id)\
        .order_by(ParkingEvent.timestamp.desc())\
        .limit(limit)\
        .all()
    return jsonify({
        'events': [e.to_dict() for e in events]
    })


@slots_bp.route('/events')
@jwt_required(optional=True)
def get_all_events():
    """Get recent events across all slots, optionally filtered by lot."""
    access_error = _require_read_access()
    if access_error:
        return access_error

    requested_limit = request.args.get('limit', 100, type=int)
    limit = max(1, min(requested_limit, MAX_EVENTS_LIMIT))
    lot_id = request.args.get('lot_id')

    query = ParkingEvent.query.options(
        joinedload(ParkingEvent.slot).joinedload(ParkingSlot.lot)
    )

    if lot_id:
        query = query.join(ParkingSlot).filter(ParkingSlot.lot_id == lot_id)

    events = query.order_by(ParkingEvent.timestamp.desc()).limit(limit).all()

    payload = []
    for event in events:
        slot = event.slot
        lot = slot.lot if slot else None
        payload.append({
            'id': event.id,
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'slot_id': event.slot_id,
            'slot_number': slot.slot_number if slot else None,
            'lot_id': slot.lot_id if slot else None,
            'lot_name': lot.name if lot else None,
            'sensor_distance_cm': event.sensor_distance_cm,
        })

    return jsonify({
        'events': payload,
        'total': len(payload)
    })
