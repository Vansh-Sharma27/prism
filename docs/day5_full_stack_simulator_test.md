# Day 5 Full-Stack Simulator Test Report

Date: 2026-03-02

## Objective

Validate the Day 5 live-data pipeline:

1. Simulator-style payloads ingested by backend MQTT processing logic.
2. Backend API endpoints returning updated slot and lot state.
3. Frontend polling-compatible response fields available (`latest_distance_cm`, `last_reading_at`, `sensor_id`, `zone_name`).

## Environment Constraints

Direct broker/network integration commands (`mosquitto_pub`, local HTTP calls) were blocked in this execution sandbox without elevated network runtime. To keep progress unblocked, verification used an in-process integration flow:

- Flask app + SQLite DB in `/tmp/prism_day5_integration.db`
- `MQTTService._handle_slot_update(...)` invoked with simulator-like payloads
- API verified through Flask `test_client()` on `/api/v1/slots?lot_id=lot-a` and `/api/v1/lots/lot-a`

## Test Procedure

1. Created lot `lot-a` with 6 slots (`lot-a-slot-1` ... `lot-a-slot-6`).
2. Sent simulator-style update cycle 1 with random occupied/vacant distances.
3. Captured slot API snapshot.
4. Sent simulator-style update cycle 2.
5. Captured second slot API snapshot and compared changed fields.
6. Queried lot detail endpoint for availability summary.

## Result Summary

```json
{
  "cycle1_total_slots": 6,
  "cycle2_total_slots": 6,
  "changed_slots_between_cycles": 6,
  "lot_available_slots": 3,
  "lot_total_slots": 6
}
```

## Conclusion

- Backend ingestion and slot-state persistence are working for simulator payloads.
- API returns the new telemetry fields needed by frontend live polling.
- Consecutive simulator cycles changed all 6 slot records in this run.

## Manual End-to-End Command Set (for unrestricted local machine)

```bash
# 1) Start broker
mosquitto -p 1883

# 2) Start backend
cd backend
PRISM_AUTO_CREATE_TABLES=true python3 run.py

# 3) Seed lot/slots if empty
# (use backend shell/script to create lot-a and slots lot-a-slot-1..6)

# 4) Start frontend
cd ../frontend
npm run dev

# 5) Start simulator
cd ..
python3 hardware/simulator/mqtt_simulator.py --broker localhost --port 1883 --lot lot-a --interval 1
```
