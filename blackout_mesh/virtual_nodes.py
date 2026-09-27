"""Background generator for software-emulated ("virtual") nodes.

Fills in NODE_IDS not covered by physical hardware (see
config.HARDWARE_NODE_IDS) with steady, near-baseline readings so the
dashboard always shows a complete feeder — matching the recommended
"2 real ESP32 + 2 virtual nodes" build.
"""

import random
import threading
import time
from typing import Callable, Iterable, Optional

from .models import NodeReading

NORMAL_VOLTAGE = 3.3
NORMAL_CURRENT = 0.4


class VirtualNodeGenerator:
    def __init__(
        self,
        node_ids: Iterable[str],
        callback: Optional[Callable[[NodeReading], None]] = None,
        interval_s: float = 0.5,
    ):
        self.node_ids = list(node_ids)
        self.callback = callback
        self.interval_s = interval_s
        self._seq = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "VirtualNodeGenerator":
        if not self.node_ids:
            return self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            for node_id in self.node_ids:
                self._seq += 1
                reading = NodeReading(
                    node_id=node_id,
                    seq=self._seq,
                    timestamp_ms=int(time.time() * 1000),
                    voltage=NORMAL_VOLTAGE + random.uniform(-0.05, 0.05),
                    current=NORMAL_CURRENT + random.uniform(-0.02, 0.02),
                    anomaly=random.uniform(0.0, 0.05),
                    heartbeat=True,
                    source="virtual",
                )
                if self.callback:
                    self.callback(reading)
            time.sleep(self.interval_s)
