# Phase 9 — Binary Market Margin Problem + rev6 Fix

**Time:** 2026-05-13 20:42–20:47 UTC

## Critical finding from first VIRTUAL_BURN event

After the cold-start BBO pull-up activated and bot filled both sides:

```
20:42:16 💰 [VIRTUAL_BURN] new_pairs=15 pair_sum=1.00000 margin=0.000%
        burn_pnl=$+0.0000 | Q:-15→0 | Y_avg=0.13000 N_avg=0.87000
```

**Pair sum exactly $1.000 — zero margin per pair.**

### Why

On binary outcome markets the relationship `YES_bid + NO_bid ≈ $1.00` is enforced by arbitrage. Filling AT both BBO bids means paying exactly the floor of pair_sum. The maker's "half-spread" that would normally be profit is offset by the half-spread cost on the other side.

| Side | BBO_bid | Quote (pull-to-BBO) | Edge captured per leg |
|---|---:|---:|---:|
| YES | 0.130 | 0.130 | 0¢ |
| NO  | 0.870 | 0.870 | 0¢ |
| **Pair** | **1.000** | **1.000** | **0¢** |

Math invariant: on Y+N=1 markets, if Y_bid + N_bid = 1.0, then buying both at bid → break-even.

## Solution — rev6 `bbo_pull_offset_ticks`

Pull quotes to `BBO_bid - N*tick_size` instead of exactly `BBO_bid`. Each tick of offset adds 2 ticks of pair_sum margin (one per leg).

### New config knob

```yaml
bbo_pull_offset_ticks: 100   # pulls 100 HL ticks below BBO bid each side
```

Math:
- BBO_Y_bid 0.130, BBO_N_bid 0.870 (pair = 1.000)
- After offset 100 ticks: Quote_Y 0.129, Quote_N 0.869 (pair = 0.998)
- **Pair margin = 0.002 = 0.2% per pair** ✓

Trade-off:
- 0 ticks: max fill rate, 0% margin
- 100 ticks: medium fill rate, 0.2% margin
- 250 ticks: slower fills, 0.5% margin
- 500 ticks: rare fat fills, 1.0% margin

### Code change

`grid_strategy.py:_apply_bbo_clamp` + Option C final anchor:
```python
_pull_offset = getattr(self.config, 'bbo_pull_offset_ticks', 0) * self.tick_size

elif _yes_is_closing and l0_y < yes_bid:
    _target_y = yes_bid - _pull_offset
    if _target_y > self.tick_size:
        l0_y = round(_target_y, self.price_decimals)
```

`GridConfig` dataclass: added `bbo_pull_offset_ticks: int = 0` (PM default unchanged).

## Why bot was filling so well

In Phase 9 first minutes (with offset=0):
- 6 fills in 2 minutes (3 fills/min)
- Both sides fill at BBO bid → bot perfectly at top of queue
- Hunter activates at Q=19 (above threshold 3) → fills NO 20@0.870 to close
- Q→0 epoch closures within 30 seconds of opening

This **proves the maker mechanism works on HL**. We just need positive margin, which rev6 adds via the offset.

## Bot state post-rev6 restart

Bot restarted with `bbo_pull_offset_ticks: 100`. Expected behavior:
- Quote_Y at BBO_Y_bid - 100 ticks = 0.001 below bid
- Quote_N at BBO_N_bid - 100 ticks = 0.001 below bid
- Pair_sum target = 0.998 (0.2% margin per pair)
- Fill rate: estimated 50-70% of pre-rev6 (slower because deeper)

Monitoring for first VIRTUAL_BURN with margin > 0% to confirm rev6 works.

## Next iterations

Once rev6 produces > 0% margin events:
- `offset=100` → confirm pair_sum ≈ 0.998 (0.2% margin)
- If fills plentiful (≥1/min), push to `offset=250` (0.5% margin)
- If still plentiful, push to `offset=500` (1.0% margin)
- Goal: maximum offset that maintains ≥0.5 fills/min average

## Strategic summary

**With cold-start BBO pull-up + offset, the bot is now a tunable HL pair-lock maker:**

| Config | Profile |
|---|---|
| `offset=0` | Ultra-aggressive, 0% margin (queue fight only) |
| `offset=100` | Conservative active maker, 0.2% margin |
| `offset=250` | Balanced, 0.5% margin |
| `offset=500` | Patient maker, 1.0% margin |
| `offset=1000` | Hunter mode, 2.0% margin (only fat opportunities) |

**Burn enabled later:** Same offset config — burn just changes capital velocity. Profit per pair is locked by the offset choice.

For deterministic positive EV: any `offset > 0` guarantees positive math expectation. The choice is **how much fill rate vs margin per pair**.

## Files in this phase

- `strategies/gabagool/grid_strategy.py` — Added `bbo_pull_offset_ticks` reading + arithmetic in 2 places (BBO clamp + final anchor)
- `strategies/gabagool/grid_strategy.py:GridConfig` — Added `bbo_pull_offset_ticks: int = 0`
- `configs/HL_Test.yaml` — `bbo_pull_offset_ticks: 100`
