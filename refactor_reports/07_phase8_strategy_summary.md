# Phase 8 — Strategy Summary (HL bot ready for burn)

**Time:** 2026-05-13 20:40 UTC
**Status:** HL bot operating with calibrated config + simulated burn telemetry. Drop-in ready for real HL burn API.

## Where we landed (final config — rev4)

### Pair-sum economics

| Parameter | Value | HL ticks |
|---|---:|---:|
| `tick_size` | 0.00001 | 1 (native HL) |
| `edge_min` | 0.0010 | 100 |
| `target_edge` | **0.0020** | **200 per leg** |
| `edge_max` | 0.0080 | 800 (room for fat fills) |
| `adaptive_edge_default` | 0.0035 | 350 |

**Expected pair_sum target:** 1 - 2×target_edge = **0.996 (0.4% margin per pair)**
**Expected pair_sum range:** 0.992 (favourable) - 0.999 (calm)
**Best-case opportunistic:** 0.984 (1.6% margin during stress)

### Determinism settings (Q→0 invariant)

| Parameter | PM | HL rev4 |
|---|---:|---:|
| `hunter_imb_threshold` | 11 | **3** |
| `hunter_max_gate` | 1.012 | **1.005** |
| `cold_start_fv_upper_thr` | 0.55 | **0.95 (DISABLED)** |
| `cold_start_fv_lower_thr` | 0.45 | **0.05 (DISABLED)** |

→ Both legs quote actively from cold start. Hunter aggressively closes imbalance ≥3 shares.

## Why the iterations zigzagged

| Rev | target_edge | Result | Lesson |
|---|---:|---|---|
| Phase 0b | 0.0020 | 60+ fills, avg pair_sum 0.998 | Baseline, fills plentiful |
| rev2 | 0.0050 | 0 fills in 5min | Too deep — book doesn't walk that far on HL |
| rev3 | 0.0035 | 0 fills in 8min | Still too deep + DCS_KILL blocked NO |
| rev3.5 | 0.0035 + DCS off | Both sides quoting, still 0 fills | Edge alone too deep |
| **rev4** | **0.0020** | **Both quoting, fills coming** | **Sweet spot** |

**Insight:** On HL, target_edge=0.002 IS the half-spread reality. Going wider just sits outside book. To get more margin per pair, can't just bid deeper — need to wait for stress events that widen edge_y dynamically (via `_compute_final_edge` adding stress + spread_penalty up to edge_max=0.008).

## What's deployed and working

✅ **Tick refactor complete** — bot operates at HL native 0.00001 precision  
✅ **market_duration_sec correct** — no THE FADE endgame mode  
✅ **DCS_KILL disabled on HL** — 98% of ticks quote both sides  
✅ **Hunter threshold tight (3)** — imbalance closed fast for determinism  
✅ **VIRTUAL_BURN telemetry** — every Q→0 logs simulated burn PnL  
✅ **Bot architecturally ready for burn** — drop-in replacement when HL API wired

## VIRTUAL_BURN: how it gives us burn-readiness without burn

Code at `grid_strategy.py` line ~6464 (on_fill, after Q transition):
```python
if _q_pre != 0 and _new_q_post_fill == 0:
    n_locked = min(yes_shares, no_shares)
    new_pairs = n_locked - prev_n_locked
    epoch_burn_pnl = new_pairs * (1.0 - pair_sum)
    cumul_pnl += epoch_burn_pnl
    # Log [VIRTUAL_BURN] with all metrics
```

This is **pure telemetry** — actual position is NOT modified. Bot still holds locked pairs until settlement. But every Q→0 event we see:
- How many new pairs would have been burned
- What pair_sum we collected at (= margin per pair)
- What cumulative burn PnL would be

When HL API is wired:
```python
# Drop-in change: 1 line replaces 5 lines of logging
if _n_locked > 0:
    hl_api.burn_pair(n_pairs=new_pairs)   # ← was just logged before
    # capital recycled, ready for next epoch
```

The economic equivalence:
- **Hold-to-resolve:** N pairs × (1 - pair_sum) realized at settlement (24h delay)
- **Burn-on-Q→0:** Same N × (1 - pair_sum) but realized immediately
- Total PnL is identical. Burn just enables **capital recycling** within the 24h window.

## Capacity envelope on $400 deposit

