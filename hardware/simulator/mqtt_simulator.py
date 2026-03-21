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
from typing import Dict, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)


# Default configuration
DEFAULT_BROKER = "localhost"
DEFAULT_PORT = 1883
DEFAULT_LOT_ID = "lot-a"
DEFAULT_LOTS = [DEFAULT_LOT_ID, "lot-b"]
DEFAULT_INTERVAL = 5  # seconds between updates
DEFAULT_MODE = "dynamic"
# Keep demo-default stable; outage simulation can be enabled explicitly.
DEFAULT_FAILURE_PROBABILITY = 0.0
DEFAULT_FAILURE_MIN_CYCLES = 2
DEFAULT_FAILURE_MAX_CYCLES = 6

# Slot configuration
SLOTS = ["slot-1", "slot-2", "slot-3", "slot-4", "slot-5", "slot-6"]

# Distance thresholds (cm)
OCCUPIED_DISTANCE_MIN = 3.0
OCCUPIED_DISTANCE_MAX = 12.0
VACANT_DISTANCE_MIN = 50.0
VACANT_DISTANCE_MAX = 150.0

# Probability of occupancy change per cycle
CHANGE_PROBABILITY = 0.1

# Coarse campus occupancy profile by hour.
# Values represent expected occupied ratio for that hour.
HOURLY_OCCUPANCY_PROFILE = {
    0: 0.15,
    1: 0.12,
    2: 0.10,
    3: 0.10,
    4: 0.12,
    5: 0.16,
    6: 0.25,
    7: 0.45,
    8: 0.72,  # morning rush
    9: 0.78,
    10: 0.70,
    11: 0.62,
    12: 0.58,
    13: 0.52,
    14: 0.57,
    15: 0.68,  # afternoon peak
    16: 0.75,
    17: 0.71,
    18: 0.60,
    19: 0.48,
    20: 0.38,
    21: 0.30,
    22: 0.24,
    23: 0.18,
}


