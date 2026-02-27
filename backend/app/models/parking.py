"""
Database models for PRISM parking system.
"""
from datetime import datetime

from app import db


class ParkingLot(db.Model):
    """Represents a parking lot/zone."""
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    total_slots = db.Column(db.Integer, default=0)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    slots = db.relationship('ParkingSlot', backref='lot', lazy='dynamic')
    zones = db.relationship('Zone', backref='lot', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'total_slots': self.total_slots,
            'available_slots': self.slots.filter_by(is_occupied=False).count(),
            'latitude': self.latitude,
            'longitude': self.longitude
        }


class ParkingSlot(db.Model):
    """Represents an individual parking slot."""
    __tablename__ = 'parking_slots'
    
    id = db.Column(db.String(50), primary_key=True)
    lot_id = db.Column(db.String(50), db.ForeignKey('parking_lots.id'), nullable=False)
    zone_id = db.Column(db.String(50), db.ForeignKey('zones.id'), nullable=True)
    slot_number = db.Column(db.Integer, nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    is_reserved = db.Column(db.Boolean, default=False)
    slot_type = db.Column(db.String(20), default='standard')  # standard, handicapped, ev
    sensor_id = db.Column(db.String(50))
    last_status_change = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    events = db.relationship('ParkingEvent', backref='slot', lazy='dynamic')
    occupancy_logs = db.relationship('OccupancyLog', backref='slot', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'lot_id': self.lot_id,
            'zone_id': self.zone_id,
            'slot_number': self.slot_number,
            'is_occupied': self.is_occupied,
            'is_reserved': self.is_reserved,
            'slot_type': self.slot_type,
            'last_status_change': self.last_status_change.isoformat() if self.last_status_change else None
        }


class Zone(db.Model):
    """Logical grouping of slots inside a lot."""
    __tablename__ = 'zones'

    id = db.Column(db.String(50), primary_key=True)
    lot_id = db.Column(db.String(50), db.ForeignKey('parking_lots.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    walk_times = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    slots = db.relationship('ParkingSlot', backref='zone', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('lot_id', 'name', name='uq_zone_lot_name'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'lot_id': self.lot_id,
            'name': self.name,
            'walk_times': self.walk_times,
        }


class ParkingEvent(db.Model):
    """Records parking events (entry/exit)."""
    __tablename__ = 'parking_events'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.String(50), db.ForeignKey('parking_slots.id'), nullable=False)
    event_type = db.Column(db.String(10), nullable=False)  # 'entry' or 'exit'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sensor_distance_cm = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'slot_id': self.slot_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat()
        }


class SensorReading(db.Model):
    """Raw sensor readings for ML training."""
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.String(50), db.ForeignKey('parking_slots.id'), nullable=False)
    distance_cm = db.Column(db.Float, nullable=False)
    is_occupied = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_sensor_readings_slot_time', 'slot_id', 'timestamp'),
    )


class OccupancyLog(db.Model):
    """Time-series state changes used for analytics and ML features."""
    __tablename__ = 'occupancy_logs'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.String(50), db.ForeignKey('parking_slots.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # occupied or vacant
    distance_cm = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_occupancy_logs_slot_time', 'slot_id', 'timestamp'),
    )
