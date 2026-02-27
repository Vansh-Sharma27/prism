"""Model exports for convenient imports in routes/services."""

from app.models.user import User
from app.models.parking import (
    OccupancyLog,
    ParkingEvent,
    ParkingLot,
    ParkingSlot,
    SensorReading,
    Zone,
)

__all__ = [
    "User",
    "ParkingLot",
    "Zone",
    "ParkingSlot",
    "ParkingEvent",
    "SensorReading",
    "OccupancyLog",
]
