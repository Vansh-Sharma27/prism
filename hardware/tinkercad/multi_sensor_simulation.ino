/*
 * PRISM TinkerCAD Simulation - Multi-Sensor Configuration
 *
 * This sketch simulates 3 HC-SR04 ultrasonic sensors for parking slots.
 * Designed for TinkerCAD using Arduino Uno (ESP32 not available in TinkerCAD).
 *
 * Hardware Setup in TinkerCAD:
 * - Arduino Uno
 * - 3x HC-SR04 Ultrasonic Sensors
 *
 * Sensor 1 (Slot A):
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TRIG -> Pin 2
 *   - ECHO -> Pin 3
 *
 * Sensor 2 (Slot B):
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TRIG -> Pin 4
 *   - ECHO -> Pin 5
 *
 * Sensor 3 (Slot C):
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TRIG -> Pin 6
 *   - ECHO -> Pin 7
 *
 * Status LEDs (optional):
 *   - LED1 (Slot A) -> Pin 11 (via 220Ω)
 *   - LED2 (Slot B) -> Pin 12 (via 220Ω)
 *   - LED3 (Slot C) -> Pin 13 (via 220Ω)
 *
 * Behavior:
 * - Reads all 3 sensors sequentially every 500ms
 * - Outputs JSON-formatted data for each slot
 * - LEDs indicate occupied status
 */

// Number of sensors
const int NUM_SENSORS = 3;

// Pin definitions for each sensor
const int TRIG_PINS[NUM_SENSORS] = {2, 4, 6};
const int ECHO_PINS[NUM_SENSORS] = {3, 5, 7};
const int LED_PINS[NUM_SENSORS] = {11, 12, 13};

// Slot identifiers (matching backend schema)
const char* SLOT_IDS[NUM_SENSORS] = {"slot-1", "slot-2", "slot-3"};
const char* LOT_ID = "lot-a";

// Configuration
const float THRESHOLD_CM = 15.0;      // Distance threshold for occupancy
const int READING_INTERVAL_MS = 500;  // Time between full sensor sweeps
const int SENSOR_DELAY_MS = 60;       // Delay between individual sensor reads

// State tracking for debounce (simplified for simulation)
struct SlotState {
  bool occupied;
  float lastDistance;
};

SlotState slots[NUM_SENSORS];

void setup() {
  Serial.begin(9600);

  // Initialize all sensor pins
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(TRIG_PINS[i], OUTPUT);
    pinMode(ECHO_PINS[i], INPUT);
    pinMode(LED_PINS[i], OUTPUT);

    // Initialize state
    slots[i].occupied = false;
    slots[i].lastDistance = 999.0;
  }

  Serial.println("PRISM Multi-Sensor Parking System");
  Serial.println("==================================");
  Serial.print("Lot ID: ");
  Serial.println(LOT_ID);
  Serial.print("Sensors: ");
  Serial.println(NUM_SENSORS);
  Serial.print("Threshold: ");
  Serial.print(THRESHOLD_CM);
  Serial.println(" cm");
  Serial.println("----------------------------------");
}

float measureDistance(int sensorIndex) {
  int trigPin = TRIG_PINS[sensorIndex];
  int echoPin = ECHO_PINS[sensorIndex];

  // Send ultrasonic pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure echo time (30ms timeout = ~5m max range)
  long duration = pulseIn(echoPin, HIGH, 30000);

  // Calculate distance (speed of sound = 343m/s = 0.0343cm/us)
  float distance = (duration * 0.0343) / 2.0;

  // Return 999 for timeout/invalid readings
  if (duration == 0) {
    return 999.0;
  }

  return distance;
}

void updateSlot(int index, float distance) {
  bool isOccupied = (distance > 0 && distance < THRESHOLD_CM);

  slots[index].lastDistance = distance;
  slots[index].occupied = isOccupied;

  // Update LED
  digitalWrite(LED_PINS[index], isOccupied ? HIGH : LOW);
}

void printSlotStatus(int index) {
  // Human-readable format
  Serial.print(SLOT_IDS[index]);
  Serial.print(": ");
  Serial.print(slots[index].lastDistance, 1);
  Serial.print("cm -> ");
  Serial.println(slots[index].occupied ? "OCCUPIED" : "VACANT");
}

void printJSONPayload(int index) {
  // MQTT-compatible JSON payload
  Serial.print("{\"lot_id\":\"");
  Serial.print(LOT_ID);
  Serial.print("\",\"slot_id\":\"");
  Serial.print(SLOT_IDS[index]);
  Serial.print("\",\"distance_cm\":");
  Serial.print(slots[index].lastDistance, 1);
  Serial.print(",\"occupied\":");
  Serial.print(slots[index].occupied ? "true" : "false");
  Serial.print(",\"timestamp\":");
  Serial.print(millis());
  Serial.println("}");
}

void printSummary() {
  int occupied = 0;
  int vacant = 0;

  for (int i = 0; i < NUM_SENSORS; i++) {
    if (slots[i].occupied) {
      occupied++;
    } else {
      vacant++;
    }
  }

  Serial.println("----------------------------------");
  Serial.print("Summary: ");
  Serial.print(occupied);
  Serial.print(" occupied, ");
  Serial.print(vacant);
  Serial.println(" vacant");
  Serial.println("==================================");
}

void loop() {
  Serial.println();

  // Read all sensors
  for (int i = 0; i < NUM_SENSORS; i++) {
    float distance = measureDistance(i);
    updateSlot(i, distance);
    printSlotStatus(i);
    printJSONPayload(i);

    // Small delay between sensors to avoid interference
    delay(SENSOR_DELAY_MS);
  }

  printSummary();

  // Wait before next reading cycle
  delay(READING_INTERVAL_MS);
}
