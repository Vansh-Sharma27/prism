# PRISM MQTT Topic Specification

This document defines the MQTT topic and payload contract for PRISM sensor nodes and backend ingestion.

## Topic Naming Rules

All topics use lowercase segments and slash-separated paths.

## Core Topics

### Slot Status Updates

- Topic: `prism/{lot_id}/slot/{slot_id}`
- Publisher: ESP32 sensor node
- Subscriber: PRISM backend (`MQTTService`)
- QoS: `0` (current baseline), can be upgraded to `1` later

#### Payload

```json
{
  "distance_cm": 8.4,
  "occupied": true,
  "timestamp": 1739982000
}
```

#### Field Notes

- `distance_cm` is the raw ultrasonic reading in centimeters.
- `occupied` is optional for backend logic; backend currently computes occupancy from threshold.
- `timestamp` is device uptime time or epoch time depending on firmware mode.

### Heartbeat

- Topic: `prism/{lot_id}/heartbeat`
- Publisher: ESP32 sensor node
- Subscriber: PRISM backend (`MQTTService`)

#### Payload

```json
{
  "device": "esp32-01",
  "uptime": 12345,
  "wifi_rssi": -62,
  "slots": [
    {
      "slot_id": "slot-1",
      "distance_cm": 92.1,
      "occupied": false
    },
    {
      "slot_id": "slot-2",
      "distance_cm": 7.8,
      "occupied": true
    }
  ]
}
```

- `slots` is the per-slot freshness contract used by the backend to keep stable sensors online between occupancy changes.
- If a slot is currently faulted, heartbeat may emit `{"slot_id":"slot-3","status":"offline"}` for that entry instead of distance data.

Simulator outage payload extension (Day 6):

```json
{
  "device": "simulator",
  "slot_id": "slot-3",
  "status": "offline",
  "timestamp": 1739982000
}
```

## Naming Conventions

- `lot_id` example: `lot-a`
- `slot_id` example: `slot-1`
- Backend slot primary key format: `{lot_id}-{slot_id}` (example: `lot-a-slot-1`)

## Validation and Error Handling

- Invalid JSON payloads are rejected and logged.
- Unknown slots are ignored safely; no database write is attempted.
- The backend refreshes `parking_slots.last_telemetry_at` and `parking_slots.last_distance_cm` from both slot updates and heartbeat slot snapshots.
- The backend writes `sensor_readings` for heartbeat snapshots that include a valid distance payload.
- The backend writes `occupancy_logs` only when occupancy state changes.

## Security Notes (Planned)

- enforce broker credentials in production
- enforce topic-level ACL per device
- use TLS-enabled broker endpoint for cloud deployment
- avoid exposing `1883` beyond loopback unless the host firewall and broker auth are configured intentionally
