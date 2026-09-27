# Fault-localization algorithm

Implemented in `blackout_mesh/inference.py`. Deliberately rule-based
and deterministic (not a black-box model) so every incident the
dashboard reports comes with a plain-English "why."

## The core idea

Most simple monitoring only asks: *did this one sensor detect an
anomaly?* BLACKOUT MESH instead asks: *what combination of electrical
state **and** communication state across the whole mesh best explains
what every node is seeing?*

Concretely: **a node going silent is not just a communication
failure — it is itself evidence about where the fault is.** If N3
stops reporting entirely while N1, N2, and N4 all keep reporting
normal, that pattern points at the N2-N3 section far more precisely
than any single node's reading could.

## Per-edge scoring

For every edge `(i, j)` in the feeder topology graph (`N1-N2`,
`N2-N3`, `N3-N4` by default, see `blackout_mesh/config.py`). The graph
isn't limited to a straight line — `topology.py`/`inference.py` only
ever reason in terms of edges and neighbors, so a branching (tree
-shaped) feeder works too. Either edit `TOPOLOGY_EDGES`/`NODE_IDS` in
`config.py` to match your feeder's real shape, or pass
`FaultInferenceEngine(node_ids=..., topology_edges=...)` to use an
alternate topology without editing that file (see
`tests/test_branching_topology.py` for a worked example with a
2-way branch):

```text
Score(i,j) = w1 * anomaly_evidence(i,j)
           + w2 * state_discontinuity(i,j)
           + w3 * neighbor_agreement(i,j)
           + w4 * topology_consistency(i,j)
```

Default weights: `w1=0.35, w2=0.30, w3=0.20, w4=0.15` (tunable in
`config.ANOMALY_WEIGHTS` — these aren't claimed to be universally
"correct," just tuned against the four demo scenarios).

- **`anomaly_evidence`** — average of the two endpoints' anomaly
  scores (0-1, from each node's adaptive baseline z-score; an offline
  node counts as anomaly = 1.0).
- **`state_discontinuity`** — normalized voltage gap between the two
  endpoints. A real break in the feeder shows up as a sharp
  discontinuity across exactly one edge, not a gradual slope.
- **`neighbor_agreement`** — rewards the edge whose endpoints are
  abnormal *while the nodes just outside that edge stay normal* — i.e.
  the boundary of the affected section sits precisely on this edge,
  not smeared across the whole feeder.
- **`topology_consistency`** — using `networkx`, checks whether the
  full set of abnormal/offline nodes forms one *contiguous* run of the
  graph touching this edge (a real fault propagates along a
  connected section; scattered, unrelated anomalies shouldn't score
  well here).

The edge with the highest score is reported as the probable affected
section.

## Confidence and severity

**Confidence** is the winning score expressed as a percentage
(capped at 99%) — it is an *evidence margin*, not a calibrated
probability, and the dashboard/docs are careful to call it "inference
confidence" rather than implying a statistically calibrated
likelihood.

**Severity** (`NORMAL -> WARNING -> LOCALIZED_EVENT -> CRITICAL_EVENT`)
is derived from the same score plus whether any implicated node has
gone fully offline (`config.SEVERITY_THRESHOLDS`).

## Optional Layer-2 ML cross-check

`blackout_mesh/ml_layer.py` runs a small Isolation Forest (scikit-learn)
per node over its recent voltage/current samples purely as a
*supporting* signal — when it agrees a node looks anomalous, that's
added as an extra evidence line ("ML cross-check also flags N2..."). It
never overrides the rule-based score above. This matches the project's
"hardware performs sensing, software performs intelligence" design,
and answers the inevitable judge question "where's the AI?" without
sacrificing explainability. If scikit-learn isn't installed, this layer
simply stays silent — nothing else depends on it.

## Incident lifecycle

`FaultInferenceEngine` opens an `Incident` (persisted to SQLite via
`Storage`) the moment severity reaches `LOCALIZED_EVENT` or higher,
keeps it updated with the latest confidence/evidence while the same
section stays implicated, and closes it once the mesh returns to
`NORMAL`/`WARNING`. The dashboard's "Event log" reads this history
directly.
