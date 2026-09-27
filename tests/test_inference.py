from blackout_mesh.inference import FaultInferenceEngine
from blackout_mesh.models import IncidentSeverity
from blackout_mesh.simulator import Simulator


def run_scenario(scenario: str, ticks: int = 6):
    engine = FaultInferenceEngine()
    sim = Simulator(scenario=scenario)
    result = None
    for _ in range(ticks):
        for reading in sim._tick_readings():
            result = engine.ingest(reading)
    return engine, result


def test_normal_scenario_reports_no_incident():
    _, result = run_scenario("normal")
    assert result["severity"] == IncidentSeverity.NORMAL.value
    assert result["confidence"] < 10


def test_nodes_that_never_report_show_offline():
    """Regression test: a node with zero readings must show OFFLINE, not
    default to NORMAL (last_seen == 0.0 must not be treated as 'recent').
    """
    engine = FaultInferenceEngine()
    sim = Simulator(scenario="normal")
    readings = [r for r in sim._tick_readings() if r.node_id in ("N1", "N2")]
    result = None
    for reading in readings:
        result = engine.ingest(reading)

    assert result["node_states"]["N3"] == "OFFLINE"
    assert result["node_states"]["N4"] == "OFFLINE"


def test_interruption_scenario_localizes_to_n2_n3():
    _, result = run_scenario("interruption")
    assert result["section"] == ("N2", "N3")
    assert result["severity"] == IncidentSeverity.CRITICAL_EVENT.value
    assert result["confidence"] > 90
    evidence_text = " ".join(result["evidence"])
    assert "N2" in evidence_text
    assert "N3" in evidence_text


def test_overload_scenario_flags_warning_near_n3():
    _, result = run_scenario("overload")
    assert result["severity"] == IncidentSeverity.WARNING.value
    assert "N3" in result["section"]


def test_connectivity_loss_is_critical_but_local_nodes_stay_normal():
    _, result = run_scenario("connectivity_loss")
    assert result["node_states"]["N1"] == "NORMAL"
    assert result["node_states"]["N2"] == "NORMAL"
    assert result["node_states"]["N3"] == "OFFLINE"
    assert result["node_states"]["N4"] == "OFFLINE"
    assert result["severity"] == IncidentSeverity.CRITICAL_EVENT.value


def test_incident_opens_then_closes_when_mesh_recovers():
    engine = FaultInferenceEngine()
    fault_sim = Simulator(scenario="interruption")
    for _ in range(6):
        for reading in fault_sim._tick_readings():
            engine.ingest(reading)
    assert engine.active_incident is not None
    assert engine.active_incident.section == ("N2", "N3")

    normal_sim = Simulator(scenario="normal")
    for _ in range(10):
        for reading in normal_sim._tick_readings():
            engine.ingest(reading)
    assert engine.active_incident is None