class ParkingSimulator:
    """Simulates parking slot occupancy changes and publishes via MQTT."""

    def __init__(
        self,
        broker: str,
        port: int,
        lot_ids: list[str],
        interval: float,
        mode: str,
        failure_probability: float,
        failure_min_cycles: int,
        failure_max_cycles: int,
        max_cycles: Optional[int],
        seed: Optional[int],
    ):
        self.broker = broker
        self.port = port
        self.lot_ids = list(dict.fromkeys(lot_ids))
        self.interval = interval
        self.mode = mode
        self.failure_probability = max(0.0, min(failure_probability, 1.0))
        self.failure_min_cycles = max(1, failure_min_cycles)
        self.failure_max_cycles = max(self.failure_min_cycles, failure_max_cycles)
        self.max_cycles = max_cycles
        self.running = False

        if seed is not None:
            random.seed(seed)

        # Initialize slot states randomly per lot.
        self.slot_states: Dict[str, Dict[str, bool]] = {
            lot_id: {slot: random.choice([True, False]) for slot in SLOTS}
            for lot_id in self.lot_ids
        }
        self.last_distances: Dict[str, Dict[str, float]] = {
            lot_id: {
                slot: self._generate_distance(self.slot_states[lot_id][slot])
                for slot in SLOTS
            }
            for lot_id in self.lot_ids
        }
        self.failure_cycles_remaining: Dict[str, Dict[str, int]] = {
            lot_id: {slot: 0 for slot in SLOTS}
            for lot_id in self.lot_ids
        }

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

        # No vehicle: longer distance
        base = random.uniform(VACANT_DISTANCE_MIN, VACANT_DISTANCE_MAX)
        noise = random.gauss(0, 2.0)
        return round(base + noise, 1)

    def _target_occupancy_ratio(self, hour: int) -> float:
        """Return target occupancy ratio for the current simulated hour."""
        return HOURLY_OCCUPANCY_PROFILE.get(hour, 0.5)

    def _effective_change_probability(self, lot_id: str, slot: str, hour: int) -> float:
        """
        Compute occupancy flip probability.

        In dynamic mode, the fleet drifts toward an hourly target occupancy ratio.
        """
        if self.mode == "random":
            return CHANGE_PROBABILITY

        target = self._target_occupancy_ratio(hour)
        lot_state = self.slot_states[lot_id]
        occupied_count = sum(1 for occupied in lot_state.values() if occupied)
        current_ratio = occupied_count / len(lot_state)
        delta = target - current_ratio

        if lot_state[slot]:
            # If we're above target, increase chance to vacate this slot.
            if delta < 0:
                return min(0.65, CHANGE_PROBABILITY + abs(delta) * 0.8)
            return max(0.02, CHANGE_PROBABILITY * 0.3)

        # Slot is vacant. If below target, increase chance to occupy.
        if delta > 0:
            return min(0.65, CHANGE_PROBABILITY + abs(delta) * 0.8)
        return max(0.02, CHANGE_PROBABILITY * 0.3)

    def _maybe_toggle_occupancy(self, lot_id: str, slot: str, hour: int) -> bool:
        """Toggle occupancy based on the selected simulator mode."""
        probability = self._effective_change_probability(lot_id, slot, hour)
        if random.random() < probability:
            self.slot_states[lot_id][slot] = not self.slot_states[lot_id][slot]
            return True
        return False

    def _slot_is_offline(self, lot_id: str, slot: str) -> bool:
        """Return whether a slot is in a simulated sensor outage window."""
        remaining = self.failure_cycles_remaining[lot_id][slot]
        if remaining > 0:
            self.failure_cycles_remaining[lot_id][slot] = remaining - 1
            return True

        if random.random() < self.failure_probability:
            self.failure_cycles_remaining[lot_id][slot] = random.randint(
                self.failure_min_cycles, self.failure_max_cycles
            ) - 1
            return True

        return False

    def _publish_slot_update(self, lot_id: str, slot: str) -> None:
        """Publish a single slot update to MQTT."""
        is_occupied = self.slot_states[lot_id][slot]
        distance = self._generate_distance(is_occupied)
        self.last_distances[lot_id][slot] = distance

        payload = {
            "distance_cm": distance,
            "occupied": is_occupied,
            "timestamp": int(time.time()),
        }

        topic = f"prism/{lot_id}/slot/{slot}"
        result = self.client.publish(topic, json.dumps(payload))
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"  {lot_id}/{slot}: publish failed rc={result.rc}")
            return

        status = "OCCUPIED" if is_occupied else "VACANT"
        print(f"  {lot_id}/{slot}: {status:8} ({distance:5.1f} cm)")

    def _publish_offline_heartbeat(self, lot_id: str, slot: str) -> None:
        """Emit an informational heartbeat event during simulated slot outage."""
        payload = {
            "device": "simulator",
            "slot_id": slot,
            "status": "offline",
            "timestamp": int(time.time()),
        }
        topic = f"prism/{lot_id}/heartbeat"
        self.client.publish(topic, json.dumps(payload))

    def _publish_heartbeat(self, lot_id: str) -> None:
        """Publish device heartbeat."""
        slots = [
            {
                "slot_id": slot,
                "distance_cm": self.last_distances[lot_id][slot],
                "occupied": self.slot_states[lot_id][slot],
            }
            for slot in SLOTS
            if self.failure_cycles_remaining[lot_id][slot] <= 0
        ]
        payload = {
            "device": "simulator",
            "uptime": int(time.time()),
            "wifi_rssi": random.randint(-70, -40),
            "slots": slots,
        }
        topic = f"prism/{lot_id}/heartbeat"
        self.client.publish(topic, json.dumps(payload))

    def _print_cycle_header(self, cycle: int, hour: int) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        target = self._target_occupancy_ratio(hour)
        lot_ratios = []
        for lot_id in self.lot_ids:
            lot_state = self.slot_states[lot_id]
            ratio = sum(1 for occupied in lot_state.values() if occupied) / len(lot_state)
            lot_ratios.append(f"{lot_id}={ratio:.0%}")
        print(
            f"[{timestamp}] Cycle {cycle} | "
            f"target={target:.0%} current({', '.join(lot_ratios)}) mode={self.mode}"
        )

    def _print_start_banner(self) -> None:
        total_slots = len(self.lot_ids) * len(SLOTS)
        print(f"\nSimulating {total_slots} slots across lots: {', '.join(self.lot_ids)}")
        print(f"Publishing every {self.interval} seconds")
        print(f"Mode: {self.mode}")
        missing_default_lots = [lot_id for lot_id in DEFAULT_LOTS if lot_id not in self.lot_ids]
        if missing_default_lots:
            print(
                "WARNING: running subset lot simulation. "
                "Missing lots will appear offline/static in the dashboard: "
                f"{', '.join(missing_default_lots)}"
            )
        print(
            f"Failure simulation: probability={self.failure_probability:.1%}, "
            f"duration={self.failure_min_cycles}-{self.failure_max_cycles} cycles"
        )
        if self.max_cycles is not None:
            print(f"Maximum cycles: {self.max_cycles}")
        print("Press Ctrl+C to stop\n")

    def start(self):
        """Start the simulation loop."""
        self.running = True

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as exc:
            print(f"Error connecting to broker: {exc}")
            return

        self._print_start_banner()

        cycle = 0
        while self.running:
            cycle += 1
            now = datetime.now()
            self._print_cycle_header(cycle, now.hour)

            # Update each slot for each configured lot.
            for lot_id in self.lot_ids:
                for slot in SLOTS:
                    if self._slot_is_offline(lot_id, slot):
                        self._publish_offline_heartbeat(lot_id, slot)
                        print(f"  {lot_id}/{slot}: OFFLINE  (simulated sensor outage)")
                        continue

                    self._maybe_toggle_occupancy(lot_id, slot, now.hour)
                    self._publish_slot_update(lot_id, slot)

            # Publish heartbeat every 6 cycles (30 seconds at default interval)
            if cycle % 6 == 0:
                for lot_id in self.lot_ids:
                    self._publish_heartbeat(lot_id)
                print(f"  [heartbeat sent: {', '.join(self.lot_ids)}]")

            print()

            if self.max_cycles is not None and cycle >= self.max_cycles:
                self.stop()
                break

            time.sleep(self.interval)

    def stop(self):
        """Stop the simulation."""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("\nSimulator stopped.")


