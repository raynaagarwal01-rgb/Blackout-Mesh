#pragma once
#include <stdint.h>

// Shared ESP-NOW payload. Keep this identical in firmware/node and
// firmware/gateway (both copies must match byte-for-byte).
typedef struct __attribute__((packed)) {
  uint8_t node_id;       // 1, 2, 3 ...
  uint32_t seq;
  uint32_t timestamp_ms;
  float voltage;         // analog proxy, 0-5V range
  float current;         // analog proxy, derived from voltage
  float anomaly;         // 0.0-1.0, computed locally against an adaptive baseline
  uint8_t state;         // 0=NORMAL 1=WARNING 2=FAULT
  bool heartbeat;
} MeshPacket;

enum NodeStateCode { STATE_NORMAL = 0, STATE_WARNING = 1, STATE_FAULT = 2 };
