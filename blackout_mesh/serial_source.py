"""Reads newline-delimited JSON packets from an ESP32 over USB serial.

Expected line format (see firmware/node, firmware/gateway,
firmware/single_board_simulator):

    {"node":2,"seq":42,"ts":12345,"voltage":3.31,"current":0.40,"anomaly":0.03,"state":0,"heartbeat":true}
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


def read_serial(port: str = SERIAL_DEFAULT_PORT, baud: int = SERIAL_DEFAULT_BAUD) -> Iterator[NodeReading]:
    with serial.Serial(port, baud, timeout=1) as ser:
        while True:
            raw_line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if "node" not in data:
                continue

            yield NodeReading(
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
