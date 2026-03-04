# PRISM MQTT Simulator

Simulates parking slot sensor data for testing the PRISM backend without physical hardware.

## Requirements

```bash
pip install paho-mqtt
```

## Usage

```bash
# Basic usage (connects to localhost:1883)
python mqtt_simulator.py

# Custom broker
python mqtt_simulator.py --broker 192.168.1.100 --port 1883

# Custom lot ID and interval
python mqtt_simulator.py --lot lot-b --interval 3

# Multi-lot simulation in one process (recommended for full dashboard checks)
python mqtt_simulator.py --lots lot-a,lot-b --interval 3

# Day 6 dynamic mode with failure simulation and bounded run
python mqtt_simulator.py --mode dynamic --failure-probability 0.03 --cycles 240 --interval 2
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--broker, -b` | localhost | MQTT broker host |
| `--port, -p` | 1883 | MQTT broker port |
| `--lot, -l` | lot-a | Parking lot ID |
| `--lots` | unset | Comma-separated lot IDs for one process run (overrides `--lot`) |
| `--interval, -i` | 5 | Seconds between updates |
| `--mode` | dynamic | `dynamic` follows hour-based occupancy profile, `random` keeps static flips |
| `--failure-probability` | 0.02 | Chance per cycle that a slot enters simulated outage |
| `--failure-min-cycles` | 2 | Minimum outage duration |
| `--failure-max-cycles` | 6 | Maximum outage duration |
| `--cycles` | unset | Stop automatically after N cycles |
| `--seed` | unset | Random seed for reproducible runs |

## Behavior

- Simulates 6 parking slots (slot-1 through slot-6)
- Supports one lot (`--lot`) or multiple lots in a single process (`--lots lot-a,lot-b`)
- Dynamic mode tracks realistic hourly occupancy targets (rush/peak/low windows)
- Random mode preserves classic 10% per-cycle flipping
- Slots can occasionally enter simulated offline windows (no slot update published)
- Occupied slots report distances of 3-12 cm
- Vacant slots report distances of 50-150 cm
- Publishes to `prism/{lot_id}/slot/{slot_id}` topics
- Sends heartbeat every 30 seconds

## Testing with Backend

1. Start Mosquitto broker: `sudo systemctl start mosquitto`
2. Start backend: `cd ../backend && python run.py`
3. Run simulator: `python mqtt_simulator.py`
4. Watch backend logs for slot updates

## Export Training Dataset (Day 6)

After running simulator long enough to generate data, export backend `occupancy_logs`:

```bash
cd ../backend
python scripts/export_occupancy_logs.py --output ../data/processed/day6_occupancy_logs.csv
```

Optional filters:

```bash
# Export a single lot and cap rows
python scripts/export_occupancy_logs.py --lot-id lot-a --limit 10000

# Export by time range (ISO8601)
python scripts/export_occupancy_logs.py --start 2026-03-02T08:00:00Z --end 2026-03-02T18:00:00Z
```
