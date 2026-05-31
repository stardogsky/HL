# HL — Hyperliquid Outcome Markets Adapter

Data collection and trading adapter connecting the `grid_poly_mm` strategy to **Hyperliquid HIP-4 binary outcome markets**. The strategy core (`grid_strategy.py`) runs unchanged — differences are encapsulated in the feeder adapter.

## What it does

Hyperliquid HIP-4 introduces binary outcome markets structurally similar to Polymarket: two tokens (YES/NO) per outcome, settle at $1 on resolution. This project bridges HL's WebSocket API to the ZMQ interface expected by `grid_poly_mm`.

**Status: Paused** — HL mainnet currently offers only BTC daily (1d) outcomes. The strategy is native to 15-minute markets. Track resumes when HL adds 15min markets, or strategy is calibrated for daily regime.

**Paper run #1 result (outcome 3, 16 hours):** +$1.79 on $400 deposit. Strategy executes correctly on HL without re-calibration. See `Calibration_Plan.md` for calibration roadmap.

## Architecture

```
hl_collector/ (pm2)
    ↓ WebSocket subscription to HL outcome markets
    ↓ writes JSONL hourly to data/raw/<network>/<date>/
hl_feeder.py (pm2)
    ↓ tails JSONL, converts HL format → Polymarket-compatible
    ↓ publishes on ZMQ tcp://127.0.0.1:5575
grid_poly_mm/main.py (bot_HL_Test)
    ↓ subscribes to ZMQ:5575 (same as gateway:5555 for PM)
    ↓ grid_strategy.py runs venue-agnostic logic
    ↓ writes live_state_HL_Test.json
gabagool-dashboard
    ↓ picks up HL bot alongside PM bots automatically
```

PM gateway: `ZMQ:5555`. HL feeder: `ZMQ:5575`. Production isolated.

## Repository structure

```
HL/
├── hl_feeder.py               ← ZMQ adapter (converts HL → PM-compatible format)
├── hl_feeder_hype15m.py       ← HYPE 15m testnet variant
├── hl_collector/              ← WebSocket data collection daemon
│   ├── main.py                ← entry point (pm2)
│   ├── discovery.py           ← outcome discovery + lifecycle filter
│   ├── ws_client.py           ← WebSocket client with reconnect logic
│   ├── settlement.py          ← settlement phase capture
│   ├── writer.py              ← JSONL writer (hourly rotation)
│   └── config.yaml
├── doc/                       ← Synced HL gitbook (85+ pages)
│   └── Docs/                  ← trading, hypercore, HIP-4 specs
├── refactor_reports/          ← Phase-by-phase refactor history (12 phases)
├── code_map/                  ← Static code analysis outputs
├── data/                      ← Collected market data (JSONL)
│   └── raw/<network>/<date>/  ← l2Book, bbo, trades, activeAssetCtx, allMids
├── Auto_Discovery_Design.md   ← Phase-gated state machine design (Priority 2)
├── Calibration_Plan.md        ← Strategy calibration plan for HL (Priority 1)
├── 00_HL_START_HERE.md        ← Entry point for resuming HL work
├── Current_Deployment.md      ← VPS state snapshot at pause
└── Roadmap.md                 ← Task queue with estimates
```

## HL vs Polymarket differences

| Parameter | Polymarket | Hyperliquid |
|---|---|---|
| Tick size | 0.01 | 0.00001 |
| Block time | ~2s | ~70-100ms |
| Market period | 15 min | 1d (currently) |
| Spread (typical) | 1-2 cents | 0.38 cents |
| Order atomicity | eventual | atomic cancel-then-place intra-block |

## Data collected per outcome

- `l2Book` — orderbook snapshots
- `bbo` — best bid/offer changes
- `trades` — with public buyer/seller addresses (additional alpha vs PM)
- `activeAssetCtx` — outcome context
- `allMids` — mid prices (1s REST poll)
- `outcomeMeta` — outcome metadata (60s)
- Settlement phase capture: NORMAL → TIGHT (T-60s) → CRITICAL (T-10s) → POST

Archive: 100+ testnet HYPE 15m settlements + 4+ mainnet BTC 1d settlements.

## Key learnings

**Subscription lifecycle storm (2026-05-05):** subscribing to settled/expired outcome → HL silently closes connection. Self-amplifying via 30 new conn/min IP rate limit. Fix: lifecycle filter (`seconds_until_expiry > 0`) + GC unsubscribe on settlement. Reconnect rate: 37/min → 0.

**Testnet HYPE 15m is broken:** markPx degenerates to targetPrice (no liquidity). Settlement always YES. Usable only for infrastructure validation, not strategy validation.

**Settlement window adverse selection:** TOXIC fill observed at T-45min before expiry (mainnet outcome 3). Hunter NO at $0.110 → PS 0.83→1.15. Hypothesis: wall+canyon pattern in settlement window. See `doc/Research/2026-05-17_AS2008_binary_markets_deep_dive.md`.

## Resuming work

```bash
# Check VPS state
pm2 list | grep -E "hl_|bot_HL"

# Find current active outcome
TODAY=$(date -u +%Y-%m-%d)
tail -1 ~/HL/data/raw/mainnet/$TODAY/outcome_meta_*.jsonl 2>/dev/null | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); \
  print([(o['outcome'], o['description']) for o in d['outcomes'] \
  if o['description'].startswith('class:priceBinary')])"

# Patch feeder to current outcome (manual, until auto-discovery is implemented)
sed -i "s|^OUTCOME_ID = .*$|OUTCOME_ID = <NEW_ID>|" hl_feeder.py
pm2 restart hl_feeder bot_HL_Test
```

See `00_HL_START_HERE.md` for the complete return checklist, resume triggers, and priority queue.

## Calibration needed for daily markets

Current config (`HL_Test.yaml`) uses PM defaults (not calibrated for HL daily):
- `tick_size: 0.01` → should be `0.00001`
- `market_duration_sec: 900` → should be `86400`
- Edge thresholds tuned for 1-2c spread → need adjustment for 0.38c HL spread

See `Calibration_Plan.md` for the full 3-phase plan (estimate: 4-6h work + 24-48h validation).

## Outcome encoding (HIP-4)

Binary outcomes: YES = `#<10*outcome_id+0>`, NO = `#<10*outcome_id+1>`.  
Example: outcome #5 → YES token `#50`, NO token `#51`.

## Related

Strategy core: [grid_poly_mm](../grid_poly_mm) — runs unchanged on HL data via this adapter.
