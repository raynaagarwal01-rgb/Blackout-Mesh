/*
 * BLACKOUT MESH - single-board simulator firmware (ultra-budget tier,
 * ~Rs 300-600 if you already have one ESP32 + breadboard).
 *
 * Emulates a 3-node mesh on ONE ESP32: three potentiometers stand in
 * for N1/N2/N3 voltage, and three buttons trigger fault scenarios
 * directly. No ESP-NOW is used here — everything goes straight out
 * over USB serial as one JSON packet per node per cycle. Pair with:
 *
 *   python backend/run_gateway.py --source serial --port /dev/ttyUSB0
 *
 * and set HARDWARE_NODE_IDS = {"N1", "N2", "N3"} in
 * blackout_mesh/config.py so the backend fills in N4 as a virtual node.
 *
 * Board: "ESP32 Dev Module". See docs/HARDWARE.md for wiring.
 */

#include <math.h>

#define PIN_POT_N1 34
#define PIN_POT_N2 35
#define PIN_POT_N3 32

#define PIN_BTN_INTERRUPTION 25   // hold: feeder interruption between N2-N3
#define PIN_BTN_OVERLOAD     26   // hold: overload at N3
#define PIN_BTN_INTERMITTENT 27   // hold: rapidly toggling fault at N2-N3

#define SEND_INTERVAL_MS 250
#define WARNING_THRESHOLD 0.35f
#define FAULT_THRESHOLD   0.65f
#define BASELINE_WARMUP_MS 5000
#define INTERMITTENT_TOGGLE_MS 600
#define DEBOUNCE_MS 30

struct NodeModel {
  int pin;
  float baselineMean = -1.0f;
  float baselineVar = 0.01f;
  uint32_t seq = 0;
};

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

NodeModel nodes[3] = { {PIN_POT_N1}, {PIN_POT_N2}, {PIN_POT_N3} };
DebouncedButton interruptionButton = {PIN_BTN_INTERRUPTION};
DebouncedButton overloadButton = {PIN_BTN_OVERLOAD};
DebouncedButton intermittentButton = {PIN_BTN_INTERMITTENT};
unsigned long lastSend = 0;
unsigned long bootTime = 0;
bool intermittentToggle = false;
unsigned long lastToggle = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BTN_INTERRUPTION, INPUT_PULLUP);
  pinMode(PIN_BTN_OVERLOAD, INPUT_PULLUP);
  pinMode(PIN_BTN_INTERMITTENT, INPUT_PULLUP);
  analogReadResolution(12);
  bootTime = millis();
  Serial.println("BLACKOUT MESH single-board simulator ready (N1,N2,N3 -> backend adds virtual N4)");
}

float readVoltageProxy(int pin) {
  int raw = analogRead(pin);
  return (raw / 4095.0f) * 5.0f;
}

void updateBaseline(NodeModel &n, float value) {
  if (n.baselineMean < 0) {
    n.baselineMean = value;
    return;
  }
  bool warming = (millis() - bootTime) < BASELINE_WARMUP_MS;
  float alpha = warming ? 0.3f : 0.02f;
  float deviation = value - n.baselineMean;
  n.baselineMean += alpha * deviation;
  n.baselineVar = (1 - alpha) * (n.baselineVar + alpha * deviation * deviation);
  if (n.baselineVar < 1e-4f) n.baselineVar = 1e-4f;
}

float computeAnomaly(NodeModel &n, float value) {
  float std = sqrt(n.baselineVar);
  float z = fabs(value - n.baselineMean) / max(std, 0.05f);
  float score = z / 4.0f;
  if (score > 1.0f) score = 1.0f;
  if (score < 0.0f) score = 0.0f;
  return score;
}

void sendPacket(int nodeId, NodeModel &n, float voltage, float anomaly, uint8_t state) {
  float current = voltage > 0.1f ? (voltage / 5.0f) * 1.2f : 0.0f;
  Serial.printf(
    "{\"node\":%d,\"seq\":%lu,\"ts\":%lu,\"voltage\":%.3f,\"current\":%.3f,\"anomaly\":%.3f,\"state\":%u,\"heartbeat\":true}\n",
    nodeId, (unsigned long)(++n.seq), millis(), voltage, current, anomaly, state
  );
}

void loop() {
  // Sample/debounce buttons every iteration, independent of the send
  // cadence below, so a transition is never missed or delayed.
  bool interruption = interruptionButton.read();
  bool overload = overloadButton.read();
  bool intermittent = intermittentButton.read();

  if (millis() - lastSend < SEND_INTERVAL_MS) {
    return;
  }
  lastSend = millis();

  if (intermittent && millis() - lastToggle > INTERMITTENT_TOGGLE_MS) {
    intermittentToggle = !intermittentToggle;
    lastToggle = millis();
  }

  for (int i = 0; i < 3; i++) {
    int nodeId = i + 1;  // N1=1, N2=2, N3=3
    float voltage = readVoltageProxy(nodes[i].pin);
    float anomaly = 0.0f;
    uint8_t state = 0;  // 0=NORMAL 1=WARNING 2=FAULT
    bool silence = false;

    if (interruption && nodeId == 3) {
      silence = true;                 // N3 goes offline -> loss of feeder voltage
    } else if (interruption && nodeId == 2) {
      voltage *= 0.5f;
      anomaly = 0.9f;
      state = 2;
    } else if (overload && nodeId == 3) {
      voltage *= 1.4f;
      anomaly = 0.55f;
      state = 1;
    } else if (intermittent && intermittentToggle && (nodeId == 2 || nodeId == 3)) {
      voltage *= 0.4f;
      anomaly = 0.85f;
      state = 2;
    } else {
      updateBaseline(nodes[i], voltage);
      anomaly = computeAnomaly(nodes[i], voltage);
      state = anomaly >= FAULT_THRESHOLD ? 2 : (anomaly >= WARNING_THRESHOLD ? 1 : 0);
    }

    if (silence) continue;  // simply don't send this node's packet -> backend marks it OFFLINE

    sendPacket(nodeId, nodes[i], voltage, anomaly, state);
  }
}
