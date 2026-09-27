"""Optional Layer-2 ML cross-check (Isolation Forest).

Per the project's "hardware performs sensing, software performs
intelligence" design: this NEVER overrides the explainable, rule-based
score in inference.py. It only adds a supporting signal ("the ML layer
also flags this node") surfaced in the evidence list — useful when a
judge asks "where's the AI?" without sacrificing explainability.

Degrades gracefully: if scikit-learn isn't installed, `available()`
returns False and the rest of the system runs unaffected.
"""

try:
    from sklearn.ensemble import IsolationForest
    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _SKLEARN_AVAILABLE = False

import numpy as np


class MLAnomalyLayer:
    def __init__(self, window: int = 200, min_samples: int = 20):
        self.window = window
        self.min_samples = min_samples
        self._samples: list[list[float]] = []

    @staticmethod
    def available() -> bool:
        return _SKLEARN_AVAILABLE

    def update(self, voltage: float, current: float) -> float | None:
        """Feed one reading, return an anomaly score in [0, 1] or None."""
        if not _SKLEARN_AVAILABLE:
            return None

        self._samples.append([voltage, current])
        if len(self._samples) > self.window:
            self._samples.pop(0)
        if len(self._samples) < self.min_samples:
            return None

        arr = np.array(self._samples)
        model = IsolationForest(n_estimators=50, contamination=0.1, random_state=0).fit(arr)
        raw_score = -model.score_samples(arr[-1:])[0]  # higher = more anomalous
        return float(max(0.0, min(1.0, raw_score)))
