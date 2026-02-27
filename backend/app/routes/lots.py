"""
Parking lots API endpoints.
"""
from flask import Blueprint, jsonify, request
from app import db
from app.models.parking import ParkingLot

lots_bp = Blueprint('lots', __name__)


@lots_bp.route('/lots')
def get_all_lots():
    """Get all parking lots with availability summary."""
    lots = ParkingLot.query.all()
    return jsonify({
        'lots': [lot.to_dict() for lot in lots],
        'total': len(lots)
    })


@lots_bp.route('/lots/<lot_id>')
def get_lot(lot_id):
    """Get a specific parking lot with slot details."""
    lot = ParkingLot.query.get_or_404(lot_id)
    lot_dict = lot.to_dict()
    lot_dict['slots'] = [slot.to_dict() for slot in lot.slots]
    return jsonify(lot_dict)


@lots_bp.route('/lots', methods=['POST'])
def create_lot():
    """Create a new parking lot."""
    data = request.get_json()
    lot = ParkingLot(
        id=data['id'],
        name=data['name'],
        location=data.get('location'),
        total_slots=data.get('total_slots', 0),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    db.session.add(lot)
    db.session.commit()
    return jsonify(lot.to_dict()), 201


@lots_bp.route('/lots/summary')
def get_lots_summary():
    """Get summary statistics for all lots."""
    lots = ParkingLot.query.all()
    total_slots = sum(lot.total_slots for lot in lots)
    available = sum(lot.slots.filter_by(is_occupied=False).count() for lot in lots)
    
    return jsonify({
        'total_lots': len(lots),
        'total_slots': total_slots,
        'available_slots': available,
        'occupied_slots': total_slots - available,
        'occupancy_rate': round((total_slots - available) / total_slots * 100, 1) if total_slots > 0 else 0
    })
