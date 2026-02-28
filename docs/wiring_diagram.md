# PRISM Hardware Wiring Documentation

This document describes the wiring for PRISM parking sensor hardware configurations.

## TinkerCAD Simulation Setup

TinkerCAD uses Arduino Uno for simulation (ESP32 not available). The pin mappings translate to ESP32 for production.

### Single Sensor Configuration

| Component | Arduino Uno Pin | Notes |
|-----------|-----------------|-------|
| HC-SR04 VCC | 5V | Power supply |
| HC-SR04 GND | GND | Ground |
| HC-SR04 TRIG | D9 | Trigger pulse output |
| HC-SR04 ECHO | D10 | Echo pulse input |
| Status LED+ | D13 | Via 220Ω resistor |
| Status LED- | GND | Common ground |

### Multi-Sensor Configuration (3 Slots)

| Component | Arduino Uno Pin | ESP32 Equivalent | Notes |
|-----------|-----------------|------------------|-------|
| **Sensor 1 (Slot A)** ||||
| HC-SR04 VCC | 5V | 5V/VIN | Shared power |
| HC-SR04 GND | GND | GND | Shared ground |
| HC-SR04 TRIG | D2 | GPIO 25 | Trigger |
| HC-SR04 ECHO | D3 | GPIO 26 | Echo |
| LED1 | D11 | GPIO 32 | Status indicator |
| **Sensor 2 (Slot B)** ||||
| HC-SR04 VCC | 5V | 5V/VIN | Shared power |
| HC-SR04 GND | GND | GND | Shared ground |
| HC-SR04 TRIG | D4 | GPIO 27 | Trigger |
| HC-SR04 ECHO | D5 | GPIO 14 | Echo |
| LED2 | D12 | GPIO 33 | Status indicator |
| **Sensor 3 (Slot C)** ||||
| HC-SR04 VCC | 5V | 5V/VIN | Shared power |
| HC-SR04 GND | GND | GND | Shared ground |
| HC-SR04 TRIG | D6 | GPIO 12 | Trigger |
| HC-SR04 ECHO | D7 | GPIO 13 | Echo |
| LED3 | D13 | GPIO 2 | Status indicator |

### Power Requirements

| Component | Voltage | Current (typical) | Current (peak) |
|-----------|---------|-------------------|----------------|
| HC-SR04 | 5V DC | 2mA | 15mA |
| ESP32 | 3.3-5V | 80mA | 500mA (WiFi TX) |
| LED (x3) | 2V | 20mA each | 20mA each |

**Total estimated current:** ~200mA idle, ~600mA peak (WiFi transmit)

## ESP32 Production Wiring

For actual deployment with ESP32 DevKit V1 (30-pin):

### Pin Assignments

```
ESP32 DevKit V1 Pinout for PRISM
================================

       3V3 [  ] [ ] VIN (5V input)
       GND [  ] [ ] GND
       D15 [  ] [ ] D13 ← HC-SR04 #3 ECHO
       D2  [  ] [ ] D12 ← HC-SR04 #3 TRIG
       D4  [  ] [ ] D14 ← HC-SR04 #2 ECHO
       D16 [  ] [ ] D27 ← HC-SR04 #2 TRIG
       D17 [  ] [ ] D26 ← HC-SR04 #1 ECHO
       D5  [  ] [ ] D25 ← HC-SR04 #1 TRIG
       D18 [  ] [ ] D33 ← LED #2
       D19 [  ] [ ] D32 ← LED #1
       D21 [  ] [ ] D35 (input only)
       D22 [  ] [ ] D34 (input only)
       D23 [  ] [ ] D39 (input only)
       EN  [  ] [ ] D36 (input only)
```

### ESP32 Pin Selection Notes

1. **Avoid GPIO 0, 2, 15** for critical functions (boot strapping pins)
2. **Avoid GPIO 6-11** - connected to internal flash
3. **GPIO 34-39** are input-only
4. **ADC2 pins** (GPIO 0,2,4,12-15,25-27) don't work when WiFi is active
5. Use ADC1 pins for analog if needed (GPIO 32-39)

### Breadboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  BREADBOARD LAYOUT - 3 SENSOR CONFIGURATION                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ HC-SR04 │  │ HC-SR04 │  │ HC-SR04 │                     │
│  │ Slot A  │  │ Slot B  │  │ Slot C  │                     │
│  │         │  │         │  │         │                     │
│  │V G T E  │  │V G T E  │  │V G T E  │                     │
│  └┬─┬─┬─┬──┘  └┬─┬─┬─┬──┘  └┬─┬─┬─┬──┘                     │
│   │ │ │ │      │ │ │ │      │ │ │ │                        │
│   │ │ │ └──────┼─┼─┼─┼──────┼─┼─┼─┼── ECHO pins            │
│   │ │ └────────┼─┼─┼─┼──────┼─┼─┼─┼── TRIG pins            │
│   │ └──────────┼─┼─┼─┼──────┼─┼─┴─┴── GND (common)         │
│   └────────────┼─┴─┴─┴──────┴─┴────── VCC (common 5V)      │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    ESP32 DevKit                         ││
│  │  GPIO25─TRIG_A  GPIO26─ECHO_A  GPIO32─LED_A             ││
│  │  GPIO27─TRIG_B  GPIO14─ECHO_B  GPIO33─LED_B             ││
│  │  GPIO12─TRIG_C  GPIO13─ECHO_C  GPIO2─LED_C              ││
│  │                                                         ││
│  │  VIN─────5V rail    GND─────GND rail                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Power Rails:                                               │
│  + (red)  ────────────────────────────── 5V from USB/Supply │
│  - (blue) ────────────────────────────── GND                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Sensor Calibration

### Distance Thresholds

| Environment | Threshold (cm) | Notes |
|-------------|---------------|-------|
| TinkerCAD simulation | 10 | Tabletop testing |
| Indoor parking | 15 | Standard car detection |
| Outdoor parking | 20 | Allow for wind/debris |
| Motorcycle slots | 8 | Smaller vehicles |

### Calibration Procedure

1. Place known object at 10cm, verify reading
2. Place known object at 50cm, verify reading
3. Adjust threshold based on actual slot dimensions
4. Test with actual vehicle if available

## Safety Notes

1. HC-SR04 operates at 5V - use level shifter if connecting to 3.3V MCU logic
2. Keep sensor face clear of obstructions
3. Avoid pointing sensors at each other (interference)
4. Add 60ms delay between sensor readings to prevent cross-talk

## Files Reference

| File | Description |
|------|-------------|
| `single_sensor_test.ino` | Basic single sensor TinkerCAD sketch |
| `multi_sensor_simulation.ino` | 3-sensor TinkerCAD simulation |
| `../esp32/multi_sensor_mqtt.ino` | Production ESP32 firmware |
