"""The algorithm isn't limited to a straight-line feeder: topology.py and
inference.py only ever reason in terms of graph edges/neighbors, so any
tree-shaped topology works. This proves it end-to-end on a branching
feeder where N2 splits into two downstream sections (N3 and N4).
"""

from blackout_mesh.inference import FaultInferenceEngine
from blackout_mesh.models import IncidentSeverity, NodeReading

BRANCHING_EDGES = [("N1", "N2"), ("N2", "N3"), ("N2", "N4")]
BRANCHING_NODES = ["N1", "N2", "N3", "N4"]


def make_engine():
    return FaultInferenceEngine(node_ids=BRANCHING_NODES, topology_edges=BRANCHING_EDGES)


def reading(node_id, seq, voltage, anomaly):
    return NodeReading(
        node_id=node_id, seq=seq, timestamp_ms=0,
        voltage=voltage, current=0.4, anomaly=anomaly,
    )


def test_topology_reflects_the_branch():
    engine = make_engine()
    assert set(engine.topology.edges()) == {("N1", "N2"), ("N2", "N3"), ("N2", "N4")}
    assert set(engine.topology.neighbors("N2")) == {"N1", "N3", "N4"}


def test_fault_on_one_branch_does_not_blame_the_other():
    engine = make_engine()
    result = None
    for i in range(6):
        result = engine.ingest(reading("N1", i, 3.3, 0.02))
        result = engine.ingest(reading("N2", i, 1.6, 0.9))  # branch point itself faulted
        # N3 stays silent (never ingested) -> OFFLINE; N4 stays healthy.
        result = engine.ingest(reading("N4", i, 3.3, 0.02))

    assert result["node_states"]["N3"] == "OFFLINE"
    assert result["node_states"]["N4"] == "NORMAL"
    assert result["section"] == ("N2", "N3")
    assert result["severity"] == IncidentSeverity.CRITICAL_EVENT.value
    # The healthy branch should never be blamed.
    assert result["section"] != ("N2", "N4")
