from blackout_mesh.topology import Topology


def test_default_edges():
    topo = Topology()
    assert topo.edges() == [("N1", "N2"), ("N2", "N3"), ("N3", "N4")]


def test_neighbors():
    topo = Topology()
    assert set(topo.neighbors("N2")) == {"N1", "N3"}


def test_no_abnormal_nodes_scores_zero():
    topo = Topology()
    assert topo.contiguous_consistency(("N1", "N2"), set()) == 0.0


def test_abnormal_nodes_not_touching_edge_scores_zero():
    topo = Topology()
    assert topo.contiguous_consistency(("N1", "N2"), {"N4"}) == 0.0


def test_single_abnormal_node_touching_edge():
    topo = Topology()
    assert topo.contiguous_consistency(("N2", "N3"), {"N3"}) == 0.6


def test_contiguous_abnormal_section_scores_highest():
    topo = Topology()
    assert topo.contiguous_consistency(("N2", "N3"), {"N2", "N3"}) == 1.0


def test_scattered_abnormal_nodes_score_lower():
    topo = Topology()
    # N1 and N4 are not adjacent -> the induced subgraph is disconnected.
    assert topo.contiguous_consistency(("N1", "N2"), {"N1", "N4"}) == 0.3
