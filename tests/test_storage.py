from blackout_mesh.models import Incident, IncidentSeverity, NodeReading, NodeState
from blackout_mesh.storage import Storage


def make_reading(node_id="N1", voltage=3.3, anomaly=0.02):
    return NodeReading(
        node_id=node_id, seq=1, timestamp_ms=0,
        voltage=voltage, current=0.4, anomaly=anomaly,
    )


def test_insert_and_read_back_reading(tmp_path):
    storage = Storage(str(tmp_path / "test.db"))
    storage.insert_reading(make_reading(), 0.02, NodeState.NORMAL)

    latest = storage.latest_per_node()
    assert "N1" in latest
    assert latest["N1"]["voltage"] == 3.3
    assert latest["N1"]["state"] == "NORMAL"


def test_incident_lifecycle_round_trip(tmp_path):
    storage = Storage(str(tmp_path / "test.db"))
    incident = Incident(
        incident_id=1, opened_at=100.0, section=("N2", "N3"),
        severity=IncidentSeverity.CRITICAL_EVENT, confidence=98.0,
        evidence=["N2 detected abnormal electrical state."],
    )
    storage.open_incident(incident)

    active = storage.active_incident_row()
    assert active is not None
    assert active["section_from"] == "N2"
    assert active["section_to"] == "N3"
    assert active["confidence"] == 98.0

    incident.closed_at = 110.0
    storage.close_incident(incident)
    assert storage.active_incident_row() is None

    history = storage.recent_incidents()
    assert len(history) == 1
    assert history[0]["closed_at"] == 110.0
