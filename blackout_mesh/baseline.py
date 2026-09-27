"""Per-node adaptive baseline + z-score anomaly scoring.

Mirrors the logic that also runs locally on each ESP32 (see
firmware/node/node.ino) so the backend can (a) cross-check/derive an
anomaly score for nodes that don't send one, and (b) score fully
virtual/simulated nodes the same way.
"""

import math

from .config import BASELINE_EMA_ALPHA, BASELINE_WARMUP_S


class BaselineTracker:
    def __init__(self, alpha: float = BASELINE_EMA_ALPHA, warmup_s: float = BASELINE_WARMUP_S):
        self.alpha = alpha
        self.warmup_s = warmup_s
        self._start: dict[str, float] = {}
        self._mean: dict[str, float] = {}
        self._var: dict[str, float] = {}

    def update(self, node_id: str, value: float, now: float) -> None:
        if node_id not in self._mean:
            self._mean[node_id] = value
            self._var[node_id] = 1e-4
            self._start[node_id] = now
            return

        mean = self._mean[node_id]
        var = self._var[node_id]
        deviation = value - mean
        warming = (now - self._start[node_id]) < self.warmup_s
        alpha = 0.3 if warming else self.alpha

        self._mean[node_id] = mean + alpha * deviation
        self._var[node_id] = max((1 - alpha) * (var + alpha * deviation ** 2), 1e-4)

    def anomaly_score(self, node_id: str, value: float) -> float:
        mean = self._mean.get(node_id, value)
        var = self._var.get(node_id, 1e-4)
        std = math.sqrt(var)
        z = abs(value - mean) / max(std, 0.05)
        return max(0.0, min(1.0, z / 4.0))