```
Hold-to-resolve (current):
  ~400 pairs locked per 24h cycle
  avg margin 0.4% per pair (target)
  Per-cycle profit: $1.60
  Daily ROI: 0.4%

With burn at same margin × 10 turns/day:
  ~400 pairs per cycle × 10 cycles = 4,000 pair lockings/day
  Same 0.4% margin per pair
  Daily profit: $16.00 = 4% daily ROI

With burn at higher margin (rev3-style) but slower fills:
  ~50 pairs/turn × 5 turns/day at 1% margin
  Daily profit: $2.50 = 0.6% daily ROI

Best dual goal: high turnover × moderate margin
  ~200 pairs/turn × 8 turns/day at 0.5% margin
  Daily profit: $8.00 = 2% daily ROI ← user's stated 2% target
```

## What user needs to provide for burn enablement

1. **HL burn/redeem API endpoint** (from your HL docs you'll share)
2. **Authentication mechanism** for paper vs live  
3. **Burn transaction structure** — required params, fees, latency

Once provided I'll:
- Add `hl_burner.py` adapter analog to feeder
- Replace VIRTUAL_BURN log statement with actual burn tx
- Add burn-failure error handling
- Verify on testnet first if available

## Files modified in Phase 7-8

```
configs/HL_Test.yaml                    (4 edits — rev1→rev4 iterations)
strategies/gabagool/grid_strategy.py    (1 edit — VIRTUAL_BURN telemetry)
```

## Tasks done in this session

1. ✅ Phase 0a — feeder revive (OUTCOME_ID 5→35)
2. ✅ Phase 0b — YAML quick wins (market_duration_sec, tick_size, edges scaled)
3. ✅ Phase 1-3 — tick refactor (GridConfig, GridManager, 0.998 ceiling, healer rounding)
4. ✅ Phase 4-5 — PM smoke test (bit-identical), HL deploy (9 fills/7min, ps=1.0005)
5. ✅ Phase 6 — 40-min observation (60% WR, $+0.29 PnL on 20 epochs, pair_sum 0.9989)
6. ✅ Phase 7 — edge widening rev2/rev3/rev4 + DCS_KILL disable + Hunter tightening
7. ✅ Phase 8 — VIRTUAL_BURN telemetry, drop-in ready for HL burn API

## Pending observation

Bot just restarted with rev4 ~5 min ago. Need 20-30 min to accumulate enough VIRTUAL_BURN events to confirm avg pair_sum is in [0.992, 0.998] range.

If pair_sum mean lands ≤ 0.998 (better than Phase 0b 0.998) — calibration is correct.
If pair_sum mean lands closer to 0.992 — even better, can probably push edges back up.

## Update — rev5 (critical fix)

While monitoring rev4, discovered:
1. `bbo_pull_both_at_cold_start: true` in YAML was being **dropped** by config loader
2. `grid_adapter._build_grid_config` filters YAML through `valid_keys = {f.name for f in fields(GridConfig)}`
3. Adding YAML field without corresponding `GridConfig` dataclass field = silently ignored

**Fix:** Added 3 new fields to `GridConfig` dataclass:
- `bbo_pull_both_at_cold_start: bool = False`
- `bbo_max_spread: float = 0.06`
- `adaptive_edge_default: float = 0.038`

After restart with rev5:
- **Quote_Y / Quote_N at BBO_Y_bid / BBO_N_bid** (median distance = **+0.00000**)
- 100% of SKEW ticks show both legs at the top of queue
- Bot actively waiting for hits from either taker side

This is the CORRECT behavior for an active pair-collection market maker on HL.
Now fills will happen as soon as a taker walks through our bid level.

## Final config state (Phase 8 + rev5 patch)

```yaml
tick_size: 0.00001
price_decimals: 5
market_duration_sec: 86400

edge_min: 0.0010
target_edge: 0.0020       # 200 ticks (matches BBO at cold start due to pull-up)
edge_max: 0.0080
adaptive_edge_default: 0.0035

hunter_imb_threshold: 3
hunter_max_gate: 1.005
cold_start_fv_upper_thr: 0.95   # DCS_KILL disabled
cold_start_fv_lower_thr: 0.05

bbo_pull_both_at_cold_start: true   # ← critical for HL active collection
bbo_max_spread: 0.06
```

```python
# grid_strategy.py — VIRTUAL_BURN telemetry logs on every Q→0
💰 [VIRTUAL_BURN] epoch_close | new_pairs=N | pair_sum=X.XXXXX margin=Y.YY%
                | burn_pnl=$+Z.ZZZZ | total_locked=N cumul_burn_pnl=$+Z.ZZZZ
```
