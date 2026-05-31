# Phase 12 — Feeder Freeze Postmortem + Auto-Discovery Deploy

**Time:** 2026-05-16 23:55 UTC
**Status:** ✅ RESOLVED — auto-discovery + watchdog deployed, all tests pass.

## Incident summary

| | |
|---|---|
| **Detected** | 2026-05-16 23:40 UTC (user noticed bot inactive after refactor work) |
| **Started** | 2026-05-14 06:00:23 UTC (settlement of outcome 35) |
| **Duration** | 2 days 17 hours 40 min of total feeder silence |
| **Last bot fill** | 2026-05-13 21:03:36 UTC (8h after Phase 0a restart) |
| **Bot state during incident** | DEAD_ZONE — bridge saw market_info with new slug but no orderbook |
| **Real-money impact** | None (paper mode) |
| **Repeated occurrence** | 3rd time this exact failure mode (outcome 2→3, 3→5, 5→35, 35→?) |

## Root cause atomization

**The atomic bug** (`hl_feeder.py:36-42`, pre-fix):
```python
OUTCOME_ID = 35                              # module-level constant
YES_TOKEN_ID = str(OUTCOME_ID * 10)          # frozen at import time
NO_TOKEN_ID = str(OUTCOME_ID * 10 + 1)
YES_FILE_PREFIX = f"book_h{YES_TOKEN_ID}_"   # "book_h350_"
NO_FILE_PREFIX = f"book_h{NO_TOKEN_ID}_"
# discover_files() searches only these fixed prefixes forever
```

**The chain:**
1. Outcome 35 settled 2026-05-14 06:00:23 UTC. HL closed the WebSocket
   subscription per `hl_collector` lifecycle filter.
2. Collector rotated cleanly — wrote files for new outcomes 40, 45, 50 as they
   were issued (`book_h400_*`, `book_h450_*`, `book_h500_*`).
3. Feeder kept calling `discover_files()` for `book_h350_*` only — files no
   longer exist → benign warning every 60s, no error, no crash, no restart.
