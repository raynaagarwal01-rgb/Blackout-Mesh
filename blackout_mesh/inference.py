"""The core BLACKOUT MESH fault-localization algorithm.

For every edge (i, j) of the feeder topology we compute:

    Score(i,j) = w1 * anomaly_evidence(i,j)
               + w2 * state_discontinuity(i,j)
               + w3 * neighbor_agreement(i,j)
               + w4 * topology_consistency(i,j)

and report the edge with the highest score as the probable affected
section, with a plain-English evidence list. See docs/ALGORITHM.md for
the full explanation and rationale (in particular: why a node going
silent/offline is treated as *evidence*, not just a communication
failure).

This module is intentionally dependency-light and deterministic/rule
-based so every incident is explainable — the optional ML layer
(ml_layer.py) only ever adds a supporting evidence line, never overrides
this score.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .baseline import BaselineTracker
from .config import ANOMALY_WEIGHTS, NODE_IDS, OFFLINE_TIMEOUT_S, SEVERITY_THRESHOLDS
from .ml_layer import MLAnomalyLayer
from .models import Incident, IncidentSeverity, NodeReading, NodeState
from .topology import Topology


@dataclass
class NodeStatus:
    node_id: str
    state: NodeState = NodeState.NORMAL
    last_reading: Optional[NodeReading] = None
    last_seen: float = 0.0
    ml_score: Optional[float] = None


class FaultInferenceEngine:
    def __init__(self, storage=None, node_ids=None, topology_edges=None):
        """`node_ids`/`topology_edges` default to config.NODE_IDS/TOPOLOGY_EDGES
        (a straight-line feeder), but accept any tree-shaped topology — e.g.
        a branching feeder where one node splits into two downstream
        sections. Pass them explicitly to use an alternate topology without
        editing config.py (e.g. from a script or test)."""
        self.topology = Topology(topology_edges)
        self.baseline = BaselineTracker()
        node_ids = node_ids if node_ids is not None else NODE_IDS
        self.nodes: dict[str, NodeStatus] = {nid: NodeStatus(node_id=nid) for nid in node_ids}
        self.ml_layers: dict[str, MLAnomalyLayer] = {nid: MLAnomalyLayer() for nid in node_ids}
        self.storage = storage
        self._incident_seq = 0
        self.active_incident: Optional[Incident] = None
        self._lock = threading.Lock()

    def ingest(self, reading: NodeReading) -> dict:
        with self._lock:
            return self._ingest_locked(reading)

    def _ingest_locked(self, reading: NodeReading) -> dict:
        now = time.time()
        status = self.nodes.setdefault(reading.node_id, NodeStatus(node_id=reading.node_id))
        status.last_reading = reading
        status.last_seen = reading.received_at or now

        self.baseline.update(reading.node_id, reading.voltage, now)
        anomaly = reading.anomaly
        if anomaly is None:
            anomaly = self.baseline.anomaly_score(reading.node_id, reading.voltage)
        reading.anomaly = anomaly

        ml_layer = self.ml_layers.setdefault(reading.node_id, MLAnomalyLayer())
        status.ml_score = ml_layer.update(reading.voltage, reading.current)

        if anomaly >= SEVERITY_THRESHOLDS["critical"]:
            status.state = NodeState.FAULT
        elif anomaly >= SEVERITY_THRESHOLDS["warning"]:
            status.state = NodeState.WARNING
        else:
            status.state = NodeState.NORMAL

        if self.storage:
            self.storage.insert_reading(reading, anomaly, status.state)

        return self._evaluate(now)

    def _mark_offline_nodes(self, now: float) -> None:
        # Note: a node that has NEVER reported has last_seen == 0.0, so
        # (now - 0.0) is always far past the timeout — it correctly shows
        # OFFLINE from the start rather than defaulting to NORMAL.
        for status in self.nodes.values():
            if (now - status.last_seen) > OFFLINE_TIMEOUT_S:
                status.state = NodeState.OFFLINE

    def _anomaly_of(self, status: Optional[NodeStatus]) -> float:
        if not status:
            return 0.0
        if status.state == NodeState.OFFLINE:
            return 1.0  # silence is itself evidence, whether or not it ever reported
        if not status.last_reading:
            return 0.0
        return max(0.0, min(1.0, status.last_reading.anomaly or 0.0))

    def _discontinuity(self, si: Optional[NodeStatus], sj: Optional[NodeStatus]) -> float:
        if not si or not sj:
            return 0.0
        if si.state == NodeState.OFFLINE or sj.state == NodeState.OFFLINE:
            return 1.0
        if not si.last_reading or not sj.last_reading:
            return 0.0
        vi, vj = si.last_reading.voltage, sj.last_reading.voltage
        span = max(abs(vi), abs(vj), 0.5)
        return max(0.0, min(1.0, abs(vi - vj) / span))

    def _neighbor_agreement(self, i: str, j: str, abnormal: set[str]) -> float:
        """High when the edge (i,j) explains the anomaly *and* nodes just
        outside it stay normal — i.e. the boundary of the affected section
        sits exactly on this edge, not somewhere else on the feeder."""
        if not ({i, j} & abnormal):
            return 0.0
        outside = (set(self.topology.neighbors(i)) | set(self.topology.neighbors(j))) - {i, j}
        return 1.0 if not (outside & abnormal) else 0.4

    def _evaluate(self, now: float) -> dict:
        self._mark_offline_nodes(now)

        abnormal = {
            nid for nid, s in self.nodes.items()
            if s.state in (NodeState.WARNING, NodeState.FAULT, NodeState.OFFLINE)
        }

        best_edge = None
        best_score = 0.0
        best_breakdown: dict = {}

        for edge in self.topology.edges():
            i, j = edge
            si, sj = self.nodes.get(i), self.nodes.get(j)

            anomaly_evidence = (self._anomaly_of(si) + self._anomaly_of(sj)) / 2.0
            discontinuity = self._discontinuity(si, sj)
            neighbor_agreement = self._neighbor_agreement(i, j, abnormal)
            topo_consistency = self.topology.contiguous_consistency(edge, abnormal)

            w = ANOMALY_WEIGHTS
            score = (
                w["w1_anomaly"] * anomaly_evidence
                + w["w2_discontinuity"] * discontinuity
                + w["w3_neighbor_agreement"] * neighbor_agreement
                + w["w4_topology_consistency"] * topo_consistency
            )

            if score > best_score:
                best_score = score
                best_edge = edge
                best_breakdown = {
                    "anomaly_evidence": anomaly_evidence,
                    "discontinuity": discontinuity,
                    "neighbor_agreement": neighbor_agreement,
                    "topology_consistency": topo_consistency,
                }

        severity = self._classify(best_score, abnormal)
        confidence = round(min(0.99, best_score) * 100, 1)

        result = {
            "timestamp": now,
            "node_states": {nid: s.state.value for nid, s in self.nodes.items()},
            "severity": severity.value,
            "section": best_edge,
            "confidence": confidence,
            "score": best_score,
            "evidence": self._build_evidence(best_edge, abnormal, best_breakdown),
        }

        self._update_incident(result, now)
        return result

    def _classify(self, score: float, abnormal: set[str]) -> IncidentSeverity:
        any_offline = any(self.nodes[n].state == NodeState.OFFLINE for n in abnormal)
        if score >= SEVERITY_THRESHOLDS["critical"] or (any_offline and score >= SEVERITY_THRESHOLDS["localized"]):
            return IncidentSeverity.CRITICAL_EVENT
        if score >= SEVERITY_THRESHOLDS["localized"]:
            return IncidentSeverity.LOCALIZED_EVENT
        if score >= SEVERITY_THRESHOLDS["warning"]:
            return IncidentSeverity.WARNING
        return IncidentSeverity.NORMAL

    def _build_evidence(self, edge, abnormal: set[str], breakdown: dict) -> list[str]:
        if not edge:
            return ["All nodes reporting normal electrical state.", "Neighbor communication is consistent."]

        i, j = edge
        lines: list[str] = []
        for nid in (i, j):
            status = self.nodes[nid]
            if status.state == NodeState.OFFLINE:
                lines.append(f"{nid} reported loss of feeder voltage / heartbeat.")
            elif status.state == NodeState.FAULT:
                lines.append(f"{nid} detected abnormal electrical state.")
            elif status.state == NodeState.WARNING:
                lines.append(f"{nid} detected a minor voltage deviation.")
            if status.ml_score is not None and status.ml_score > 0.5:
                lines.append(f"ML cross-check (Isolation Forest) also flags {nid} as anomalous.")

        for nid, status in self.nodes.items():
            if nid not in (i, j) and status.state == NodeState.NORMAL:
                lines.append(f"{nid} remains normal.")

        if breakdown.get("neighbor_agreement", 0) >= 0.8:
            lines.append("Neighbor communication remains consistent.")
        else:
            lines.append("Neighbor communication shows partial disagreement.")

        return lines

    def _update_incident(self, result: dict, now: float) -> None:
        severity = IncidentSeverity(result["severity"])
        is_incident = severity in (IncidentSeverity.LOCALIZED_EVENT, IncidentSeverity.CRITICAL_EVENT)

        if is_incident and result["section"]:
            if not self.active_incident or self.active_incident.section != result["section"]:
                self._incident_seq += 1
                self.active_incident = Incident(
                    incident_id=self._incident_seq,
                    opened_at=now,
                    section=result["section"],
                    severity=severity,
                    confidence=result["confidence"],
                    evidence=result["evidence"],
                )
                if self.storage:
                    self.storage.open_incident(self.active_incident)
            else:
                self.active_incident.confidence = result["confidence"]
                self.active_incident.evidence = result["evidence"]
                self.active_incident.severity = severity
                if self.storage:
                    self.storage.update_incident(self.active_incident)
        elif self.active_incident and not self.active_incident.closed_at:
            self.active_incident.closed_at = now
            if self.storage:
                self.storage.close_incident(self.active_incident)
            self.active_incident = None
