# HL — Hyperliquid Outcome Markets

An attempt to run the same market making strategy on Hyperliquid binary outcome markets (HIP-4). The strategy from `grid_poly_mm` runs unchanged — the only difference is the data adapter.

Currently paused: Hyperliquid mainnet offers only one market (BTC daily), while the strategy is native to 15-minute markets. The infrastructure is ready and waiting for suitable markets to appear.

---

## What is here

**Collector** (`hl_collector/`) — pm2 daemon that subscribes to Hyperliquid WebSocket and writes JSONL files hourly. Handles settlements without reconnect storms (the solution is documented in `refactor_reports/`).

**Feeder** (`hl_feeder.py`) — reads JSONL, converts HL format to Polymarket-compatible format, publishes on ZMQ:5575. The `grid_poly_mm` bot connects to this instead of the standard gateway:5555.

```
hl_collector → data/raw/<network>/<date>/ → hl_feeder → ZMQ:5575 → grid_poly_mm bot
```

**Documentation** (`doc/`) — 85+ pages of synced Hyperliquid gitbook: HIP-4 specs, API reference, mark price formulas, contract parameters.

**Refactor archive** (`refactor_reports/`) — 12 phases from first launch to feeder freeze postmortem. Reads like a project journal.

---

## Result

One paper run: **+$1.79 over 16 hours** on a $400 deposit. The strategy executes correctly on HL without recalibration. Adverse selection observed in the settlement window (T-45min before expiry).

The main obstacle is not the code but the market: mainnet only offers BTC daily, which is not optimal for a strategy built around 24-hour horizons.

---

## If you want to continue

`00_HL_START_HERE.md` — entry point, full checklist for resuming the project.

`Calibration_Plan.md` — what needs to change in the strategy for daily markets (estimate: 4-6 hours of work).

`Auto_Discovery_Design.md` — ready design for an auto-discovery feeder that does not freeze on every settlement.

---

## Structure

```
hl_feeder.py              ← ZMQ adapter (HL → PM-compatible format)
hl_collector/             ← data collection daemon
doc/                      ← Hyperliquid documentation (gitbook sync)
refactor_reports/         ← 12-phase refactor history
data/raw/                 ← collected JSONL data
Auto_Discovery_Design.md  ← auto-discovery design (not implemented)
Calibration_Plan.md       ← calibration plan for HL
00_HL_START_HERE.md       ← entry point when returning to the project
```

---

Strategy core: [grid_poly_mm](https://github.com/stardogsky/grid_poly_mm)
