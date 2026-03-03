# Day 7 Simulation Documentation (Hardware Not Issued Path)

## Scope

This document captures the Day 7 simulation path when physical hardware is not issued.

## Simulator Configuration

Command used:

```bash
cd hardware/simulator
python mqtt_simulator.py --mode dynamic --interval 2 --failure-probability 0.03 --cycles 240
```

Key behavior:

- 6 slots (`slot-1` to `slot-6`) in `lot-a`
- Dynamic occupancy profile based on time windows
- Random outage windows to test resilience
- Heartbeat publish every 30 seconds

## Topic Contract Validation

Validated topic shapes:

- `prism/<lot_id>/slot/<slot_id>`
- `prism/<lot_id>/heartbeat`

Validated payload fields:

- Slot payload: `distance_cm`, `timestamp`, optional `occupied`
- Heartbeat payload: `device`, `uptime`, `wifi_rssi`

Reference: [`docs/mqtt_topics.md`](./mqtt_topics.md)

## Data Collection Notes

- Occupancy transitions are ingested by backend and written to:
  - `parking_events`
  - `occupancy_logs`
- Export utility available:

```bash
cd backend
python scripts/export_occupancy_logs.py --output ../data/processed/day7_occupancy_logs.csv
```

## Calibration Notes (Simulation Baseline)

- Occupied detection baseline: `< 15 cm`
- Vacant baseline: `>= 15 cm`
- Practical ranges observed in simulator:
  - Occupied: `3-12 cm`
  - Vacant: `50-150 cm`

## Issues Encountered and Fixes

1. Issue: simulator topic slot IDs must map to backend primary keys.
   Fix: Day 7 seed command now creates canonical IDs (`lot-a-slot-1..lot-a-slot-6`) expected by MQTT ingestion.
2. Issue: environment drift can cause empty dashboard after DB reset.
   Fix: run `flask seed-campus` after migrations/reset before launching frontend.
3. Issue: long runs include intermittent simulated outages.
   Fix: use outage windows as a test case, not as failure, and verify recovery events.

## Exit Criteria Met

- Backend receives slot updates continuously.
- Event feed (`/api/v1/events`) shows entry/exit transitions.
- Frontend dashboard has live data source via authenticated API polling.
- Seeded baseline can be recreated repeatably with one CLI command.
