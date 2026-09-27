"""BLACKOUT MESH — low-cost, outage-resilient cooperative edge sensing.

This package implements the software side of the prototype: ingesting
node telemetry (from real ESP32 hardware over serial, or from the
built-in simulator), tracking per-node baselines/anomaly, and running
the explainable fault-localization algorithm described in
docs/ALGORITHM.md.
"""

__version__ = "0.1.0"
