# Phase 1 Hardware/Simulation Handoff Summary

## Date

2026-03-03

## Path Used

Hardware-not-issued fallback path completed with simulation-first validation.

## Hardware Status Summary

- Physical multi-sensor assembly pending college lab issuance.
- Firmware baseline is ready:
  - `hardware/esp32/multi_sensor_mqtt.ino`
  - `hardware/sketches/prism_camera/prism_camera.ino` (camera skeleton)
- Wiring and assembly references are complete in docs.

## Simulation Status Summary

- MQTT simulator is stable in dynamic mode.
- Outage simulation and bounded-run options validated.
- Topic contracts and payload formats are aligned with backend parser.
- Backend event ingestion verified with seeded campus slots.

## Sensor Calibration Notes

- Current occupancy threshold baseline: `15 cm`.
- Simulated occupied range: `3-12 cm`.
- Simulated vacant range: `50-150 cm`.
- Debounce and status-change logging paths are active in backend event pipeline.

## Issues Encountered and Solutions

1. Dashboard can appear empty after DB reset.
   - Solution: run `flask seed-campus` before frontend validation.
2. Simulator updates require known slot IDs in backend.
   - Solution: seed now guarantees canonical IDs `lot-a-slot-1..lot-a-slot-6` for MQTT mapping.
3. Public reads disabled by default blocked unauthenticated dashboards.
   - Solution: keep auth flow in place and validate with login token.

## Handoff for Day 8-9

1. Execute checklist in `docs/day8_day9_physical_assembly_checklist.md`.
2. Perform full 2-hour physical stability run once hardware is issued.
3. Compare physical readings against simulation baselines and tune threshold.
4. Capture photos/logs for weekly faculty audit package.
