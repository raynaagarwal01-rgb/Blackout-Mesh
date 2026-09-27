"""Fully-software data source — no ESP32 required.

Lets the software/dashboard team start building immediately while
hardware is still being wired, and doubles as a rehearsal tool
(`--scenario auto` cycles through all four demo scenarios
unattended). See docs/DEMO_SCRIPT.md for what each scenario shows on
the dashboard.
"""

import random
import time
from itertools import cycle
from typing import Iterator

from .config import NODE_IDS
from .models import NodeReading

NORMAL_VOLTAGE = 3.3
NORMAL_CURRENT = 0.4

SCENARIOS = ["normal", "overload", "interruption", "intermittent", "connectivity_loss"]


class Simulator:
    def __init__(self, scenario: str = "auto", tick_s: float = 0.5, phase_s: float = 8.0):
        self.scenario = scenario
        self.tick_s = tick_s
        self.phase_s = phase_s
        self._seq = 0
        self._cycle = cycle(SCENARIOS)
        self._current = "normal" if scenario == "auto" else scenario
        self._phase_start = time.time()
        self._intermittent_toggle = False

    def _advance_auto_phase(self) -> None:
        if self.scenario != "auto":
            return
        now = time.time()
        if now - self._phase_start > self.phase_s:
            self._current = next(self._cycle)
            self._phase_start = now
            print(f"[simulator] --- scenario: {self._current} ---")

    def _reading(self, node_id: str, voltage: float, current: float, anomaly: float) -> NodeReading:
        self._seq += 1
        return NodeReading(
            node_id=node_id,
            seq=self._seq,
            timestamp_ms=int(time.time() * 1000),
            voltage=voltage,
            current=current,
            anomaly=anomaly,
            heartbeat=True,
            source="simulator",
        )

    def _normal_reading(self, node_id: str) -> NodeReading:
        return self._reading(
            node_id,
            NORMAL_VOLTAGE + random.uniform(-0.05, 0.05),
            NORMAL_CURRENT + random.uniform(-0.02, 0.02),
            random.uniform(0.0, 0.05),
        )

    def _tick_readings(self) -> list[NodeReading]:
        self._advance_auto_phase()
        scenario = self._current
        readings: list[NodeReading] = []

        if scenario == "overload":
            for node_id in NODE_IDS:
                if node_id == "N3":
                    readings.append(self._reading(node_id, NORMAL_VOLTAGE * 1.4, NORMAL_CURRENT * 1.6, 0.55))
                else:
                    readings.append(self._normal_reading(node_id))

        elif scenario == "interruption":
            for node_id in NODE_IDS:
                if node_id == "N2":
                    readings.append(self._reading(node_id, NORMAL_VOLTAGE * 0.5, NORMAL_CURRENT * 1.8, 0.9))
                elif node_id == "N3":
                    continue  # feeder voltage lost -> node goes silent -> backend infers OFFLINE
                else:
                    readings.append(self._normal_reading(node_id))

        elif scenario == "intermittent":
            self._intermittent_toggle = not self._intermittent_toggle
            for node_id in NODE_IDS:
                if node_id in ("N2", "N3") and self._intermittent_toggle:
                    readings.append(self._reading(node_id, NORMAL_VOLTAGE * 0.4, NORMAL_CURRENT * 1.9, 0.85))
                else:
                    readings.append(self._normal_reading(node_id))

        elif scenario == "connectivity_loss":
            for node_id in NODE_IDS:
                if node_id in ("N3", "N4"):
                    continue  # simulate loss of comms to the rest of the mesh
                readings.append(self._normal_reading(node_id))

        else:  # "normal"
            for node_id in NODE_IDS:
                readings.append(self._normal_reading(node_id))

        return readings

    def stream(self) -> Iterator[NodeReading]:
        while True:
            for reading in self._tick_readings():
                yield reading
            time.sleep(self.tick_s)
