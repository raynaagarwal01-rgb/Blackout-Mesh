"""Central configuration: feeder topology, weights, thresholds, I/O defaults.

Edit this file to match your physical build (which nodes are real ESP32
boards vs. software-emulated, how many nodes your feeder has, serial
port, etc.) without touching the algorithm code.
"""

import networkx as nx

# --- Feeder topology -------------------------------------------------
# A simple linear feeder: SOURCE -> N1 -> N2 -> N3 -> N4 -> LOADS
#
# This does not have to be a straight line: the algorithm (topology.py,
# inference.py) works against a networkx graph and only ever reasons in
# terms of edges/neighbors, so any tree-shaped feeder works too, e.g. a
# branching layout where N2 splits into two downstream sections:
#   TOPOLOGY_EDGES = [("N1", "N2"), ("N2", "N3"), ("N2", "N4")]
# Change NODE_IDS/TOPOLOGY_EDGES below to match your actual feeder, or
# pass `topology_edges=` to FaultInferenceEngine(...) to use a different
# topology without editing this file (e.g. from a script or test).
NODE_IDS = ["N1", "N2", "N3", "N4"]
TOPOLOGY_EDGES = [("N1", "N2"), ("N2", "N3"), ("N3", "N4")]


def build_topology(edges=None) -> nx.Graph:
    """Build the feeder graph from `edges` (default: TOPOLOGY_EDGES).

    Nodes are derived from the edges themselves, so a branching/tree
    topology just needs the right edge list here.
    """
    graph = nx.Graph()
    graph.add_edges_from(edges if edges is not None else TOPOLOGY_EDGES)
    return graph


# --- Hardware vs. virtual nodes ---------------------------------------
# Nodes listed here are expected to report over serial (real ESP32
# boards). Any NODE_IDS not in this set are filled in continuously as
# steady "NORMAL" virtual nodes by blackout_mesh.virtual_nodes, so the
# dashboard always shows a complete feeder even with fewer boards.
#
# Recommended ₹1,000-1,500 build: 2 physical ESP32 boards (N1, N2),
# N3/N4 virtual. Swap to {"N1", "N2", "N3"} if you flash the
# single-board simulator firmware (see firmware/single_board_simulator).
HARDWARE_NODE_IDS = {"N1", "N2"}

# --- Timing -------------------------------------------------------------
OFFLINE_TIMEOUT_S = 2.5       # no packet within this window => node OFFLINE
BASELINE_WARMUP_S = 5.0       # fast baseline adaptation right after boot
BASELINE_EMA_ALPHA = 0.02     # slow baseline adaptation afterwards

# --- Fault-localization algorithm weights (Score(i,j), see docs/ALGORITHM.md)
ANOMALY_WEIGHTS = {
    "w1_anomaly": 0.35,
    "w2_discontinuity": 0.30,
    "w3_neighbor_agreement": 0.20,
    "w4_topology_consistency": 0.15,
}

SEVERITY_THRESHOLDS = {
    "warning": 0.35,
    "localized": 0.65,
    "critical": 0.85,
}

# --- Serial gateway -------------------------------------------------
SERIAL_DEFAULT_PORT = "/dev/ttyUSB0"
SERIAL_DEFAULT_BAUD = 115200

# --- Storage -------------------------------------------------------
DB_PATH = "blackout_mesh.db"
