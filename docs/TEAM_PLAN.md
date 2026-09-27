# 24-hour build plan & team roles

## Suggested role split (3-4 people)

- **Electronics** — breadboard wiring, potentiometers/buttons/LEDs,
  power, physical feeder layout (see `docs/HARDWARE.md`).
- **Firmware** — ESP-NOW node/gateway protocol, baseline + anomaly
  scoring on-device (`firmware/`).
- **Backend/algorithm** — Python ingestion, fault-localization
  algorithm, storage (`blackout_mesh/`, `backend/`).
- **Dashboard** — Streamlit + Plotly UI, live incident visualization
  (`dashboard/`).

With 3 people, merge "electronics" into "firmware" (same person can
wire the board they're flashing) and split backend/dashboard across
the other two.

Everyone: start against `python backend/run_gateway.py --source
simulator --scenario auto` on day one — the dashboard/algorithm team
doesn't need to wait on working hardware, and the electronics/firmware
team can validate their JSON output against the same schema the
simulator produces.

## Hour-by-hour

| Hours | Focus |
|---|---|
| 0-2 | Finalize architecture & topology; lay out the physical feeder board. |
| 2-4 | Get ESP32 ADC reading a potentiometer reliably. |
| 4-7 | Implement ESP-NOW: node sends `{id, value, timestamp, heartbeat}`, gateway receives it. |
| 7-10 | Implement per-node baseline + anomaly scoring + event detection. |
| 10-13 | Build the Python gateway/ingestion service. |
| 13-16 | Build the Streamlit dashboard: feeder visualization + incident panel. |
| 16-18 | Implement fault-section inference (the scoring algorithm). |
| 18-20 | Wire up the physical fault trigger(s); test all four demo scenarios. |
| 20-22 | Polish the dashboard: animations, event log, confidence, evidence, timestamps. |
| 22-24 | **Do not add features.** Rehearse the demo script repeatedly. |

## Project objectives (for your submission form)

1. Detect abnormal electrical conditions at multiple points along a
   feeder.
2. Localize the probable affected section, not just "power is out."
3. Treat node-to-node communication loss as evidence, not just a
   failure mode.
4. Keep local fault inference working without cloud/internet
   dependency.
5. Make every incident explainable — show the evidence, not just a
   verdict.
6. Build the whole thing for ₹1,000-1,500 in 24 hours.
7. Be explicit and honest about what the prototype does and does not
   claim (see `docs/PITCH.md`).
