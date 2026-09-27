#!/usr/bin/env python3
"""BLACKOUT MESH live dashboard.

Run with: streamlit run dashboard/app.py

Normally reads from the same SQLite database the gateway service
(backend/run_gateway.py) writes to, so it can run as a separate
process — start the gateway first, then this.

For a one-process deployment (e.g. Streamlit Community Cloud, which
only runs this single script and can't also run a separate gateway
process), set BLACKOUT_MESH_STANDALONE_DEMO=true (as an environment
variable, or a Streamlit secret) to have this app run the built-in
scenario simulator in a background thread on its own, so the demo is
fully self-contained.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from blackout_mesh.config import DB_PATH, NODE_IDS, OFFLINE_TIMEOUT_S
from blackout_mesh.storage import Storage

st.set_page_config(page_title="BLACKOUT MESH", page_icon="⚡", layout="wide")

STATE_ICON = {"NORMAL": "🟢", "WARNING": "🟡", "FAULT": "🔴", "OFFLINE": "⚫"}
STATE_COLOR = {"NORMAL": "#16a34a", "WARNING": "#ca8a04", "FAULT": "#dc2626", "OFFLINE": "#6b7280"}

# Streamlit's auto-refreshing fragment API stabilized as `st.fragment` around
# 1.37-1.38; fall back to the experimental name on older installs.
_fragment = getattr(st, "fragment", None) or st.experimental_fragment


def _config_flag(name: str) -> bool:
    value = "false"
    try:
        value = st.secrets.get(name, value)  # Streamlit Cloud's Secrets manager
    except Exception:
        pass
    value = os.environ.get(name, value)
    return str(value).strip().lower() in ("1", "true", "yes")


STANDALONE_DEMO = _config_flag("BLACKOUT_MESH_STANDALONE_DEMO")


@st.cache_resource
def get_storage() -> Storage:
    return Storage(DB_PATH)


@st.cache_resource
def start_standalone_demo() -> bool:
    """Runs the scenario simulator in a background thread inside this
    same process, so the dashboard is a complete, self-contained demo
    with no separate gateway process required. Cached so it only
    starts once per running app, not on every Streamlit rerun."""
    if not STANDALONE_DEMO:
        return False

    from blackout_mesh.inference import FaultInferenceEngine
    from blackout_mesh.simulator import Simulator

    engine = FaultInferenceEngine(storage=get_storage())

    def _run() -> None:
        for reading in Simulator(scenario="auto").stream():
            engine.ingest(reading)

    threading.Thread(target=_run, daemon=True).start()
    return True


def derive_state(row: dict | None) -> str:
    if not row:
        return "OFFLINE"
    if time.time() - row["received_at"] > OFFLINE_TIMEOUT_S:
        return "OFFLINE"
    return row["state"] or "NORMAL"


@_fragment(run_every=1)
def render() -> None:
    storage = get_storage()
    latest = storage.latest_per_node()
    incident = storage.active_incident_row()

    states = {nid: derive_state(latest.get(nid)) for nid in NODE_IDS}

    # The feeder panel and the incident card come from two separate
    # queries (per-node latest readings vs. the incidents table). During
    # an automatic scenario transition (standalone demo mode) a node can
    # briefly still be mid-recovery in incident-tracking for a tick or
    # two after its own latest reading already reads NORMAL. Never let
    # the incident card contradict a feeder panel that's all green.
    if incident and all(state == "NORMAL" for state in states.values()):
        incident = None

    has_incident = incident is not None

    header_col, status_col = st.columns([3, 1])
    with header_col:
        st.title("⚡ BLACKOUT MESH")
        st.caption("Distribution intelligence — outage-resilient cooperative edge sensing")
        if STANDALONE_DEMO:
            st.caption("🎬 Standalone demo mode — cycling through simulated scenarios, no hardware attached.")
    with status_col:
        if has_incident:
            st.error("⚠ INCIDENT", icon="⚠️")
        else:
            st.success("● NETWORK OPERATIONAL", icon="✅")

    col_feeder, col_incident = st.columns([1, 2])

    with col_feeder:
        st.subheader("Feeder")
        for nid in NODE_IDS:
            state = states[nid]
            row = latest.get(nid)
            voltage_str = f"{row['voltage']:.2f} V" if row else "—"
            st.markdown(f"{STATE_ICON[state]} **{nid}** — {state} ({voltage_str})")

    with col_incident:
        st.subheader("Active incident")
        if incident:
            st.error(
                f"**{incident['severity']}** — probable section "
                f"**{incident['section_from']} — {incident['section_to']}**"
            )
            m1, m2 = st.columns(2)
            m1.metric("Confidence", f"{incident['confidence']}%")
            m2.metric("Detected", time.strftime("%H:%M:%S", time.localtime(incident["opened_at"])))
            st.markdown("**Evidence**")
            for line in json.loads(incident["evidence"]):
                st.markdown(f"- {line}")
        else:
            st.success("No active incident. All monitored sections normal.")

    st.subheader("Telemetry")
    readings = storage.recent_readings(limit=300)
    if readings:
        fig_voltage = go.Figure()
        fig_anomaly = go.Figure()
        for nid in NODE_IDS:
            series = [r for r in readings if r["node_id"] == nid]
            if not series:
                continue
            xs = [r["received_at"] for r in series]
            fig_voltage.add_trace(go.Scatter(x=xs, y=[r["voltage"] for r in series], mode="lines", name=nid))
            fig_anomaly.add_trace(go.Scatter(x=xs, y=[r["anomaly"] for r in series], mode="lines", name=nid))
        fig_voltage.update_layout(title="Voltage", height=280, margin=dict(l=10, r=10, t=40, b=10))
        fig_anomaly.update_layout(title="Anomaly score", height=280, margin=dict(l=10, r=10, t=40, b=10))

        chart_col1, chart_col2 = st.columns(2)
        chart_col1.plotly_chart(fig_voltage, use_container_width=True)
        chart_col2.plotly_chart(fig_anomaly, use_container_width=True)
    else:
        st.info("Waiting for telemetry — start the gateway service: `python backend/run_gateway.py`")

    st.subheader("Event log")
    incidents = storage.recent_incidents(limit=10)
    if incidents:
        st.dataframe(
            [
                {
                    "Time": time.strftime("%H:%M:%S", time.localtime(row["opened_at"])),
                    "Severity": row["severity"],
                    "Section": f"{row['section_from']}-{row['section_to']}",
                    "Confidence": f"{row['confidence']}%",
                    "Status": "OPEN" if not row["closed_at"] else "CLOSED",
                }
                for row in incidents
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No incidents recorded yet.")


start_standalone_demo()
render()
