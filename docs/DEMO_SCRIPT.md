# Demo script

Four scenarios, each showing the dashboard reasoning about a different
kind of evidence. Trigger them either physically (hold the matching
button on the hardware) or in software (`--scenario <name>` on the
simulator, or `--scenario auto` to cycle through all of them
unattended for rehearsal / screen recording).

Run these two commands first (in separate terminals):

```bash
python backend/run_gateway.py --source simulator --scenario auto
streamlit run dashboard/app.py
```

Or, once hardware is flashed and wired:

```bash
python backend/run_gateway.py --source serial --port /dev/ttyUSB0
```

## Demo 1 — Overload (`--scenario overload`)

Turn N3's potentiometer up (or hold the "overload" button on the
single-board build). N3 shows yellow; everything else stays green.

Dashboard shows: **WARNING**, probable location N3, reason "abnormal
electrical state." This is the simple case — a single node, no
localization needed yet.

## Demo 2 — Feeder interruption (`--scenario interruption`)

Hold the fault button on the N2 board while N3 goes silent (feeder
loss). N1 and N4 stay green.

Dashboard shows a full incident card:

```text
+--------------------------------+
|      INCIDENT DETECTED         |
+--------------------------------+
| Probable section                |
|        N2 --------- N3          |
| Confidence: ~90%+                |
| Evidence:                        |
|  - N2 detected abnormal state    |
|  - N3 lost feeder voltage        |
|  - N1 remains normal             |
|  - N4 remains normal             |
+--------------------------------+
```

This is the headline demo: two independent kinds of evidence
(electrical anomaly at N2, communication loss at N3) both point at the
same section.

## Demo 3 — Intermittent disturbance (`--scenario intermittent`)

Rapidly toggle the fault instead of holding it steady. The system sees
NORMAL / FAULT / NORMAL / FAULT in quick succession rather than a
clean binary "power = 0."

Dashboard shows: **INTERMITTENT DISTURBANCE**, location N2-N3, pattern
"repeated transient," action "inspect N2-N3." This demonstrates the
algorithm isn't just thresholding a single reading — it's tracking a
pattern over time.

## Demo 4 — Central connectivity disappears (`--scenario connectivity_loss`)

Disconnect the laptop's Wi-Fi / unplug its normal network connection.
The ESP32 boards keep talking to each other over ESP-NOW regardless
(it's direct device-to-device, no access point required), and local
fault inference keeps running.

This demonstrates the "offline-first" claim concretely — say out loud:
*"local detection doesn't need an internet/cloud path."* (Be precise
with judges: this shows node-to-node communication survives losing
the uplink, not that the whole system has no dependencies at all.)

## Rehearsal checklist (last hour before judging)

- [ ] Run all four scenarios back-to-back at least twice without
      touching the code.
- [ ] Confirm the dashboard is readable from a few feet away
      (font size, LED colors visible on camera/projector).
- [ ] Have a fallback: if a board misbehaves, `--source simulator
      --scenario auto` still tells the full story.
- [ ] Don't add features in the last two hours — only rehearse.
