/*
 * PRISM ESP32-CAM Firmware Skeleton
 *
 * Purpose:
 * - Initialize camera on AI Thinker ESP32-CAM module
 * - Capture JPEG frames at interval
 * - POST frames to backend endpoint
 *
 * NOTE:
 * - Update WiFi credentials and BACKEND_UPLOAD_URL before deployment.
 * - This is a scaffold for Day 5 integration and may require board-specific tuning.
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ===== CONFIGURATION - UPDATE THESE =====
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DEVICE_ID = "esp32-cam-01";
const char* LOT_ID = "lot-a";
const char* BACKEND_UPLOAD_URL = "http://192.168.1.100:5000/api/v1/camera/upload";
const unsigned long CAPTURE_INTERVAL_MS = 10000;
// =========================================

// AI Thinker ESP32-CAM pin definitions
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

unsigned long lastCapture = 0;

bool connectWiFi();
bool initCamera();
bool captureAndUpload();

void setup() {
  Serial.begin(115200);
  Serial.println("\nPRISM ESP32-CAM Skeleton");
  Serial.println("=========================");

  if (!initCamera()) {
    Serial.println("[FATAL] Camera initialization failed.");
  }

  if (!connectWiFi()) {
    Serial.println("[WARN] WiFi not connected during setup.");
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  unsigned long now = millis();
  if (now - lastCapture >= CAPTURE_INTERVAL_MS) {
    if (WiFi.status() == WL_CONNECTED) {
      captureAndUpload();
    } else {
      Serial.println("[WARN] Skip upload: WiFi disconnected.");
    }
    lastCapture = now;
  }

  delay(100);
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
    Serial.println("\nWiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("\nWiFi connection failed");
  return false;
}

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 14;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.print("Camera init failed with error: 0x");
    Serial.println(err, HEX);
    return false;
  }

  Serial.println("Camera initialized successfully");
  return true;
}

bool captureAndUpload() {
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) {
    Serial.println("[ERROR] Camera capture failed");
    return false;
  }

  HTTPClient http;
  http.begin(BACKEND_UPLOAD_URL);
  http.addHeader("Content-Type", "application/octet-stream");
  http.addHeader("X-Device-ID", DEVICE_ID);
  http.addHeader("X-Lot-ID", LOT_ID);

  int status = http.POST(frame->buf, frame->len);
  if (status > 0) {
    Serial.print("Upload success, status=");
    Serial.print(status);
    Serial.print(", bytes=");
    Serial.println(frame->len);
  } else {
    Serial.print("[ERROR] Upload failed: ");
    Serial.println(http.errorToString(status));
  }

  http.end();
  esp_camera_fb_return(frame);
  return status > 0;
}
