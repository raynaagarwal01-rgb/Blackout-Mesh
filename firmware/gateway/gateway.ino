/*
 * BLACKOUT MESH - gateway firmware
 *
 * Also acts as physical NODE_ID=2 itself (dual sensing role), so a
 * two-board build gives you two genuinely independent hardware
 * measurement points without buying a dedicated gateway-only board.
 * Receives ESP-NOW packets broadcast by other node boards and relays
 * every packet (its own + remote) to the laptop over USB serial as
 * one JSON object per line, e.g.:
 *
 *   {"node":1,"seq":42,"ts":12345,"voltage":3.31,"current":0.40,"anomaly":0.03,"state":0,"heartbeat":true}
 *
 * Point backend/run_gateway.py --source serial at this board's port.
 *
 * Board: "ESP32 Dev Module". Wiring is identical to firmware/node
 * (see docs/HARDWARE.md) — this board is a node too.
 */

#include <WiFi.h>
#include <esp_now.h>
#include "mesh_protocol.h"

#define NODE_ID 2

#define PIN_VOLTAGE    34
#define PIN_FAULT_BTN  25
#define PIN_LED_GREEN  26
#define PIN_LED_YELLOW 27
#define PIN_LED_RED    14

#define SEND_INTERVAL_MS 250
#define WARNING_THRESHOLD 0.35f
#define FAULT_THRESHOLD   0.65f
#define BASELINE_WARMUP_MS 5000
#define DEBOUNCE_MS 30

// Debounces a momentary button wired to GND (INPUT_PULLUP, active LOW).
// Sample every loop() iteration via read() - a raw transition only
// becomes the reported state once it has held steady for DEBOUNCE_MS,
// filtering out mechanical contact bounce.
struct DebouncedButton {
  int pin;
  bool stableState = false;
  bool rawState = false;
  unsigned long lastChangeMs = 0;

  bool read() {
    bool raw = (digitalRead(pin) == LOW);
    unsigned long now = millis();
    if (raw != rawState) {
      rawState = raw;
      lastChangeMs = now;
    }
    if ((now - lastChangeMs) > DEBOUNCE_MS) {
      stableState = raw;
    }
    return stableState;
  }
};

uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

DebouncedButton faultButton = {PIN_FAULT_BTN};
float baselineMean = -1.0f;
float baselineVar = 0.01f;
uint32_t seqCounter = 0;
unsigned long lastSend = 0;
unsigned long bootTime = 0;

void printPacket(const MeshPacket &p) {
  Serial.printf(
    "{\"node\":%u,\"seq\":%lu,\"ts\":%lu,\"voltage\":%.3f,\"current\":%.3f,\"anomaly\":%.3f,\"state\":%u,\"heartbeat\":%s}\n",
    p.node_id, (unsigned long)p.seq, (unsigned long)p.timestamp_ms,
    p.voltage, p.current, p.anomaly, p.state, p.heartbeat ? "true" : "false"
  );
}

// arduino-esp32 core 3.x (ESP-IDF 5.x) changed this callback's first
// argument from a raw MAC pointer to an esp_now_recv_info_t*; this
// signature matches the current esp_now_recv_cb_t in esp_now.h.
void onDataRecv(const esp_now_recv_info_t *recvInfo, const uint8_t *data, int len) {
  if (len != sizeof(MeshPacket)) return;
  MeshPacket packet;
  memcpy(&packet, data, sizeof(packet));
  printPacket(packet);
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
  esp_now_register_recv_cb(onDataRecv);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  bootTime = millis();
  Serial.printf("BLACKOUT MESH gateway online (also sensing as node %d)\n", NODE_ID);
}

float readVoltageProxy() {
  int raw = analogRead(PIN_VOLTAGE);
  return (raw / 4095.0f) * 5.0f;
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
  // Sample/debounce the button every iteration, independent of the
  // send cadence below, so a transition is never missed or delayed.
  bool faultPressed = faultButton.read();

  if (millis() - lastSend < SEND_INTERVAL_MS) {
    return;
  }
  lastSend = millis();

  float voltage = readVoltageProxy();

  if (faultPressed) {
    voltage = 0.0f;
  } else {
    updateBaseline(voltage);
  }

  float anomaly = faultPressed ? 1.0f : computeAnomaly(voltage);
  float current = voltage > 0.1f ? (voltage / 5.0f) * 1.2f : 0.0f;

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

  printPacket(packet);   // gateway's own reading goes straight to serial
}
