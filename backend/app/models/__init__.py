"""Model exports for convenient imports in routes/services."""

from app.models.parking import (
    OccupancyLog,
    ParkingEvent,
    ParkingLot,
    ParkingSlot,
    SensorReading,
    Zone,
)
from app.models.user import User

__all__ = [
    "User",
    "ParkingLot",
    "Zone",
    "ParkingSlot",
    "ParkingEvent",
    "SensorReading",
    "OccupancyLog",
]
