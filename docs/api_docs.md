# PRISM API Documentation (Day 7)

This document covers all backend endpoints available in Phase 1.

## Base URL

- Local backend: `http://localhost:5000`
- Versioned API prefix: `/api/v1`

## Authentication Model

- Auth uses JWT bearer tokens.
- Register and login are public.
- Most data routes require auth unless `PRISM_ALLOW_PUBLIC_READS=true`.
- Send tokens in header:

```http
Authorization: Bearer <access_token>
```

## Response Conventions

- JSON responses only.
- Typical success codes: `200`, `201`.
- Typical error codes: `400`, `401`, `403`, `404`, `409`.

---

## Health Endpoints

### GET `/`

Basic API metadata.

Example response:

```json
{
  "docs": "/api/v1",
  "message": "PRISM Parking API",
  "version": "1.0.0"
}
```

### GET `/health`

Service health check for monitoring.

Example response:

```json
{
  "service": "prism-backend",
  "status": "healthy",
  "timestamp": "2026-03-03T15:02:40.123456"
}
```

---

## Auth Endpoints

### POST `/api/v1/auth/register`

Register a new user.

Request body:

```json
{
  "email": "student@gla.ac.in",
  "password": "StrongPass123",
  "role": "student"
}
```

Notes:

- `role` defaults to `student`.
- If `PRISM_ALLOW_PRIVILEGED_SELF_REGISTER=false`, only `student` is accepted.

Success response (`201`):

```json
{
  "message": "User registered",
  "user": {
    "created_at": "2026-03-03T14:58:33.000001",
    "email": "student@gla.ac.in",
    "id": 2,
    "role": "student"
  }
}
```

Common errors:

- `400` validation failed
- `403` privileged role self-registration blocked
- `409` email already registered

### POST `/api/v1/auth/login`

Authenticate a user and return JWT.

Request body:

```json
{
  "email": "student@gla.ac.in",
  "password": "StrongPass123"
}
```

Success response (`200`):

```json
{
  "access_token": "<jwt-token>",
  "user": {
    "created_at": "2026-03-03T14:58:33.000001",
    "email": "student@gla.ac.in",
    "id": 2,
    "role": "student"
  }
}
```

Common errors:

- `400` validation failed
- `401` invalid email or password

### GET `/api/v1/auth/me`

Return current authenticated user.

Headers: `Authorization: Bearer <token>`

Success response (`200`):

```json
{
  "user": {
    "created_at": "2026-03-03T14:58:33.000001",
    "email": "student@gla.ac.in",
    "id": 2,
    "role": "student"
  }
}
```

Common errors:

- `401` missing/invalid token
- `404` user not found

---

## Lot Endpoints

### GET `/api/v1/lots`

List all parking lots with availability summary.

Query params: none

Success response (`200`):

```json
{
  "lots": [
    {
      "available_slots": 5,
      "id": "lot-a",
      "latitude": 27.4921,
      "location": "North Campus - Academic Complex",
      "longitude": 77.6752,
      "name": "Academic Block A",
      "total_slots": 6
    }
  ],
  "total": 2
}
```

### GET `/api/v1/lots/<lot_id>`

Get one lot with slot details.

Success response (`200`):

```json
{
  "available_slots": 5,
  "id": "lot-a",
  "latitude": 27.4921,
  "location": "North Campus - Academic Complex",
  "longitude": 77.6752,
  "name": "Academic Block A",
  "slots": [
    {
      "id": "lot-a-slot-1",
      "is_occupied": true,
      "is_reserved": false,
      "last_reading_at": "2026-03-03T15:11:04.221212",
      "last_status_change": "2026-03-03T15:11:04.221212",
      "latest_distance_cm": 8.4,
      "lot_id": "lot-a",
      "sensor_id": "lot-a-sensor-1",
      "slot_number": 1,
      "slot_type": "standard",
      "zone_id": "zone-a-east",
      "zone_name": "East Wing"
    }
  ],
  "total_slots": 6
}
```

Common errors:

- `404` lot not found

