# Hardware

## Safety note (read first)

This prototype uses a **safe, low-voltage DC model feeder** (a
potentiometer-based analog stand-in for voltage/current), not a
connection to real AC mains. **Never** wire any part of this build to
230V/120V mains power. The physical rig demonstrates the sensing,
communication, and fault-inference *architecture* — a production
version would later swap in properly isolated grid-monitoring
instrumentation.

## Budget tiers

| Tier | Boards | What you get | Approx. cost |
|---|---|---|---|
| Minimum viable | 1x ESP32 | 3 potentiometers simulate N1-N3 on one board, buttons trigger scenarios directly | ₹500–800 |
| **Recommended** | 2x ESP32 | Two genuinely independent physical sensing points (node + gateway, ESP-NOW between them), N3/N4 filled in virtually | ₹1,000–1,500 |
| Stronger demo | 3x ESP32 | Three physical nodes + one virtual node | ₹2,000–2,500 |

### Bill of materials (recommended 2-board tier)

| Component | Qty | Approx. cost |
|---|---:|---:|
| ESP32 dev board | 2 | ₹800–900 |
| 10k potentiometer | 2 | ₹150–160 |
| Push button (momentary) | 2–4 | ₹20–40 |
| LEDs (green/yellow/red) | 6 | ₹20–40 |
| Resistors (220ohm for LEDs, 10k pull-ups if needed) | 1 pack | ₹30–50 |
| Breadboard | 1–2 | ₹100–150 |
| Jumper wires | 1 set | ₹80–100 |
| USB cables + laptop | existing | ₹0 |

**Total: roughly ₹1,200–1,500** (less if your lab already stocks
breadboards, resistors, and wires).

Deliberately **not** on this list: ZMPT101B / ACS712 (real AC
voltage/current sensors), OLEDs per node, LoRa modules, a Raspberry Pi,
or a cloud server — none of these are needed to demonstrate the
fault-localization concept, and skipping them keeps the 24-hour build
realistic.

## Pin table

### `firmware/node/node.ino` (NODE_ID 1) and `firmware/gateway/gateway.ino` (NODE_ID 2)

Identical wiring on both boards:

| Signal | GPIO | Notes |
|---|---|---|
| Voltage proxy (potentiometer wiper) | 34 | ADC1_CH6; pot's outer legs go to 3V3 and GND |
| Fault button | 25 | Momentary button to GND; uses internal pull-up (`INPUT_PULLUP`) |
| LED — green (NORMAL) | 26 | Through a 220ohm resistor to GND |
| LED — yellow (WARNING) | 27 | Through a 220ohm resistor to GND |
| LED — red (FAULT) | 14 | Through a 220ohm resistor to GND |

### `firmware/single_board_simulator/single_board_simulator.ino`

| Signal | GPIO | Notes |
|---|---|---|
| N1 voltage proxy | 34 | Potentiometer |
| N2 voltage proxy | 35 | Potentiometer |
| N3 voltage proxy | 32 | Potentiometer |
| Button — feeder interruption (N2/N3) | 25 | Hold to trigger Demo 2 |
| Button — overload (N3) | 26 | Hold to trigger Demo 1 |
| Button — intermittent (N2/N3) | 27 | Hold to trigger Demo 3 |

## Physical layout

```text
5V SUPPLY
    |
    R1
    |
   N1  <- real (node board) or potentiometer 1
    |
    R2
    |
   N2  <- real (gateway board) or potentiometer 2
    |
    R3
    |
   N3  <- virtual, or potentiometer 3
    |
    R4
    |
   N4  <- virtual
    |
   LOAD
```

The resistors (R1-R4) are just there to give the miniature feeder a
visible physical form for the demo table — they aren't part of the
sensing path.
