/*
 * BLACKOUT MESH - sensor node firmware
 *
 * Reads a potentiometer as a voltage proxy, maintains an adaptive
 * baseline, computes a local anomaly score, drives a 3-color status
 * LED, and broadcasts a MeshPacket over ESP-NOW every ~250ms. A
 * momentary push button lets you manually trigger a fault (simulated
 * loss of feeder voltage) for the demo.
 *
 * Board: "ESP32 Dev Module" in the Arduino IDE board manager.
 * Set NODE_ID uniquely per flashed board (this is N1 by default; the
 * gateway board doubles as N2 — see firmware/gateway/gateway.ino).
 *
 * Wiring (see docs/HARDWARE.md for the full pin table):
 *   PIN_VOLTAGE   <- potentiometer wiper (outer legs to 3V3 and GND)
 *   PIN_FAULT_BTN <- momentary button to GND (uses internal pull-up)
 *   PIN_LED_GREEN/YELLOW/RED -> 220ohm resistor -> LED -> GND
 */

#include <WiFi.h>
#include <esp_now.h>
#include "mesh_protocol.h"

#define NODE_ID 1

#define PIN_VOLTAGE    34   // ADC1_CH6
#define PIN_FAULT_BTN  25
#define PIN_LED_GREEN  26
#define PIN_LED_YELLOW 27
#define PIN_LED_RED    14

#define SEND_INTERVAL_MS 250
#define WARNING_THRESHOLD 0.35f
#define FAULT_THRESHOLD   0.65f
#define BASELINE_WARMUP_MS 5000

uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

float baselineMean = -1.0f;
float baselineVar = 0.01f;
uint32_t seqCounter = 0;
unsigned long lastSend = 0;
unsigned long bootTime = 0;

void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  // no-op; kept for clarity/debugging if you add Serial logging here
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_FAULT_BTN, INPUT_PULLUP);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  analogReadResolution(12);

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_send_cb(onDataSent);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add broadcast peer");
  }

  bootTime = millis();
  Serial.printf("BLACKOUT MESH node %d ready\n", NODE_ID);
}

float readVoltageProxy() {
  int raw = analogRead(PIN_VOLTAGE);       // 0-4095
  return (raw / 4095.0f) * 5.0f;           // scaled to a 0-5V proxy
}

void updateBaseline(float value) {
  if (baselineMean < 0) {
    baselineMean = value;
    return;
  }
  bool warming = (millis() - bootTime) < BASELINE_WARMUP_MS;
  float alpha = warming ? 0.3f : 0.02f;
  float deviation = value - baselineMean;
  baselineMean += alpha * deviation;
  baselineVar = (1 - alpha) * (baselineVar + alpha * deviation * deviation);
  if (baselineVar < 1e-4f) baselineVar = 1e-4f;
}

float computeAnomaly(float value) {
  float std = sqrt(baselineVar);
  float z = fabs(value - baselineMean) / max(std, 0.05f);
  float score = z / 4.0f;
  if (score > 1.0f) score = 1.0f;
  if (score < 0.0f) score = 0.0f;
  return score;
}

void setLeds(uint8_t state) {
  digitalWrite(PIN_LED_GREEN, state == STATE_NORMAL);
  digitalWrite(PIN_LED_YELLOW, state == STATE_WARNING);
  digitalWrite(PIN_LED_RED, state == STATE_FAULT);
}

void loop() {
  if (millis() - lastSend < SEND_INTERVAL_MS) {
    return;
  }
  lastSend = millis();

  float voltage = readVoltageProxy();
  bool faultPressed = (digitalRead(PIN_FAULT_BTN) == LOW);

  if (faultPressed) {
    voltage = 0.0f;   // simulate loss of feeder voltage at this node
  } else {
    updateBaseline(voltage);
  }

  float anomaly = faultPressed ? 1.0f : computeAnomaly(voltage);
  float current = voltage > 0.1f ? (voltage / 5.0f) * 1.2f : 0.0f;  // simple derived current proxy

  uint8_t state = STATE_NORMAL;
  if (anomaly >= FAULT_THRESHOLD) state = STATE_FAULT;
  else if (anomaly >= WARNING_THRESHOLD) state = STATE_WARNING;
  setLeds(state);

  MeshPacket packet;
  packet.node_id = NODE_ID;
  packet.seq = ++seqCounter;
  packet.timestamp_ms = millis();
  packet.voltage = voltage;
  packet.current = current;
  packet.anomaly = anomaly;
  packet.state = state;
  packet.heartbeat = true;

  esp_now_send(broadcastAddress, (uint8_t *)&packet, sizeof(packet));
}