### POST `/api/v1/lots`

Create a new parking lot.

Headers: auth required

Request body:

```json
{
  "id": "lot-c",
  "name": "Hostel Lot C",
  "location": "West Campus",
  "total_slots": 20,
  "latitude": 27.4903,
  "longitude": 77.6799
}
```

Success response (`201`):

```json
{
  "available_slots": 0,
  "id": "lot-c",
  "latitude": 27.4903,
  "location": "West Campus",
  "longitude": 77.6799,
  "name": "Hostel Lot C",
  "total_slots": 20
}
```

Common errors:

- `400` validation failed
- `401` missing/invalid token
- `409` lot id already exists

### GET `/api/v1/lots/summary`

Get aggregate lot metrics.

Success response (`200`):

```json
{
  "available_slots": 10,
  "occupancy_rate": 16.7,
  "occupied_slots": 2,
  "total_lots": 2,
  "total_slots": 12
}
```

---

## Slot Endpoints

### GET `/api/v1/slots`

List slots with optional filters.

Query params:

- `lot_id=<id>`
- `status=available|occupied`

Success response (`200`):

```json
{
  "slots": [
    {
      "id": "lot-a-slot-1",
      "is_occupied": false,
      "is_reserved": false,
      "last_reading_at": null,
      "last_status_change": "2026-03-03T14:40:00.000000",
      "latest_distance_cm": null,
      "lot_id": "lot-a",
      "sensor_id": "lot-a-sensor-1",
      "slot_number": 1,
      "slot_type": "standard",
      "zone_id": "zone-a-east",
      "zone_name": "East Wing"
    }
  ],
  "total": 6
}
```

### GET `/api/v1/slots/<slot_id>`

Get one slot.

Success response (`200`): same slot object shape as above.

Common errors:

- `404` slot not found

### PUT `/api/v1/slots/<slot_id>/status`

Update slot status (used by ingestion pipeline and testing).

Headers: auth required

Request body:

```json
{
  "is_occupied": true,
  "is_reserved": false
}
```

Success response (`200`): updated slot object.

Notes:

- If occupancy state changes, backend creates an event (`entry` or `exit`) and occupancy log row.

Common errors:

- `400` validation failed
- `401` missing/invalid token
- `404` slot not found

### GET `/api/v1/slots/<slot_id>/events`

Get recent events for one slot.

Query params:

- `limit` (default `50`, max `500`)

Success response (`200`):

```json
{
  "events": [
    {
      "event_type": "entry",
      "id": 17,
      "slot_id": "lot-a-slot-1",
      "timestamp": "2026-03-03T15:11:04.221212"
    }
  ]
}
```

### GET `/api/v1/events`

Get recent events across all slots.

Query params:

- `limit` (default `100`, max `500`)
- `lot_id` (optional lot filter)

Success response (`200`):

```json
{
  "events": [
    {
      "event_type": "entry",
      "id": 17,
      "lot_id": "lot-a",
      "lot_name": "Academic Block A",
      "sensor_distance_cm": null,
      "slot_id": "lot-a-slot-1",
      "slot_number": 1,
      "timestamp": "2026-03-03T15:11:04.221212"
    }
  ],
  "total": 1
}
```

---

## CLI Seed Command (Day 7)

### `flask seed-campus`

Seeds baseline campus data:

- 2 lots (`lot-a`, `lot-b`)
- 4 zones
- 12 slots
- 1 admin user

Usage:

```bash
cd backend
flask seed-campus
```

Custom admin credentials:

```bash
flask seed-campus --admin-email admin@prism.local --admin-password Admin@12345
```

The command is idempotent. Re-running updates existing records without creating duplicates.

---

## Sample cURL Flow

```bash
# 1) Register
curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"student@gla.ac.in","password":"StrongPass123"}'

# 2) Login and capture token
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"student@gla.ac.in","password":"StrongPass123"}' | jq -r '.access_token')

# 3) Read lots
curl -s http://localhost:5000/api/v1/lots \
  -H "Authorization: Bearer $TOKEN"
```
