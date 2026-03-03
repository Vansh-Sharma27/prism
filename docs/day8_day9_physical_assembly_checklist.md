# Day 8-9 Physical Assembly Checklist

Use this checklist before and during physical bring-up of PRISM sensor nodes.

## A. Lab Readiness

- [ ] ESP32 DevKit V1 boards issued and verified (count: 2)
- [ ] HC-SR04 sensors available (count: 6 + 1 spare)
- [ ] Breadboards and jumper wires available
- [ ] USB cables and power sources verified
- [ ] MQTT broker host/IP confirmed
- [ ] Wi-Fi credentials available for test network

## B. Pre-Wiring Validation

- [ ] Confirm wiring plan from `docs/hardware_assembly_guide.md`
- [ ] Confirm pin map against firmware constants in `hardware/esp32/multi_sensor_mqtt.ino`
- [ ] Confirm common ground strategy
- [ ] Prepare labels for each sensor and slot mapping

## C. Sensor Wiring (Per ESP32 Node)

- [ ] VIN to 5V rail
- [ ] GND to common ground rail
- [ ] Sensor 1 TRIG/ECHO wired to mapped GPIO pins
- [ ] Sensor 2 TRIG/ECHO wired to mapped GPIO pins
- [ ] Sensor 3 TRIG/ECHO wired to mapped GPIO pins
- [ ] Optional status LED wiring verified

## D. Firmware and Connectivity

- [ ] Flash firmware (`multi_sensor_mqtt.ino`)
- [ ] Serial monitor at `115200` baud shows clean boot
- [ ] Node connects to Wi-Fi
- [ ] Node connects to MQTT broker
- [ ] Heartbeat messages visible on `prism/<lot_id>/heartbeat`

## E. Functional Sensor Test

- [ ] Slot 1 toggles occupied/vacant with physical obstruction
- [ ] Slot 2 toggles occupied/vacant with physical obstruction
- [ ] Slot 3 toggles occupied/vacant with physical obstruction
- [ ] No TRIG/ECHO cross-wire behavior
- [ ] Stable readings across repeated obstruction cycles

## F. Continuous Stability Run (2+ hours)

- [ ] Run uninterrupted for at least 2 hours
- [ ] No persistent MQTT disconnect loops
- [ ] No sensor stuck at constant 0 cm or max range
- [ ] Event stream remains consistent in backend
- [ ] Frontend dashboard remains responsive and updates

## G. Post-Run Capture

- [ ] Save serial output logs
- [ ] Record anomalies and root-cause notes
- [ ] Export occupancy logs for analysis
- [ ] Update hardware handoff document with final observations
