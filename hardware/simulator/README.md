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
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--broker, -b` | localhost | MQTT broker host |
| `--port, -p` | 1883 | MQTT broker port |
| `--lot, -l` | lot-a | Parking lot ID |
| `--interval, -i` | 5 | Seconds between updates |

## Behavior

- Simulates 6 parking slots (slot-1 through slot-6)
- Each slot has a 10% chance of changing state per cycle
- Occupied slots report distances of 3-12 cm
- Vacant slots report distances of 50-150 cm
- Publishes to `prism/{lot_id}/slot/{slot_id}` topics
- Sends heartbeat every 30 seconds

## Testing with Backend

1. Start Mosquitto broker: `sudo systemctl start mosquitto`
2. Start backend: `cd ../backend && python run.py`
3. Run simulator: `python mqtt_simulator.py`
4. Watch backend logs for slot updates
