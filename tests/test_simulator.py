from blackout_mesh.simulator import Simulator


def test_normal_scenario_yields_all_nodes():
    sim = Simulator(scenario="normal")
    readings = sim._tick_readings()
    assert {r.node_id for r in readings} == {"N1", "N2", "N3", "N4"}
    assert all(r.anomaly < 0.1 for r in readings)


def test_overload_scenario_flags_n3():
    sim = Simulator(scenario="overload")
    readings = {r.node_id: r for r in sim._tick_readings()}
    assert readings["N3"].anomaly > 0.5
    assert readings["N1"].anomaly < 0.1
    assert readings["N4"].anomaly < 0.1


def test_interruption_scenario_silences_n3():
    sim = Simulator(scenario="interruption")
    readings = {r.node_id: r for r in sim._tick_readings()}
    assert "N3" not in readings  # N3 goes silent -> backend infers OFFLINE
    assert readings["N2"].anomaly > 0.5
    assert readings["N1"].anomaly < 0.1
    assert readings["N4"].anomaly < 0.1


def test_connectivity_loss_scenario_only_n1_n2():
    sim = Simulator(scenario="connectivity_loss")
    node_ids = {r.node_id for r in sim._tick_readings()}
    assert node_ids == {"N1", "N2"}


def test_intermittent_scenario_toggles():
    sim = Simulator(scenario="intermittent")
    first = {r.node_id: r for r in sim._tick_readings()}
    second = {r.node_id: r for r in sim._tick_readings()}
    # Exactly one of the two ticks should show N2/N3 faulted, the other normal.
    assert (first["N2"].anomaly > 0.5) != (second["N2"].anomaly > 0.5)
