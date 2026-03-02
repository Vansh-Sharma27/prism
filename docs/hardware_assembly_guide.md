# PRISM Hardware Assembly Guide

This guide provides a complete wiring and bring-up workflow for the PRISM parking node using ESP32 + HC-SR04 sensors.

## 1. Hardware Checklist

- 1x ESP32 DevKit V1 (30-pin)
- 3x HC-SR04 ultrasonic sensor modules
- 1x Breadboard (830 tie-point recommended)
- Jumper wires (male-male, male-female)
- 1x USB cable for ESP32
- Optional: 3x LEDs + 220 ohm resistors
- Optional: multimeter for continuity and voltage checks

## 2. Safety and Setup Before Wiring

1. Place the breadboard and ESP32 on a non-conductive table.
2. Keep ESP32 unplugged while placing wires.
3. Confirm all grounds are common before power-on.
4. Route cables neatly and avoid crossing TRIG/ECHO lines tightly in parallel.

## 3. ESP32 Pin Mapping

| Slot | HC-SR04 TRIG | HC-SR04 ECHO | Sensor Topic Suffix | Notes |
|------|--------------|--------------|---------------------|-------|
| Slot 1 | GPIO5 | GPIO18 | `slot-1` | Node A |
| Slot 2 | GPIO19 | GPIO21 | `slot-2` | Node A |
| Slot 3 | GPIO22 | GPIO23 | `slot-3` | Node A |

Shared wiring:

| Signal | ESP32 Pin | Destination |
|--------|-----------|-------------|
| 5V power rail | VIN (5V) | HC-SR04 VCC pins |
| Ground rail | GND | HC-SR04 GND pins |
| Status LED (optional) | GPIO2 | LED anode via 220 ohm resistor |

## 4. Step-by-Step Wiring Instructions

1. Insert ESP32 into the breadboard center channel.
2. Connect ESP32 `VIN` to the positive power rail.
3. Connect ESP32 `GND` to the ground rail.
4. Place Sensor 1, connect `VCC -> 5V rail`, `GND -> GND rail`, `TRIG -> GPIO5`, `ECHO -> GPIO18`.
5. Place Sensor 2, connect `VCC -> 5V rail`, `GND -> GND rail`, `TRIG -> GPIO19`, `ECHO -> GPIO21`.
6. Place Sensor 3, connect `VCC -> 5V rail`, `GND -> GND rail`, `TRIG -> GPIO22`, `ECHO -> GPIO23`.
7. (Optional) Wire status LED: `GPIO2 -> 220 ohm resistor -> LED anode`, LED cathode to GND.
8. Re-check every wire against the pin map before connecting USB.
9. Connect ESP32 via USB and open serial monitor at `115200` baud.

## 5. Bring-Up Validation Sequence

1. Flash `hardware/esp32/multi_sensor_mqtt.ino`.
2. Confirm serial output shows WiFi connection and MQTT connection success.
3. Confirm periodic heartbeat logs.
4. Place an object under each sensor and confirm slot status publishes to MQTT topic `prism/<lot_id>/slot/<slot_id>`.
5. Verify distance readings are stable and occupancy toggles near threshold.

## 6. Common Mistakes to Avoid

- Swapping TRIG and ECHO wires for one or more sensors.
- Forgetting a common ground between all sensors and ESP32.
- Powering HC-SR04 from 3.3V when the circuit expects 5V behavior.
- Using boot strap pins (GPIO0/GPIO2/GPIO15) for critical sensor signals.
- Mounting sensors too close together, causing ultrasonic cross-talk.
- Running long unshielded ECHO wires without secure connections.

## 7. Troubleshooting

| Symptom | Likely Cause | Fix |
|--------|--------------|-----|
| No serial output | Wrong COM port or baud rate | Select correct port, set monitor to 115200 |
| WiFi fails repeatedly | Wrong credentials or weak signal | Recheck SSID/password, move near router |
| MQTT connect retry loop | Broker unreachable or wrong host/port | Verify broker IP/port and broker process |
| Distance always 0 cm | ECHO pin not connected or timeout | Re-seat ECHO wire and test continuity |
| Distance always very high | Sensor facing no target or power issue | Check VCC/GND and sensor orientation |
| Rapid status flapping | Threshold too close to object noise | Increase debounce and median filtering |
| One sensor offline, others work | Pin mismatch for that channel | Re-verify only that slot’s TRIG/ECHO map |

## 8. Debug Checklist for Lab Session

- `mosquitto_sub -h localhost -t "prism/#" -v` shows slot updates.
- Each slot publishes at least one update within 10 seconds.
- Heartbeat topic updates every 60 seconds.
- No repeated sensor timeout errors after wiring is stabilized.

## 9. Related Files

- Firmware: `hardware/esp32/multi_sensor_mqtt.ino`
- Camera skeleton: `hardware/sketches/prism_camera/prism_camera.ino`
- MQTT simulator: `hardware/simulator/mqtt_simulator.py`
- Wiring reference: `docs/wiring_diagram.md`
