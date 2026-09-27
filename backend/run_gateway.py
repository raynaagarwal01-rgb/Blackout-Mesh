#!/usr/bin/env python3
"""BLACKOUT MESH gateway / inference service.

Reads node telemetry (from real hardware over serial, or from the
built-in simulator), runs the fault-localization algorithm on every
packet, and persists readings + incidents to SQLite for the dashboard
to read.

Examples
--------
No hardware yet - develop against the simulator:
    python backend/run_gateway.py --source simulator --scenario auto

Two ESP32 boards flashed with firmware/node + firmware/gateway:
    python backend/run_gateway.py --source serial --port /dev/ttyUSB0

Single-board simulator firmware (firmware/single_board_simulator):
    python backend/run_gateway.py --source serial --port /dev/ttyUSB0
(N4 is then filled in as a virtual node automatically.)
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blackout_mesh.config import (  # noqa: E402
    DB_PATH,
    HARDWARE_NODE_IDS,
    NODE_IDS,
    SERIAL_DEFAULT_BAUD,
    SERIAL_DEFAULT_PORT,
)
from blackout_mesh.inference import FaultInferenceEngine  # noqa: E402
from blackout_mesh.storage import Storage  # noqa: E402
from blackout_mesh.virtual_nodes import VirtualNodeGenerator  # noqa: E402


def _log(result: dict) -> None:
    section = result["section"]
    section_str = f"{section[0]}-{section[1]}" if section else "-"
    print(
        f"[{time.strftime('%H:%M:%S')}] severity={result['severity']:<15} "
        f"section={section_str:<8} confidence={result['confidence']:>5}% "
        f"states={result['node_states']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="BLACKOUT MESH gateway/inference service")
    parser.add_argument("--source", choices=["serial", "simulator"], default="simulator")
    parser.add_argument("--port", default=None, help=f"Serial port (default: {SERIAL_DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=None, help=f"Baud rate (default: {SERIAL_DEFAULT_BAUD})")
    parser.add_argument(
        "--scenario", default="auto",
        help="Simulator scenario: normal|overload|interruption|intermittent|connectivity_loss|auto",
    )
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    storage = Storage(args.db)
    engine = FaultInferenceEngine(storage=storage)

    virtual_ids = [nid for nid in NODE_IDS if nid not in HARDWARE_NODE_IDS]

    if args.source == "serial":
        from blackout_mesh.serial_source import read_serial

        port = args.port or SERIAL_DEFAULT_PORT
        baud = args.baud or SERIAL_DEFAULT_BAUD
        print(f"[gateway] reading hardware packets from {port} @ {baud} baud")
        source = read_serial(port, baud)

        if virtual_ids:
            print(f"[gateway] filling in virtual nodes: {virtual_ids}")
            VirtualNodeGenerator(virtual_ids, callback=engine.ingest).start()
    else:
        from blackout_mesh.simulator import Simulator

        print(f"[gateway] running fully-simulated demo (scenario={args.scenario})")
        source = Simulator(scenario=args.scenario).stream()

    try:
        for reading in source:
            result = engine.ingest(reading)
            _log(result)
    except KeyboardInterrupt:
        print("\n[gateway] stopped")


if __name__ == "__main__":
    main()