4. `market_info_loop` continued — reads `outcomes[0]` from meta which is
   *whatever HL says is current* (now outcome 50). So bot received market_info
   with `slug=hl-btc-1d-78985-20260517-0600` (correct) but token_ids `"350"`/
   `"351"` (settled-outcome 35's tokens). No orderbook for those tokens →
   bridge stuck at `Updates:156967` forever.
5. pm2 saw the feeder as healthy (no crash). Bot saw the feeder as connected.
   No human noticed for 2.5 days.

## Why prior solutions didn't stop this

| Prior attempt | Why it failed |
|---|---|
| Manual `sed OUTCOME_ID=...` after each settlement (5/5, 5/7, 5/13) | Requires human at the keyboard at 06:00 UTC. Worked 3 times, missed the 4th. |
| `Auto_Discovery_Design.md` (2026-05-07) | Designed but tagged **Priority 2** and deferred indefinitely. |
| `hl_feeder_hype15m.py` (2026-05-07, 672 lines) | Full state-machine reference implementation written — but hardcoded for testnet HYPE 15m, never adapted to mainnet BTC daily, never deployed. |
| `Current_Deployment.md` warning | Documented the recovery procedure as "5 min if action taken at 06:01 UTC" — accepted recurring operational debt instead of fixing. |

The recurring failure mode is exactly what `00_HL_START_HERE.md` (line 99) called out: *"WILL FREEZE on next mainnet settlement... no auto-discovery — needs manual patch each day."* The bot was running 9 days against a feeder known to silently fail every 24h.

## Solution — defense in depth (3 layers)

### Layer 1: Phase-gated state machine (root fix)

Replaced `hl_feeder.py` with auto-discovery. Adapted from
`hl_feeder_hype15m.py` reference implementation. Mainnet/BTC/1d filter, port
5575 preserved for bot compatibility.

Phases: `STEADY → PRE_SETTLE (T-60s) → TRANSITION (T+0..T+180s) →
POST_SETTLE → STEADY`. On settlement: re-read `outcome_meta`, pick earliest
non-expired outcome matching filter (`class:priceBinary | underlying:BTC |
period:1d`), re-attach all tailers atomically, broadcast new slug. Bot's
bridge picks up market_switch event and resets strategy.

### Layer 2: Internal watchdog

In `STEADY` with a presumed-active outcome, track `last_book_msg_ts`. If no
orderbook message received for `STALE_BOOK_ALARM_SEC` (120s):
- Log `CRITICAL` line (greppable, future-you-friendly).
- Increment `watchdog_alarms` stat.
- Call `_force_rediscover()` which re-reads meta and switches if a new
  outcome appears, or re-attaches tailers if same outcome (hour rollover edge
  case).

Throttled to one forced rediscover per 30s to prevent thrashing.

### Layer 3: External health file + monitor

Feeder writes `~/HL/data/feeder_health.json` every 30s containing:
- phase, current outcome ID, slug, seconds to expiry
- last_book_msg_ts and seconds_since_last_book
- stats including switches, watchdog_alarms, forced_rediscoveries

`~/HL/monitor_feeder.sh` (chmod +x) checks the health file and exits:
- `0` OK — slug + status line
- `1` STALE — health file older than 5min (feeder dead, pm2 should restart)
- `2` WEDGED — heartbeat fresh but no book data for 5min in STEADY
- `3` NO_OUTCOME — feeder running but no active outcome found
- `4` NO_FILE — health file missing

Designed for cron / pm2 ecosystem / desktop notification hooks.

## Verification

### Test 1: dry-run discovery on live mainnet data
```
$ python3 ~/HL/hl_feeder.py --dry-run
ACTIVE_OUTCOME id=50
  slug=hl-btc-1d-78985-20260517-0600
  strike=$78,985
  expires_in=22006s
  yes_token=500  no_token=501
```

### Test 2: 5 state-machine scenarios (`test_feeder_rotation.py`)

1. Normal rotation `STEADY → PRE_SETTLE → TRANSITION → POST_SETTLE → STEADY` ✅
2. TRANSITION timeout fallback to STEADY ✅
3. Watchdog fires on stale book ✅
4. Watchdog recovery via re-discovery ✅
5. Cold start (no outcome → eventual discovery) ✅

All pass.

### Test 3: live deploy

```
23:55:29  🚀 [FEEDER] Network: mainnet | ZMQ: tcp://*:5575
23:55:29  🚀 [FEEDER] Watchdog: alarm if STEADY + no book 120s
23:55:29  📂 [book_yes]  book_h500_23.jsonl
23:55:29  📂 [book_no]   book_h501_23.jsonl
23:55:29  🎯 SWITCH: None → 50 | strike=$78,985 | expires_in=21870s
23:55:31  → STEADY: outcome 50 confirmed (book data flowing)
23:55:59  💓 OB Y/N: 55/55 (age:0s)  | switches:1 | watchdog_alarms:0
23:56:29  💓 OB Y/N: 110/110 (age:0s)
23:57:29  💓 OB Y/N: 222/222 (age:0s)
23:58:29  💓 OB Y/N: 332/332 (age:1s)
```

Bot bridge confirmed alive:
- Before fix: `GATEWAY SYNC ... Updates: 156967` (frozen)
- After fix:  `Updates: 150 → 188 → 224 → 262 → 300` (incrementing)

Strategy producing real ticks again with FV=0.044, BBO_Y:0.042-0.045 /
BBO_N:0.955-0.958 (BTC below target → NO heavily favored, expected).

## Next true settlement test

**2026-05-17 06:00 UTC** — outcome 50 expires, should automatically rotate to
outcome 55 (or whatever HL deploys next). Expected log sequence:

```
05:59:00  → PRE_SETTLE: outcome 50 expires in 60s
06:00:00  → TRANSITION: outcome 50 settled, searching for new
06:00:0X  🎯 SWITCH: 50 → 55 (hl-btc-1d-...)
06:00:0X  → POST_SETTLE: switched to outcome 55
06:00:1X  → STEADY: outcome 55 confirmed (book data flowing)
```

No human intervention required. If anything goes wrong, watchdog should fire
within 120s and at minimum log CRITICAL.

## Files changed / added

```
hl_feeder.py                                  REWRITTEN (522 → 624 lines)
hl_feeder.py.bak.20260516_pre_autodisc        ← prior version preserved
monitor_feeder.sh                             NEW — Layer 3 external check
test_feeder_rotation.py                       NEW — 5 unit-test scenarios
data/feeder_health.json                       NEW — runtime health snapshot
```

Untouched (intentionally):
- `hl_feeder_hype15m.py` — reference implementation, kept for future testnet/15m work
- `hl_collector/` — already handled lifecycle correctly per 2026-05-05 fix
- `~/gabagool/` — bot/strategy code, calibration is separate concern (Phase 7-10)

## Lessons (for future-self)

1. **"Will fail next settlement" warnings in docs aren't acceptable mitigation
   — they're scheduled outages.** If a known failure mode requires human
   action to recover, it WILL eventually fail unattended.

2. **Reference implementations gather dust until adapted.** The 672-line
   `hl_feeder_hype15m.py` had everything needed. Cost to port: ~30 min. Cost
   of not porting for 9 days: 2.5 days of lost paper data + user confidence
   hit. The actual blocker was "Priority 2 = never."

3. **`Warning` is not `Error` is not `Critical` is not `Alarm`.** The frozen
   feeder logged `⚠️ no file for book_yes` every 60s for 60 hours. pm2 only
   restarts on non-zero exit. Watchdog needed to be inside the feeder OR
   external — `Warning` text in logs alone isn't a control.

4. **Health files beat log scraping.** A small JSON written atomically every
   30s is faster to inspect (`cat | jq`) and easier to monitor (cron / shell)
   than parsing log lines. Adopt this pattern for future long-running daemons.

5. **The user thought dynamic-edge from Phase 11 was deployed** — it was
   only planned. Need clearer state in `00_HL_START_HERE.md` separating
   *designed / implemented / deployed*.
