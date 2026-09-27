# Pitch & positioning

## The idea, in one sentence

> BLACKOUT MESH is a low-cost network of cooperating edge nodes that
> detects abnormal electrical conditions and uses local measurements,
> neighboring-node information, and communication status together to
> estimate which section of a distribution feeder is affected.

Instead of just saying "power failure detected," it tries to answer
*"where did the problem most likely occur?"* — and *"what evidence
made us reach that conclusion?"*

## 30-second elevator pitch

> "What if a power outage could tell you where it happened — not just
> that it happened? BLACKOUT MESH turns inexpensive ESP32 nodes into a
> cooperative mesh that detects electrical disturbances and combines
> both electrical evidence and communication-state evidence to
> localize the affected feeder section. Our prototype costs about
> ₹1,000-1,500, runs locally without any cloud dependency, and
> demonstrates the concept on a safe miniature feeder."

## Honest framing (say this, not the alternative)

Don't say: *"We built a real power-grid monitoring system."*

Say: *"We built a low-cost proof-of-concept of an outage-resilient,
cooperative sensing architecture for distribution networks. For safety
and hackathon cost constraints, our physical feeder is a low-voltage
DC model; the same inference architecture could later connect to
properly isolated grid-monitoring sensors."*

## What the prototype DOES

- Detects artificial electrical-state abnormalities.
- Estimates the affected section within a known feeder topology.
- Exchanges information node-to-node without needing an access point.
- Runs basic anomaly scoring close to the sensor (edge inference).
- Correlates multiple nodes' observations into one explainable
  incident.
- Visualizes the inferred event and its evidence live.
- Keeps working locally if the uplink to the internet disappears.

## What it does NOT claim

- Does not connect to 230V mains.
- Does not replace utility protection systems, circuit breakers, or
  relays.
- Does not guarantee real-world fault-location accuracy at grid scale.
- Does not handle every three-phase grid fault type.
- Does not provide certified power-quality measurements.
- Does not automatically restore power.
- Is not a safety protection device.

These belong to a future production/research phase, not this 24-hour
build.

## Novelty — be precise about this

IoT power monitoring, distributed sensors, and fault
detection/localization are **not new** — there's real published
research on distributed IoT fault-localization and IoT-based fault
indicators. Don't claim otherwise; a judge who's seen that literature
will (rightly) discount the whole pitch if you do.

What *is* a defensible, specific contribution:

> Existing distribution-grid research has extensively explored IoT
> sensing, power-quality monitoring, fault detection, and fault
> localization. BLACKOUT MESH focuses on a low-cost, outage-resilient
> architecture that combines local electrical-anomaly evidence with
> neighboring-node communication state and known feeder topology to
> infer the most probable affected section — demonstrated on
> commodity ESP32 hardware without any cloud dependency.

The one-sentence version of that: **"BLACKOUT MESH doesn't treat a
power disturbance and a communication failure as separate events; it
uses both as evidence for inferring the affected section of a
network."**

## Likely judge questions

**"Isn't fault localization already solved?"** — At utility scale,
yes, by systems like FLISR (fault detection, isolation and
restoration). Ours is positioned as a low-cost *diagnostic/sensing
layer* for places dense instrumentation is hard to justify (campuses,
microgrids, rural feeders, industrial zones), not a replacement for
utility protection equipment.

**"Why ESP32?"** — Cheap, has built-in ESP-NOW for direct
device-to-device communication with no access point needed, and is
familiar enough to prototype reliably in 24 hours.

**"Why not use SCADA?"** — We're not replacing SCADA; BLACKOUT MESH is
a complementary sensing layer for locations where dense
instrumentation is difficult or expensive to deploy.

**"Where is your AI?"** — Hardware performs sensing; software performs
the intelligence: an explainable, weighted scoring algorithm
(`docs/ALGORITHM.md`) is the core, with an optional Isolation Forest
layer as a supporting cross-check — because an explainable "here's
exactly why" beats an unexplainable "the model said so" in front of a
judge.

**"Does it work on 230V?"** — Not in this prototype; it's a safe
low-voltage DC model demonstrating the architecture, by design (see
the "what it does NOT claim" section above).

**"How do you know where the fault is?"** — Walk them through Demo 2
in `docs/DEMO_SCRIPT.md`: two independent kinds of evidence
(electrical anomaly + communication loss) converging on the same
feeder section.

## Why judges tend to respond to this

Four things are immediately legible without reading any code:

```text
VISIBLE HARDWARE + LIVE NETWORK + VISIBLE FAULT + INSTANT LOCALIZATION
```

The hardware is cheap. The intelligence is the value. That's the
story to tell.
