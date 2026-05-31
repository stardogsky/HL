# Phase 7 — Widen edges + Virtual Burn telemetry

**Time:** 2026-05-13 20:15 UTC
**Trigger:** User goal — target 2% margin per pair, deterministic, positive EV. Burn mechanism known to exist on HL but not yet wired — operate as if burn was enabled.

## Strategy

**Two layers:**

1. **Calibrate strategy NOW** as if burn was available — wider edges target 1-2% margin per pair instead of current 0.11%.
2. **Add `VIRTUAL_BURN` telemetry** that logs simulated burn PnL on every Q→0 transition. Real position unchanged (still holds to settlement), but metrics show what burn-enabled PnL would have been. Drop-in replacement when HL burn API is wired.

## Changes to `HL_Test.yaml`

### Edges 3-5× wider
| Param | Was (Phase 0b) | Now | HL ticks | Note |
|---|---:|---:|---:|---|
| `edge_min` | 0.0010 | **0.0030** | 300 | 3× |
| `target_edge` | 0.0020 | **0.0050** | 500 | 2.5× |
| `edge_max` | 0.0035 | **0.0100** | 1000 | 2.85× |
| `edge_vol_sensitivity` | 0.001 | 0.003 | — | proportional |
| `adaptive_edge_default` | 0.0038 | **0.0080** | 800 | 2.1× |

**Per-pair target margin:** `2 × target_edge = 0.010 = 1% per pair` (1000 ticks of pair_sum margin below $1.00).

### Hunter — close imbalance fast (deterministic invariant)
| Param | Was | Now |
|---|---:|---:|
| `hunter_imb_threshold` | 11 shares | **3 shares** |
| `hunter_max_gate` | 1.012 | **1.005** |
| `hunter_escalation_shares` | 10.0 | **5.0** |

**Rationale:** Each unmatched share = directional bet = not deterministic. With tighter Hunter, Q stays near 0 → all profit comes from pair locks (math invariant $1.00 per pair at settlement, regardless of which side wins).

## Code change: VIRTUAL_BURN telemetry

Added to `on_fill` in `grid_strategy.py` after Q transition detection:

```python
if _q_pre != 0 and _new_q_post_fill == 0:
    _n_locked = min(yes_shares, no_shares)
    if _n_locked > 0:
        _pair_sum = yes_avg + no_avg
        _new_pairs = _n_locked - self._virtual_burn_last_n_locked
        _epoch_burn_pnl = _new_pairs * (1.0 - _pair_sum)
        _cumul_pnl = self._virtual_burn_cumul_pnl + _epoch_burn_pnl
        # log [VIRTUAL_BURN] event with pair_sum, margin, pnl
```

Logged as `💰 [VIRTUAL_BURN]` warning every Q→0 transition. Real position NOT modified — bot still holds to settlement for guaranteed payout.

**When HL burn API is wired:** swap log statement for actual burn transaction. Strategy already operates at burn-target margin.

## Expected behavior

### Before widening
- Quote_Y at -0.003 below BBO bid (300 ticks)
- Fills frequent (60+ in 40 min)
- Avg pair_sum 0.9989 (0.11% margin per pair)
- PnL projection: ~1% / 24h cycle

### After widening
- Quote_Y at -0.008 below BBO bid (800 ticks)
- Fills less frequent (estimate: 15-30 per hour vs 60)
- Target pair_sum: 0.99 (1% margin) — observable in VIRTUAL_BURN log
- PnL projection: ~1-2% / 24h cycle on $400 deposit

### Risk
- Edges too wide → 0 fills, idle bot. Mitigation: edge_max=0.010 caps the widening on volatile markets.
- Hunter at threshold=3 may over-eagerly close → erodes margin. Trade-off accepted for determinism.

## What VIRTUAL_BURN will show us

Sample expected output (when bot reaches Q→0):
```
💰 [VIRTUAL_BURN] epoch_close | new_pairs=15 | pair_sum=0.99205 margin=0.795%
                | burn_pnl=$+0.1193 | total_locked=405 cumul_burn_pnl=$+0.4523 
                | Q:8→0 | Y_avg=0.13150 N_avg=0.86055
```

From `cumul_burn_pnl` we can:
- Project hourly/daily burn-PnL
- Decide if pair margin is sustainable or needs further tuning
- Compare to actual hold-to-settlement PnL (will be `n_pairs * (1.0 - avg_pair_sum)` at settlement)

The two should be **identical** in mathematical expectation — burn just changes WHEN we collect, not HOW MUCH.

## Observations window
10 min after restart — accumulate at least 5-10 Q→0 events to estimate margin distribution.

## Next decision points (after observation)

| Scenario | Action |
|---|---|
| pair_sum mean ≤ 0.99 + ≥ 10 fills | ✅ Push to 0.98 target (edge × 2 more) |
| pair_sum mean ≤ 0.99 but < 5 fills | ⚠️ Keep edge, lower threshold for fill rate |
| pair_sum > 0.99 (didn't tighten) | 🔄 Investigate Why — likely MAQ filter or smart_gc |
| 0 fills at all | ❌ Revert edge to 0.003/0.006 |

## Update (revision 3)

Rev2 (target_edge=0.005) led to 0 fills in 5 min — HL spread is only ~400 ticks (0.004), so asking 500 ticks per leg meant bidding outside the half-spread → no natural maker fills.

**Rev3 changes:**
- `target_edge: 0.0035` (350 ticks per leg ≈ half-spread)
- `edge_max: 0.0100` (allows fat opportunistic fills up to 1% per leg)
- `cold_start_fv_upper_thr: 0.95` / `lower_thr: 0.05` — **disabled DCS_KILL on HL**

The DCS_KILL filter was PM-tuned for 15-min markets where directional cold start = trend chasing. On HL 24h markets with potentially extreme FV (0.13 / 0.87), DCS_KILL was blocking 50% of bot's natural flow (the "expensive side" stayed unquoted). Result: bot only quoted YES, never opened NO, never closed pairs.

After rev3:
- Both sides quote actively (verified in SKEW logs — Quote_N now size 10 instead of 0)
- Both bids ~5-6 HL ticks below their respective BBOs
- Pair target if both filled: 0.141 + 0.848 = **0.989 (1.1% margin)** — perfectly in target range

## Economic projection (with rev3 + simulated burn)

If pair_sum mean lands at 0.99 (1% margin per pair):
- **Per 24h cycle on $400 deposit, hold-to-resolve:**
  - ~400 pairs locked × $0.01 profit = +$4 / 24h = **+1.0% daily**
  - Annualized: ~365% (theoretical; real-world friction reduces)
- **With burn turnover (when wired):**
  - Same per-pair margin but capital recycles N times per day
  - N=10: ~10% daily potential
  - N=30: ~30% daily potential (likely capacity-limited on HL)

The VIRTUAL_BURN telemetry will show exactly what the burn-PnL would have been every Q→0 event, so we can:
1. Validate calibration before plumbing actual burn action
2. Compare to actual hold-to-settlement PnL (they should match in expectation)
3. Tune further if needed (push target_edge from 0.0035 → 0.005 if fills are still plentiful)
