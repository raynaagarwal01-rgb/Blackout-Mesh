"""Reads newline-delimited JSON packets from an ESP32 over USB serial.

Expected line format (see firmware/node, firmware/gateway,
firmware/single_board_simulator):

    {"node":2,"seq":42,"ts":12345,"voltage":3.31,"current":0.40,"anomaly":0.03,"state":0,"heartbeat":true}

Resilient to the board being unplugged/replugged mid-demo: a lost or
never-opened connection is retried on a fixed delay rather than
crashing the gateway process (backend/run_gateway.py just keeps
waiting on this generator).
"""

import json
import time
from typing import Iterator

import serial

from .config import SERIAL_DEFAULT_BAUD, SERIAL_DEFAULT_PORT
from .models import NodeReading


def _node_id(raw) -> str:
    if isinstance(raw, int):
        return f"N{raw}"
    text = str(raw)
    return text if text.startswith("N") else f"N{text}"


def _parse_line(raw_line: str) -> NodeReading | None:
    if not raw_line:
        return None
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError:
        return None
    if "node" not in data:
        return None

    return NodeReading(
        node_id=_node_id(data["node"]),
        seq=int(data.get("seq", 0)),
        timestamp_ms=int(data.get("ts", 0)),
        voltage=float(data.get("voltage", 0.0)),
        current=float(data.get("current", 0.0)),
        anomaly=data.get("anomaly"),
        heartbeat=bool(data.get("heartbeat", True)),
        source="hardware",
        received_at=time.time(),
    )


def read_serial(
    port: str = SERIAL_DEFAULT_PORT,
    baud: int = SERIAL_DEFAULT_BAUD,
    reconnect_delay_s: float = 2.0,
    serial_factory=serial.Serial,
) -> Iterator[NodeReading]:
    while True:
        try:
            with serial_factory(port, baud, timeout=1) as ser:
                print(f"[serial] connected to {port}")
                while True:
                    try:
                        raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
                    except serial.SerialException as exc:
                        print(f"[serial] lost connection to {port}: {exc}")
                        break  # drop to the outer loop and try to reopen the port

                    reading = _parse_line(raw_line)
                    if reading is not None:
                        yield reading
        except serial.SerialException as exc:
            print(f"[serial] could not open {port}: {exc}")

        print(f"[serial] retrying {port} in {reconnect_delay_s}s...")
        time.sleep(reconnect_delay_s)
