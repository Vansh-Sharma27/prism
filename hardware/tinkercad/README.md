# TinkerCAD Simulations

Arduino sketches for testing sensor logic before hardware deployment.

TinkerCAD lacks ESP32 support, so these use Arduino Uno. Pin mappings translate to ESP32 for production.

## Sketches

### single_sensor_test.ino

One HC-SR04 sensor. Outputs distance and occupancy status.

**Wiring:**
- VCC→5V, GND→GND, TRIG→D9, ECHO→D10
- LED on D13 (optional, 220Ω resistor)

### multi_sensor_simulation.ino

Three sensors for parking lot simulation. Outputs JSON for each slot.

**Wiring:**
- Sensor 1: TRIG→D2, ECHO→D3
- Sensor 2: TRIG→D4, ECHO→D5
- Sensor 3: TRIG→D6, ECHO→D7
- LEDs on D11, D12, D13 (optional)

## Output

Both output JSON matching the MQTT payload format:

```json
{"lot_id":"lot-a","slot_id":"slot-1","distance_cm":8.5,"occupied":true}
```

## Screenshots

Export validated circuits: Share → Image → Download PNG. Save here and commit.

## See Also

- `docs/wiring_diagram.md` - Pin mappings and breadboard layout
- `../esp32/multi_sensor_mqtt.ino` - Production firmware
