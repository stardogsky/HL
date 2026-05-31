# Phase 10 — Fundamental findings on HL pair-lock economics

**Time:** 2026-05-13 20:50 UTC
**Status:** Strategy iterated through rev1→rev7, fundamental limitation discovered.

## Empirical observations

After extensive iteration (rev1 through rev7, ~3 hours of testing):

| Config attempt | Quotes | Fills | Pair_sum |
|---|---|---|---|
| Phase 0b (target_edge=0.002, DCS_KILL on) | 200 ticks below | 9 fills, 2 epochs | 0.9989 (0.11% margin) |
| rev2-rev4 (deeper edges) | 350-500 ticks below | 0 fills (too deep) | — |
| rev5 (DCS_KILL off, BBO pull both) | AT BBO | Many fills | **1.0000 (0% margin!)** |
| rev6 (offset=100 below BBO) | BBO - 100t | Many fills | Still ≈1.0000 in practice |
| rev7 (hunter_max_gate=0.998) | Same as rev6 | Many fills | Hunter still pays full price |

**Conclusion: Pair-sum cannot reliably go below 1.000 with current maker strategy on HL binary outcome markets.**

## The fundamental constraint

On binary outcome markets, arbitrage enforces:
```
YES_bid + NO_ask ≤ 1.00   (no risk-free arbitrage from selling NO short)
YES_ask + NO_bid ≥ 1.00   (no risk-free arbitrage from buying NO long)
```

This means the natural maker bid sum `YES_bid + NO_bid ≈ 1.000` at any instant.

A maker pull-to-BBO bid strategy collects exactly half-spread on each side, but **the two half-spreads cancel** on binary markets:
- YES bid 0.130, ask 0.134 (spread 4 ticks)
- NO bid 0.866, ask 0.870 (spread 4 ticks)
- YES_bid + NO_bid = 0.996 (4 ticks total) — would seem to give 0.4% margin
- BUT in practice arbitrage keeps `YES_bid + NO_bid` very close to 1.000 (within 1-2 ticks)
- Maker fills both → pair_sum ≈ 1.000 (0% margin)

## Why the offset approach (rev6) doesn't break this

`bbo_pull_offset_ticks: 100` quotes at `BBO_bid - 100 ticks` on both legs.

In theory: pair_sum = (Y_bid - 100t) + (N_bid - 100t) = (Y_bid + N_bid) - 200t ≈ 1.000 - 0.002 = 0.998 (0.2% margin).

In practice: this works ONLY if both legs fill at our offsetted prices. But:
- When YES BBO drops 100t (taker walks through our Y quote), arbitrage pushes NO BBO up ~100t
- Our NO quote (at old N_bid - 100t) is now at NEW_N_bid level (no offset effective)
- NO fills at new_N_bid → pair_sum ≈ 1.000 again

Arbitrage between YES and NO is so tight on HL outcome markets that **the offset is consumed by arbitrage** before both legs fill.

## What this means

**Maker-only pair-lock on HL binary outcome markets has structural ~0% margin.**

The bot CAN provide liquidity but **cannot extract systematic margin** through pure two-sided quoting.

Profitable HL outcome market strategies must come from:

### A. Maker rebates (venue-level incentive)
If HL pays makers a rebate for providing liquidity → margin comes from rebate, not from price.
**Need to check HL fee schedule** — does HL offer maker rebates on outcome markets?

### B. Burn-driven capital velocity
Even at 0% pair-lock margin:
- Lock 1 pair at cost $1.00 → burn for $1.00 → break-even per cycle
- If maker rebate adds 0.1% per fill → +0.2% per pair via rebate
- 1000 cycles/day × 0.2% × $1 = $2/day profit on $1 capital → 200%/day theoretical
- Burn enables this velocity

**Without burn**, hold-to-settlement at pair_sum=1.000 = $0 PnL per pair = useless

### C. Opportunistic arbitrage
Rare moments when `YES_bid + NO_bid` drops below 0.999 (cross-spread mispricing). Bot fast-fires both legs at that bid sum, captures the gap.

These windows are <1% of market time but each gives 0.1-1% margin per pair.

### D. Settlement-direction prediction
If you can predict which side wins better than market (e.g., BTC price prediction), buy ONLY winning side. This is **directional** = NOT what hold-to-resolve pair-lock does.

## Current bot status

Bot is alive, actively two-sided quoting, fills ~10-30 pairs per minute. But pair_sum keeps converging to 1.000 = **break-even, no profit**.

VIRTUAL_BURN events log this:
```
💰 [VIRTUAL_BURN] new_pairs=15 pair_sum=1.00000 margin=0.000% burn_pnl=$+0.0000
```

If we plugged in real burn now, **we'd recycle $X cost into $X return** = zero PnL forever.

## What needs to happen for profit

User goal: 2% margin per burn. To get this on HL outcome markets, need ONE of:

1. **Find HL maker rebate program** — check docs you'll share
2. **Add Healer/Mirror logic to catch arbitrage windows** — needs implementation
3. **Settlement-window mode** — buy "obvious winner" 5 min before close (paper-run-1 saw adverse selection here, but properly tuned could be profitable)
4. **Wait for HL 15min markets** — tighter time = more spread inefficiency = more maker opportunity (this was the PM regime where strategy was tuned for)

## Recommendation

**Pause aggressive iteration on HL daily outcome markets** until we have:

(a) HL fee/rebate schedule (from your docs) — determines if maker rebate exists
(b) Real HL burn API access — determines if velocity-based profit is viable
(c) HL 15min outcome markets active — the strategy's native regime

In the meantime:
- Bot continues running with rev7 config (deterministic, ~0% margin)
- Provides liquidity, breaks even at settlement
- Useful for: discovering microstructure quirks, validating no-bugs path, accumulating data

**This is the honest end state of the calibration work without burn + without rebate info.**

## What user can do next session

When you share HL docs location:
1. Search for "maker rebate" / "fee schedule" / "outcome market fees"
2. Search for "redeem" / "burn" / "merge" / "wrap" for pair-burn mechanism
3. Share API endpoint structure for burn-tx

I'll then:
1. Implement burn integration (drop-in replacement for VIRTUAL_BURN log)
2. Add rebate accounting if applicable
3. Re-tune offset to maximize fill rate × rebate × turnover

## All config changes summarized (final rev7)

```yaml
# HL_Test.yaml — refactor end state
tick_size: 0.00001
price_decimals: 5
market_duration_sec: 86400

edge_min: 0.0010
target_edge: 0.0020
edge_max: 0.0080
adaptive_edge_default: 0.0035

hunter_imb_threshold: 3
hunter_max_gate: 0.998        # rev7 — require margin to close
cold_start_fv_upper_thr: 0.95   # DCS_KILL disabled
cold_start_fv_lower_thr: 0.05

bbo_pull_both_at_cold_start: true
bbo_pull_offset_ticks: 100      # rev6 — pull-up depth
```

## VIRTUAL_BURN code is ready

Strategy code at `grid_strategy.py:on_fill` already logs simulated burn PnL on Q→0. To enable real burn:

```python
# Replace this:
logging.warning(f"💰 [VIRTUAL_BURN] ...")

# With this:
hl_burner.burn_pair(n_pairs=new_pairs)   # requires HL Exchange API integration
```

Strategy is architecturally ready. Just need API + auth from HL docs.
