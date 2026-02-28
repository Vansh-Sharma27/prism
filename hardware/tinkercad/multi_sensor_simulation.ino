/*
 * PRISM TinkerCAD Simulation - Multi-Sensor with Debounce & Filtering
 *
 * Features:
 * - 3 HC-SR04 ultrasonic sensors
 * - Debounce state machine (prevents false triggers)
 * - Median filtering (reduces noise)
 *
 * Designed for TinkerCAD using Arduino Uno.
 *
 * Wiring: See docs/wiring_diagram.md
 */

// Number of sensors
const int NUM_SENSORS = 3;

// Pin definitions
const int TRIG_PINS[NUM_SENSORS] = {2, 4, 6};
const int ECHO_PINS[NUM_SENSORS] = {3, 5, 7};
const int LED_PINS[NUM_SENSORS] = {11, 12, 13};

// Identifiers
const char* SLOT_IDS[NUM_SENSORS] = {"slot-1", "slot-2", "slot-3"};
const char* LOT_ID = "lot-a";

// Configuration
const float THRESHOLD_CM = 15.0;
const int READING_INTERVAL_MS = 500;
const int SENSOR_DELAY_MS = 60;
const unsigned long DEBOUNCE_MS = 5000;  // 5 seconds for simulation
const int MEDIAN_SAMPLES = 5;

// Slot state with debounce tracking
struct SlotState {
  bool occupied;
  bool pendingChange;
  bool pendingState;
  unsigned long lastChangeTime;
  float lastDistance;
};

SlotState slots[NUM_SENSORS];

void setup() {
  Serial.begin(9600);

  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(TRIG_PINS[i], OUTPUT);
    pinMode(ECHO_PINS[i], INPUT);
    pinMode(LED_PINS[i], OUTPUT);

    slots[i].occupied = false;
    slots[i].pendingChange = false;
    slots[i].pendingState = false;
    slots[i].lastChangeTime = 0;
    slots[i].lastDistance = 999.0;
  }

  Serial.println("PRISM Multi-Sensor (Debounce + Median Filter)");
  Serial.println("==============================================");
  Serial.print("Debounce: ");
  Serial.print(DEBOUNCE_MS);
  Serial.println("ms");
  Serial.println("----------------------------------------------");
}

float measureSingleDistance(int sensorIndex) {
  int trigPin = TRIG_PINS[sensorIndex];
  int echoPin = ECHO_PINS[sensorIndex];

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);

  if (duration == 0) {
    return 999.0;
  }

  return (duration * 0.0343) / 2.0;
}

// Bubble sort for median calculation
void sortArray(float arr[], int n) {
  for (int i = 0; i < n - 1; i++) {
    for (int j = 0; j < n - i - 1; j++) {
      if (arr[j] > arr[j + 1]) {
        float temp = arr[j];
        arr[j] = arr[j + 1];
        arr[j + 1] = temp;
      }
    }
  }
}

// Take multiple readings and return median
float getMedianDistance(int sensorIndex) {
  float readings[MEDIAN_SAMPLES];

  for (int i = 0; i < MEDIAN_SAMPLES; i++) {
    readings[i] = measureSingleDistance(sensorIndex);
    delay(10);
  }

  sortArray(readings, MEDIAN_SAMPLES);
  return readings[MEDIAN_SAMPLES / 2];
}

// Debounce state machine
bool updateSlotState(int index, float distance) {
  bool currentReading = (distance > 0 && distance < THRESHOLD_CM);
  slots[index].lastDistance = distance;

  // No change from current state
  if (currentReading == slots[index].occupied) {
    slots[index].pendingChange = false;
    return false;
  }

  // State differs - start or continue debounce
  if (!slots[index].pendingChange || slots[index].pendingState != currentReading) {
    // New pending change
    slots[index].pendingChange = true;
    slots[index].pendingState = currentReading;
    slots[index].lastChangeTime = millis();
    return false;
  }

  // Check if debounce period elapsed
  if (millis() - slots[index].lastChangeTime >= DEBOUNCE_MS) {
    slots[index].occupied = currentReading;
    slots[index].pendingChange = false;
    return true;  // State changed
  }

  return false;
}

void printStatus(int index, bool changed) {
  Serial.print(SLOT_IDS[index]);
  Serial.print(": ");
  Serial.print(slots[index].lastDistance, 1);
  Serial.print("cm -> ");
  Serial.print(slots[index].occupied ? "OCCUPIED" : "VACANT");

  if (slots[index].pendingChange) {
    unsigned long remaining = DEBOUNCE_MS - (millis() - slots[index].lastChangeTime);
    Serial.print(" [pending: ");
    Serial.print(remaining);
    Serial.print("ms]");
  }

  if (changed) {
    Serial.print(" *CHANGED*");
  }

  Serial.println();

  // Update LED
  digitalWrite(LED_PINS[index], slots[index].occupied ? HIGH : LOW);
}

void printJSON(int index) {
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

void loop() {
  Serial.println();

  for (int i = 0; i < NUM_SENSORS; i++) {
    float distance = getMedianDistance(i);
    bool changed = updateSlotState(i, distance);
    printStatus(i, changed);
    printJSON(i);
    delay(SENSOR_DELAY_MS);
  }

  // Summary
  int occ = 0;
  for (int i = 0; i < NUM_SENSORS; i++) {
    if (slots[i].occupied) occ++;
  }
  Serial.print("Summary: ");
  Serial.print(occ);
  Serial.print("/");
  Serial.print(NUM_SENSORS);
  Serial.println(" occupied");
  Serial.println("----------------------------------------------");

  delay(READING_INTERVAL_MS);
}
