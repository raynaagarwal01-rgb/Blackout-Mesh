# Firmware

Three sketches, pick the one matching your budget/hardware tier (see
`docs/HARDWARE.md` for the full cost breakdown):

| Sketch | Boards needed | Sends via |
|---|---|---|
| `single_board_simulator/` | 1x ESP32 | USB serial directly (no ESP-NOW) |
| `node/` + `gateway/` | 2x ESP32 | ESP-NOW -> gateway -> USB serial |

The recommended ₹1,000–1,500 build is the 2-board option: flash
`node/node.ino` onto one board and `gateway/gateway.ino` onto the
other. The gateway board is *also* a sensing node (`NODE_ID 2`) so two
boards give you two genuinely independent physical measurement points;
the backend fills in the remaining feeder positions (N3, N4) as
virtual nodes so the dashboard always shows a complete 4-node feeder.

If you only have one ESP32 to start with, flash
`single_board_simulator/single_board_simulator.ino` instead — it
emulates N1/N2/N3 on three potentiometers and lets three buttons
trigger the demo fault scenarios directly. Set
`HARDWARE_NODE_IDS = {"N1", "N2", "N3"}` in `blackout_mesh/config.py`
so only N4 is filled in virtually.

## Flashing (Arduino IDE)

1. **File > Preferences > Additional boards manager URLs**, add:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
2. **Tools > Board > Boards Manager**, install "esp32" (Espressif Systems).
3. Open the `.ino` file for your chosen sketch, select
   **Tools > Board > ESP32 Arduino > ESP32 Dev Module**, pick the
   correct **Port**, then **Upload**.
4. Open **Tools > Serial Monitor** at **115200 baud** to sanity-check
   the board is printing JSON (gateway / single-board sketches) or
   just booted cleanly (node sketch — it only sends over ESP-NOW, it
   won't print packets to serial).

## Wiring

See `docs/HARDWARE.md` for the pin table, wiring diagram, and full
bill of materials for all three budget tiers.

## Notes

- ESP-NOW uses the broadcast address (`FF:FF:FF:FF:FF:FF`) so you
  never need to look up or hardcode a peer's MAC address — any node
  board and the gateway board will find each other automatically as
  long as they're on the same Wi-Fi channel (default channel 0/current,
  fine for a table-top demo).
- `mesh_protocol.h` is duplicated (byte-for-byte identical) inside both
  `node/` and `gateway/` rather than shared from a common folder — the
  Arduino IDE only reliably compiles headers that live in the sketch's
  own folder. If you edit the packet format, edit **both** copies.
- All voltage/current values are **DC proxies from potentiometers**,
  not real AC mains measurements. Never wire this project to mains
  power — see the safety note in `docs/HARDWARE.md`.
- All fault/scenario buttons are **software-debounced** (30ms, see the
  `DebouncedButton` struct in each sketch) and sampled every `loop()`
  iteration independent of the ~250ms send cadence, so a press is
  never missed or delayed by mechanical contact bounce.
- On the Python side, `backend/run_gateway.py --source serial`
  automatically retries the serial connection if a board is unplugged
  or the port drops mid-demo, instead of crashing the gateway process
  (see `blackout_mesh/serial_source.py`).
