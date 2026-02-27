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
};

Sensor sensors[] = {
  {5, 18, "slot-1", false, 0},
  {19, 21, "slot-2", false, 0},
  {22, 23, "slot-3", false, 0}
};
const int NUM_SENSORS = sizeof(sensors) / sizeof(sensors[0]);

// Thresholds
const float OCCUPANCY_THRESHOLD_CM = 15.0;  // Production threshold
const unsigned long DEBOUNCE_MS = 30000;    // 30 second debounce
const unsigned long HEARTBEAT_INTERVAL_MS = 60000;
const int MEDIAN_READINGS = 5;

// MQTT topics
char topicBuffer[100];
char payloadBuffer[200];

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastHeartbeat = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("\nPRISM Parking Sensor - ESP32");
  Serial.println("============================");
  
  // Initialize sensor pins
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(sensors[i].trigPin, OUTPUT);
    pinMode(sensors[i].echoPin, INPUT);
  }
  
  // Connect to WiFi
  connectWiFi();
  
  // Setup MQTT
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  connectMQTT();
}

void connectWiFi() {
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
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqtt.connect(DEVICE_ID)) {
      Serial.println("connected!");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqtt.state());
      Serial.println(" retrying in 5s");
      delay(5000);
    }
  }
}

float measureDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000);
  float distance = (duration * 0.0343) / 2.0;
  
  return distance;
}

float getMedianDistance(int trigPin, int echoPin) {
  float readings[MEDIAN_READINGS];
  
  for (int i = 0; i < MEDIAN_READINGS; i++) {
    readings[i] = measureDistance(trigPin, echoPin);
    delay(10);
  }
  
  // Simple bubble sort
  for (int i = 0; i < MEDIAN_READINGS - 1; i++) {
    for (int j = 0; j < MEDIAN_READINGS - i - 1; j++) {
      if (readings[j] > readings[j + 1]) {
        float temp = readings[j];
        readings[j] = readings[j + 1];
        readings[j + 1] = temp;
      }
    }
  }
  
  return readings[MEDIAN_READINGS / 2];
}

void publishSlotStatus(Sensor& sensor, float distance, bool isOccupied) {
  snprintf(topicBuffer, sizeof(topicBuffer), 
           "prism/%s/slot/%s", LOT_ID, sensor.slotId);
  
  snprintf(payloadBuffer, sizeof(payloadBuffer),
           "{\"distance_cm\":%.1f,\"occupied\":%s,\"timestamp\":%lu}",
           distance, isOccupied ? "true" : "false", millis());
  
  mqtt.publish(topicBuffer, payloadBuffer);
  
  Serial.print("Published: ");
  Serial.print(topicBuffer);
  Serial.print(" -> ");
  Serial.println(payloadBuffer);
}

void publishHeartbeat() {
  snprintf(topicBuffer, sizeof(topicBuffer), 
           "prism/%s/heartbeat", LOT_ID);
  
  snprintf(payloadBuffer, sizeof(payloadBuffer),
           "{\"device\":\"%s\",\"uptime\":%lu,\"wifi_rssi\":%d}",
           DEVICE_ID, millis() / 1000, WiFi.RSSI());
  
  mqtt.publish(topicBuffer, payloadBuffer);
  Serial.println("Heartbeat sent");
}

void loop() {
  // Maintain connections
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  if (!mqtt.connected()) {
    connectMQTT();
  }
  mqtt.loop();
  
  unsigned long now = millis();
  
  // Check each sensor
  for (int i = 0; i < NUM_SENSORS; i++) {
    float distance = getMedianDistance(sensors[i].trigPin, sensors[i].echoPin);
    bool isOccupied = (distance > 0 && distance < OCCUPANCY_THRESHOLD_CM);
    
    // Check if state changed with debounce
    if (isOccupied != sensors[i].lastState) {
      if (now - sensors[i].lastChangeTime > DEBOUNCE_MS) {
        sensors[i].lastState = isOccupied;
        sensors[i].lastChangeTime = now;
        publishSlotStatus(sensors[i], distance, isOccupied);
      }
    }
  }
  
  // Heartbeat
  if (now - lastHeartbeat > HEARTBEAT_INTERVAL_MS) {
    publishHeartbeat();
    lastHeartbeat = now;
  }
  
  delay(500);  // Main loop interval
}
