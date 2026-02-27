/*
 * PRISM TinkerCAD Simulation - Single Ultrasonic Sensor
 * 
 * This sketch is for TinkerCAD simulation using Arduino Uno
 * (ESP32 is not available in TinkerCAD, so we use Uno for simulation)
 * 
 * Hardware Setup in TinkerCAD:
 * - Arduino Uno
 * - HC-SR04 Ultrasonic Sensor
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TRIG -> Pin 9
 *   - ECHO -> Pin 10
 * - LED (optional, for visual feedback)
 *   - Anode -> Pin 13 (via 220Ω resistor)
 *   - Cathode -> GND
 * 
 * Behavior:
 * - Measures distance every 500ms
 * - Prints "OCCUPIED" if distance < 10cm (tabletop simulation threshold)
 * - Prints "AVAILABLE" otherwise
 * - LED ON when occupied
 */

// Pin definitions
const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int LED_PIN = 13;

// Configuration
const float THRESHOLD_CM = 10.0;  // Tabletop simulation threshold
const int READING_INTERVAL_MS = 500;

void setup() {
  Serial.begin(9600);
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  Serial.println("PRISM Parking Sensor - TinkerCAD Simulation");
  Serial.println("============================================");
}

float measureDistance() {
  // Send ultrasonic pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Measure echo time
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms timeout
  
  // Calculate distance (speed of sound = 343m/s)
  float distance = (duration * 0.0343) / 2.0;
  
  return distance;
}

void loop() {
  float distance = measureDistance();
  bool isOccupied = (distance > 0 && distance < THRESHOLD_CM);
  
  // Visual feedback
  digitalWrite(LED_PIN, isOccupied ? HIGH : LOW);
  
  // Serial output (simulating MQTT payload)
  Serial.print("Distance: ");
  Serial.print(distance, 1);
  Serial.print(" cm | Status: ");
  Serial.println(isOccupied ? "OCCUPIED" : "AVAILABLE");
  
  // JSON format (for testing)
  Serial.print("{\"distance_cm\":");
  Serial.print(distance, 1);
  Serial.print(",\"occupied\":");
  Serial.print(isOccupied ? "true" : "false");
  Serial.println("}");
  Serial.println("---");
  
  delay(READING_INTERVAL_MS);
}