def resolve_lot_ids(single_lot: str | None, lots_csv: str | None) -> list[str]:
    """
    Resolve lot IDs from CLI input.

    Rules:
    - If --lots is provided, use its comma-separated values.
    - Else if --lot is provided, use that one lot.
    - Else default to configured multi-lot simulation set.
    """
    if lots_csv:
        parsed_lots = [item.strip() for item in lots_csv.split(",") if item.strip()]
        if not parsed_lots:
            raise ValueError("--lots was provided but no valid lot IDs were found")
        return list(dict.fromkeys(parsed_lots))

    if single_lot:
        return [single_lot.strip()]

    return list(DEFAULT_LOTS)


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
        default=None,
        help=(
            "Single parking lot ID (optional). "
            f"If omitted, defaults to all configured lots: {','.join(DEFAULT_LOTS)}"
        ),
    )
    parser.add_argument(
        "--lots",
        default=None,
        help=(
            "Comma-separated lot IDs for multi-lot simulation "
            f"(example: {','.join(DEFAULT_LOTS)})"
        ),
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between updates (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--mode",
        choices=("dynamic", "random"),
        default=DEFAULT_MODE,
        help="Occupancy model: dynamic follows campus hour profile, random uses static flipping",
    )
    parser.add_argument(
        "--failure-probability",
        type=float,
        default=DEFAULT_FAILURE_PROBABILITY,
        help=(
            "Probability (0-1) that a slot enters simulated outage per cycle "
            f"(default: {DEFAULT_FAILURE_PROBABILITY})"
        ),
    )
    parser.add_argument(
        "--failure-min-cycles",
        type=int,
        default=DEFAULT_FAILURE_MIN_CYCLES,
        help=f"Minimum outage duration in cycles (default: {DEFAULT_FAILURE_MIN_CYCLES})",
    )
    parser.add_argument(
        "--failure-max-cycles",
        type=int,
        default=DEFAULT_FAILURE_MAX_CYCLES,
        help=f"Maximum outage duration in cycles (default: {DEFAULT_FAILURE_MAX_CYCLES})",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Optional max cycle count for bounded dataset runs",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible simulation runs",
    )
    args = parser.parse_args()

    try:
        lot_ids = resolve_lot_ids(args.lot, args.lots)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    simulator = ParkingSimulator(
        broker=args.broker,
        port=args.port,
        lot_ids=lot_ids,
        interval=args.interval,
        mode=args.mode,
        failure_probability=args.failure_probability,
        failure_min_cycles=args.failure_min_cycles,
        failure_max_cycles=args.failure_max_cycles,
        max_cycles=args.cycles,
        seed=args.seed,
    )

    def signal_handler(sig, frame):
        simulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    simulator.start()


if __name__ == "__main__":
    main()
