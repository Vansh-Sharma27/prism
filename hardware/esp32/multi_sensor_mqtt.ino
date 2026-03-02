/*
 * PRISM ESP32 Production Firmware - Multi-Sensor with MQTT
 *
 * Hardware:
 * - ESP32 DevKit V1
 * - 3x HC-SR04 Ultrasonic Sensors
 *
 * GPIO Mapping:
 * - Sensor 1: TRIG=GPIO5,  ECHO=GPIO18
 * - Sensor 2: TRIG=GPIO19, ECHO=GPIO21
 * - Sensor 3: TRIG=GPIO22, ECHO=GPIO23
 *
 * Features:
 * - WiFi connectivity
 * - MQTT publishing
 * - Median filtering (5 readings)
 * - Debounce (30 seconds)
 * - Heartbeat every 60 seconds
 * - Sensor timeout and invalid-range error handling
 * - Serial debug output with per-sensor health counters
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ===== CONFIGURATION - UPDATE THESE =====
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER = "YOUR_MQTT_BROKER_IP";
const int MQTT_PORT = 1883;
const char* LOT_ID = "lot-a";
const char* DEVICE_ID = "esp32-01";
// =========================================

// Sensor configuration
struct Sensor {
  int trigPin;
  int echoPin;
  const char* slotId;
  bool lastState;
  unsigned long lastChangeTime;
  unsigned int consecutiveErrors;
  unsigned long lastErrorPublish;
};

Sensor sensors[] = {
  {5, 18, "slot-1", false, 0, 0, 0},
  {19, 21, "slot-2", false, 0, 0, 0},
  {22, 23, "slot-3", false, 0, 0, 0}
};
const int NUM_SENSORS = sizeof(sensors) / sizeof(sensors[0]);

// Thresholds
const float OCCUPANCY_THRESHOLD_CM = 15.0;
const float MIN_VALID_DISTANCE_CM = 2.0;
const float MAX_VALID_DISTANCE_CM = 400.0;
const unsigned long SENSOR_ECHO_TIMEOUT_US = 30000;
const unsigned long DEBOUNCE_MS = 30000;
const unsigned long HEARTBEAT_INTERVAL_MS = 60000;
const unsigned long SENSOR_ERROR_PUBLISH_INTERVAL_MS = 15000;
const unsigned int SENSOR_ERROR_THRESHOLD = 3;
const int MEDIAN_READINGS = 5;

// Optional status LED (on many ESP32 boards, GPIO2 is built-in LED)
const int STATUS_LED_PIN = 2;

// MQTT topics
char topicBuffer[100];
char payloadBuffer[240];

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastHeartbeat = 0;

bool connectWiFi();
bool connectMQTT();
float measureDistance(int trigPin, int echoPin);
float getMedianDistance(int trigPin, int echoPin);
void publishSlotStatus(Sensor& sensor, float distance, bool isOccupied);
void publishSensorError(Sensor& sensor, const char* errorCode);
void publishHeartbeat();
void updateStatusLed(bool wifiOk, bool mqttOk, bool sensorFault);

void setup() {
  Serial.begin(115200);
  Serial.println("\nPRISM Parking Sensor - ESP32");
  Serial.println("============================");

  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  // Initialize sensor pins
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(sensors[i].trigPin, OUTPUT);
    pinMode(sensors[i].echoPin, INPUT);
    digitalWrite(sensors[i].trigPin, LOW);
  }

  bool wifiOk = connectWiFi();

  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  bool mqttOk = false;
  if (wifiOk) {
    mqttOk = connectMQTT();
  }

  updateStatusLed(wifiOk, mqttOk, false);
}

bool connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("\nWiFi connection failed after 30 attempts.");
  return false;
}

bool connectMQTT() {
  int attempts = 0;
  while (!mqtt.connected() && attempts < 6) {
    Serial.print("Connecting to MQTT...");
    if (mqtt.connect(DEVICE_ID)) {
      Serial.println("connected!");
      return true;
    }

    Serial.print("failed, rc=");
    Serial.print(mqtt.state());
    Serial.println(" retrying in 5s");
    delay(5000);
    attempts++;
  }

  Serial.println("MQTT connection failed after retries.");
  return mqtt.connected();
}

float measureDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, SENSOR_ECHO_TIMEOUT_US);
  if (duration <= 0) {
    return -1.0;
  }

  float distance = (duration * 0.0343) / 2.0;
  if (distance < MIN_VALID_DISTANCE_CM || distance > MAX_VALID_DISTANCE_CM) {
    return -1.0;
  }

  return distance;
}

float getMedianDistance(int trigPin, int echoPin) {
  float readings[MEDIAN_READINGS];
  int validCount = 0;

  for (int i = 0; i < MEDIAN_READINGS; i++) {
    float value = measureDistance(trigPin, echoPin);
    if (value > 0) {
      readings[validCount] = value;
      validCount++;
    }
    delay(10);
  }

  if (validCount < 3) {
    return -1.0;
  }

  // Bubble sort valid readings only
  for (int i = 0; i < validCount - 1; i++) {
    for (int j = 0; j < validCount - i - 1; j++) {
      if (readings[j] > readings[j + 1]) {
        float temp = readings[j];
        readings[j] = readings[j + 1];
        readings[j + 1] = temp;
      }
    }
  }

  return readings[validCount / 2];
}

void publishSlotStatus(Sensor& sensor, float distance, bool isOccupied) {
  snprintf(topicBuffer, sizeof(topicBuffer), "prism/%s/slot/%s", LOT_ID, sensor.slotId);

  snprintf(
    payloadBuffer,
    sizeof(payloadBuffer),
    "{\"distance_cm\":%.1f,\"occupied\":%s,\"timestamp\":%lu}",
    distance,
    isOccupied ? "true" : "false",
    millis()
  );

  bool ok = mqtt.publish(topicBuffer, payloadBuffer);
  if (!ok) {
    Serial.print("Publish failed for slot topic: ");
    Serial.println(topicBuffer);
    return;
  }

  Serial.print("Published: ");
  Serial.print(topicBuffer);
  Serial.print(" -> ");
  Serial.println(payloadBuffer);
}

void publishSensorError(Sensor& sensor, const char* errorCode) {
  snprintf(topicBuffer, sizeof(topicBuffer), "prism/%s/sensor/%s/error", LOT_ID, sensor.slotId);

  snprintf(
    payloadBuffer,
    sizeof(payloadBuffer),
    "{\"device\":\"%s\",\"slot\":\"%s\",\"error\":\"%s\",\"timestamp\":%lu}",
    DEVICE_ID,
    sensor.slotId,
    errorCode,
    millis()
  );

  mqtt.publish(topicBuffer, payloadBuffer);
  Serial.print("Sensor error published: ");
  Serial.println(payloadBuffer);
}

void publishHeartbeat() {
  snprintf(topicBuffer, sizeof(topicBuffer), "prism/%s/heartbeat", LOT_ID);

  snprintf(
    payloadBuffer,
    sizeof(payloadBuffer),
    "{\"device\":\"%s\",\"uptime\":%lu,\"wifi_rssi\":%d}",
    DEVICE_ID,
    millis() / 1000,
    WiFi.RSSI()
  );

  bool ok = mqtt.publish(topicBuffer, payloadBuffer);
  if (!ok) {
    Serial.println("Heartbeat publish failed");
    return;
  }

  Serial.println("Heartbeat sent");
}

void updateStatusLed(bool wifiOk, bool mqttOk, bool sensorFault) {
  static bool blinkState = false;
  static unsigned long lastBlink = 0;
  unsigned long now = millis();

  if (wifiOk && mqttOk && !sensorFault) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    return;
  }

  // Blink patterns for degraded states
  unsigned long interval = sensorFault ? 700 : 250;
  if (now - lastBlink >= interval) {
    blinkState = !blinkState;
    digitalWrite(STATUS_LED_PIN, blinkState ? HIGH : LOW);
    lastBlink = now;
  }
}

void loop() {
  bool wifiOk = (WiFi.status() == WL_CONNECTED);
  if (!wifiOk) {
    wifiOk = connectWiFi();
    if (!wifiOk) {
      updateStatusLed(false, false, false);
      delay(1000);
      return;
    }
  }

  bool mqttOk = mqtt.connected();
  if (!mqttOk) {
    mqttOk = connectMQTT();
    if (!mqttOk) {
      updateStatusLed(true, false, false);
      delay(1000);
      return;
    }
  }

  mqtt.loop();

  unsigned long now = millis();
  bool sensorFault = false;

  for (int i = 0; i < NUM_SENSORS; i++) {
    float distance = getMedianDistance(sensors[i].trigPin, sensors[i].echoPin);

    if (distance < 0) {
      sensors[i].consecutiveErrors++;
      sensorFault = true;

      Serial.print("[WARN] ");
      Serial.print(sensors[i].slotId);
      Serial.print(" invalid reading (errors=");
      Serial.print(sensors[i].consecutiveErrors);
      Serial.println(")");

      if (sensors[i].consecutiveErrors >= SENSOR_ERROR_THRESHOLD &&
          now - sensors[i].lastErrorPublish > SENSOR_ERROR_PUBLISH_INTERVAL_MS) {
        publishSensorError(sensors[i], "invalid_distance");
        sensors[i].lastErrorPublish = now;
      }

      continue;
    }

    // Reset error streak when a valid reading arrives.
    sensors[i].consecutiveErrors = 0;

    bool isOccupied = (distance < OCCUPANCY_THRESHOLD_CM);

    Serial.print("[DEBUG] ");
    Serial.print(sensors[i].slotId);
    Serial.print(" distance=");
    Serial.print(distance, 1);
    Serial.print("cm occupied=");
    Serial.println(isOccupied ? "true" : "false");

    if (isOccupied != sensors[i].lastState && now - sensors[i].lastChangeTime > DEBOUNCE_MS) {
      sensors[i].lastState = isOccupied;
      sensors[i].lastChangeTime = now;
      publishSlotStatus(sensors[i], distance, isOccupied);
    }
  }

  if (now - lastHeartbeat > HEARTBEAT_INTERVAL_MS) {
    publishHeartbeat();
    lastHeartbeat = now;
  }

  updateStatusLed(wifiOk, mqttOk, sensorFault);
  delay(500);
}
