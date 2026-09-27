"""Feeder graph helpers used by the fault-localization algorithm.

The key idea (see docs/ALGORITHM.md): a fault section is more credible
when the set of abnormal/offline nodes forms a *contiguous* run of the
feeder touching the candidate edge, rather than scattered, unrelated
nodes.
"""

import networkx as nx

from .config import build_topology


class Topology:
    def __init__(self):
        self.graph = build_topology()

    def neighbors(self, node_id: str) -> list[str]:
        return list(self.graph.neighbors(node_id))

    def edges(self) -> list[tuple[str, str]]:
        return list(self.graph.edges())

    def contiguous_consistency(self, edge: tuple[str, str], abnormal_nodes: set[str]) -> float:
        """Score in [0, 1]: does `abnormal_nodes` form a contiguous section
        of the feeder that touches this edge?
        """
        i, j = edge
        if not abnormal_nodes or (i not in abnormal_nodes and j not in abnormal_nodes):
            return 0.0

        if len(abnormal_nodes) == 1:
            return 0.6  # a single abnormal node is plausible evidence, but weaker than a section

        sub = self.graph.subgraph(abnormal_nodes)
        if sub.number_of_nodes() == 0:
            return 0.0
        return 1.0 if nx.is_connected(sub) else 0.3
