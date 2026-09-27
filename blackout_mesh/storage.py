"""SQLite persistence for readings and incidents.

One file (`blackout_mesh.db` by default) is shared by the gateway
process (writer) and the Streamlit dashboard (reader). SQLite handles
this single-writer/read-only-reader pattern fine at hackathon data
rates.
"""

import json
import sqlite3
import time
from contextlib import closing
from typing import Optional

from .config import DB_PATH
from .models import Incident

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    seq INTEGER,
    timestamp_ms INTEGER,
    voltage REAL,
    current REAL,
    anomaly REAL,
    state TEXT,
    source TEXT,
    received_at REAL
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY,
    opened_at REAL,
    closed_at REAL,
    section_from TEXT,
    section_to TEXT,
    severity TEXT,
    confidence REAL,
    evidence TEXT
);

CREATE INDEX IF NOT EXISTS idx_readings_node_time ON readings(node_id, received_at);
"""


class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=5)

    def insert_reading(self, reading, anomaly: float, state) -> None:
        state_value = state.value if hasattr(state, "value") else state
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO readings "
                "(node_id, seq, timestamp_ms, voltage, current, anomaly, state, source, received_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    reading.node_id, reading.seq, reading.timestamp_ms,
                    reading.voltage, reading.current, anomaly, state_value,
                    reading.source, reading.received_at,
                ),
            )
            conn.commit()

    def open_incident(self, incident: Incident) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO incidents "
                "(id, opened_at, section_from, section_to, severity, confidence, evidence) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    incident.incident_id, incident.opened_at,
                    incident.section[0], incident.section[1],
                    incident.severity.value, incident.confidence,
                    json.dumps(incident.evidence),
                ),
            )
            conn.commit()

    def update_incident(self, incident: Incident) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE incidents SET severity=?, confidence=?, evidence=? WHERE id=?",
                (incident.severity.value, incident.confidence,
                 json.dumps(incident.evidence), incident.incident_id),
            )
            conn.commit()

    def close_incident(self, incident: Incident) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE incidents SET closed_at=? WHERE id=?",
                (incident.closed_at, incident.incident_id),
            )
            conn.commit()

    def recent_readings(self, node_id: Optional[str] = None, limit: int = 300) -> list[dict]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            if node_id:
                cur = conn.execute(
                    "SELECT * FROM readings WHERE node_id=? ORDER BY id DESC LIMIT ?",
                    (node_id, limit),
                )
            else:
                cur = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()][::-1]

    def latest_per_node(self) -> dict[str, dict]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT r.* FROM readings r
                INNER JOIN (
                    SELECT node_id, MAX(id) AS max_id FROM readings GROUP BY node_id
                ) latest ON r.node_id = latest.node_id AND r.id = latest.max_id
                """
            )
            return {row["node_id"]: dict(row) for row in cur.fetchall()}

    def recent_incidents(self, limit: int = 20) -> list[dict]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]

    def active_incident_row(self) -> Optional[dict]:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM incidents WHERE closed_at IS NULL ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None
