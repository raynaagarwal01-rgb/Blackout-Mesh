import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"
    OFFLINE = "OFFLINE"


class IncidentSeverity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    LOCALIZED_EVENT = "LOCALIZED_EVENT"
    CRITICAL_EVENT = "CRITICAL_EVENT"


@dataclass
class NodeReading:
    """One telemetry packet from a node (real or virtual)."""

    node_id: str
    seq: int
    timestamp_ms: int
    voltage: float
    current: float
    anomaly: Optional[float] = None   # locally-computed score, 0..1 (None => backend derives it)
    heartbeat: bool = True
    source: str = "hardware"          # "hardware" | "virtual" | "simulator"
    received_at: float = field(default_factory=time.time)


@dataclass
class Incident:
    """A localized/critical event, as tracked in-memory and persisted to SQLite."""

    incident_id: int
    opened_at: float
    section: tuple[str, str]
    severity: IncidentSeverity
    confidence: float
    evidence: list[str]
    closed_at: Optional[float] = None
