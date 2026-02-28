"""
Marshmallow schemas for request/response validation.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class UserRegisterSchema(Schema):
    """Validates user registration input."""
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        load_only=True
    )
    role = fields.Str(
        validate=validate.OneOf(["student", "faculty", "admin"]),
        load_default="student"
    )


class UserLoginSchema(Schema):
    """Validates login input."""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class UserResponseSchema(Schema):
    """User data in responses."""
    id = fields.Int(dump_only=True)
    email = fields.Email()
    role = fields.Str()
    created_at = fields.DateTime(dump_only=True)


class ParkingLotSchema(Schema):
    """Validates parking lot input."""
    id = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    location = fields.Str(validate=validate.Length(max=200))
    total_slots = fields.Int(validate=validate.Range(min=0))
    latitude = fields.Float()
    longitude = fields.Float()


class ParkingLotResponseSchema(Schema):
    """Lot data in responses."""
    id = fields.Str()
    name = fields.Str()
    location = fields.Str()
    total_slots = fields.Int()
    available_slots = fields.Int()
    latitude = fields.Float()
    longitude = fields.Float()


class ZoneSchema(Schema):
    """Validates zone input."""
    id = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    lot_id = fields.Str(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    walk_times = fields.Dict(keys=fields.Str(), values=fields.Int())


class ParkingSlotSchema(Schema):
    """Validates slot input."""
    id = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    lot_id = fields.Str(required=True)
    zone_id = fields.Str(allow_none=True)
    slot_number = fields.Int(required=True, validate=validate.Range(min=1))
    slot_type = fields.Str(
        validate=validate.OneOf(["standard", "handicapped", "ev"]),
        load_default="standard"
    )
    sensor_id = fields.Str(validate=validate.Length(max=50))


class SlotStatusUpdateSchema(Schema):
    """Validates slot status update."""
    is_occupied = fields.Bool()
    is_reserved = fields.Bool()


class SlotResponseSchema(Schema):
    """Slot data in responses."""
    id = fields.Str()
    lot_id = fields.Str()
    zone_id = fields.Str(allow_none=True)
    slot_number = fields.Int()
    is_occupied = fields.Bool()
    is_reserved = fields.Bool()
    slot_type = fields.Str()
    last_status_change = fields.DateTime()


class ParkingEventSchema(Schema):
    """Event data in responses."""
    id = fields.Int()
    slot_id = fields.Str()
    event_type = fields.Str()
    timestamp = fields.DateTime()


# Schema instances
user_register_schema = UserRegisterSchema()
user_login_schema = UserLoginSchema()
user_response_schema = UserResponseSchema()
lot_schema = ParkingLotSchema()
lot_response_schema = ParkingLotResponseSchema()
lots_response_schema = ParkingLotResponseSchema(many=True)
zone_schema = ZoneSchema()
slot_schema = ParkingSlotSchema()
slot_status_schema = SlotStatusUpdateSchema()
slot_response_schema = SlotResponseSchema()
slots_response_schema = SlotResponseSchema(many=True)
event_schema = ParkingEventSchema()
events_schema = ParkingEventSchema(many=True)
