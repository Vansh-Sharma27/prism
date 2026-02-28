#!/usr/bin/env python3
"""
MQTT Simulator for PRISM Parking System.

Simulates multiple parking slots publishing sensor data to the MQTT broker.
Useful for testing the backend without physical hardware.
"""
import argparse
import json
import random
import signal
import sys
import time
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)


# Default configuration
DEFAULT_BROKER = "localhost"
DEFAULT_PORT = 1883
DEFAULT_LOT_ID = "lot-a"
DEFAULT_INTERVAL = 5  # seconds between updates

# Slot configuration
SLOTS = ["slot-1", "slot-2", "slot-3", "slot-4", "slot-5", "slot-6"]

# Distance thresholds (cm)
OCCUPIED_DISTANCE_MIN = 3.0
OCCUPIED_DISTANCE_MAX = 12.0
VACANT_DISTANCE_MIN = 50.0
VACANT_DISTANCE_MAX = 150.0

# Probability of occupancy change per cycle
CHANGE_PROBABILITY = 0.1


class ParkingSimulator:
    """Simulates parking slot occupancy changes and publishes via MQTT."""

    def __init__(self, broker: str, port: int, lot_id: str, interval: float):
        self.broker = broker
        self.port = port
        self.lot_id = lot_id
        self.interval = interval
        self.running = False

        # Initialize slot states randomly
        self.slot_states = {slot: random.choice([True, False]) for slot in SLOTS}

        # MQTT client setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection."""
        if reason_code == 0:
            print(f"Connected to MQTT broker at {self.broker}:{self.port}")
        else:
            print(f"Failed to connect: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT disconnection."""
        print(f"Disconnected from broker: {reason_code}")

    def _generate_distance(self, is_occupied: bool) -> float:
        """Generate realistic distance reading based on occupancy."""
        if is_occupied:
            # Vehicle present: short distance with some noise
            base = random.uniform(OCCUPIED_DISTANCE_MIN, OCCUPIED_DISTANCE_MAX)
            noise = random.gauss(0, 0.5)
            return round(max(OCCUPIED_DISTANCE_MIN, base + noise), 1)
        else:
            # No vehicle: longer distance
            base = random.uniform(VACANT_DISTANCE_MIN, VACANT_DISTANCE_MAX)
            noise = random.gauss(0, 2.0)
            return round(base + noise, 1)

    def _maybe_toggle_occupancy(self, slot: str) -> bool:
        """Randomly toggle occupancy state with configured probability."""
        if random.random() < CHANGE_PROBABILITY:
            self.slot_states[slot] = not self.slot_states[slot]
            return True
        return False

    def _publish_slot_update(self, slot: str):
        """Publish a single slot update to MQTT."""
        is_occupied = self.slot_states[slot]
        distance = self._generate_distance(is_occupied)

        payload = {
            "distance_cm": distance,
            "occupied": is_occupied,
            "timestamp": int(time.time()),
        }

        topic = f"prism/{self.lot_id}/slot/{slot}"
        self.client.publish(topic, json.dumps(payload))

        status = "OCCUPIED" if is_occupied else "VACANT"
        print(f"  {slot}: {status:8} ({distance:5.1f} cm)")

    def _publish_heartbeat(self):
        """Publish device heartbeat."""
        payload = {
            "device": "simulator",
            "uptime": int(time.time()),
            "wifi_rssi": random.randint(-70, -40),
        }
        topic = f"prism/{self.lot_id}/heartbeat"
        self.client.publish(topic, json.dumps(payload))

    def start(self):
        """Start the simulation loop."""
        self.running = True

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Error connecting to broker: {e}")
            return

        print(f"\nSimulating {len(SLOTS)} slots in {self.lot_id}")
        print(f"Publishing every {self.interval} seconds")
        print("Press Ctrl+C to stop\n")

        cycle = 0
        while self.running:
            cycle += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Cycle {cycle}")

            # Update each slot
            for slot in SLOTS:
                changed = self._maybe_toggle_occupancy(slot)
                self._publish_slot_update(slot)

            # Publish heartbeat every 6 cycles (30 seconds at default interval)
            if cycle % 6 == 0:
                self._publish_heartbeat()
                print("  [heartbeat sent]")

            print()
            time.sleep(self.interval)

    def stop(self):
        """Stop the simulation."""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("\nSimulator stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="MQTT simulator for PRISM parking system"
    )
    parser.add_argument(
        "--broker",
        "-b",
        default=DEFAULT_BROKER,
        help=f"MQTT broker host (default: {DEFAULT_BROKER})",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"MQTT broker port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--lot",
        "-l",
        default=DEFAULT_LOT_ID,
        help=f"Parking lot ID (default: {DEFAULT_LOT_ID})",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between updates (default: {DEFAULT_INTERVAL})",
    )
    args = parser.parse_args()

    simulator = ParkingSimulator(args.broker, args.port, args.lot, args.interval)

    def signal_handler(sig, frame):
        simulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    simulator.start()


if __name__ == "__main__":
    main()
