"""
Parking slots API endpoints.
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models.parking import OccupancyLog, ParkingEvent, ParkingSlot

slots_bp = Blueprint('slots', __name__)


@slots_bp.route('/slots')
def get_all_slots():
    """Get all parking slots with optional filters."""
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
def get_slot(slot_id):
    """Get a specific parking slot."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    return jsonify(slot.to_dict())


@slots_bp.route('/slots/<slot_id>/status', methods=['PUT'])
def update_slot_status(slot_id):
    """Update slot occupancy status (called by MQTT subscriber)."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    data = request.get_json()
    
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
def get_slot_events(slot_id):
    """Get recent events for a slot."""
    limit = request.args.get('limit', 50, type=int)
    events = ParkingEvent.query.filter_by(slot_id=slot_id)\
        .order_by(ParkingEvent.timestamp.desc())\
        .limit(limit)\
        .all()
    return jsonify({
        'events': [e.to_dict() for e in events]
    })
