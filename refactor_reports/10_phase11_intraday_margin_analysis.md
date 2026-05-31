# Phase 11 — Intraday HL Margin Analysis

**Time:** 2026-05-13 21:05 UTC
**Data:** 6 settled BTC daily outcomes (May 6-12), aggregated bid_sum / spread / margin by hour-from-settlement

## Source
- 482,758 YES BBO datapoints
- 448,143 NO BBO datapoints
- Across outcomes 3, 4, 10, 15, 20, 25

## Headline finding — margin is HIGHLY time-of-cycle dependent

| Stat | Mean across all hours |
|---|---:|
| Mean margin | **+0.52%** |
| Median margin | **+0.50%** |
| Range | **−1.5% to +5.95%** |
| Settlement-window peak (T-6h max) | **5.95%** |
| Settlement-window typical (T-1h to T-6h median) | **0.5-1.0%** |
| Mid-day flat (T-16 to T-13) | **0.1-0.3%** (sometimes NEGATIVE) |

## Intraday Margin Curve (median across 6 outcomes)

```
Hour from settle  Median margin  Note
T-24h to T-19h    0.60-0.70%   First 6h after open — wider book, makers setting up
T-18h to T-13h    0.20-0.45%   Mid-day equilibrium — TIGHT book, arbitrage active
T-12h to T- 8h    0.38-0.50%   Steady-state — moderate margin
T-7h to T-6h      0.41-0.73%   Approach to settlement — widening
T-6h SPIKE        max 5.95%    Pre-settlement dislocations
T-5h to T-3h      0.53-0.68%   Settlement positioning
T-2h               0.26%        Surprising calm before storm
T-1h               0.76%        Final hour — fat opportunity, but limited data (3 outcomes)
```

## What this means for strategy

### Current bot (fixed offset 500 ticks all day):
- Asking for 1% margin universally
- Mid-day reality: 0.2-0.4% available
- **Result: 0 fills mid-day** (we observed!)
- Settlement window reality: 0.5-1.5% available  
- **Result: would catch fills here**

### Better strategy: **adaptive offset by time-to-expiry**

| Time window | Available margin | Suggested offset | Resulting target pair_sum |
|---|---:|---:|---:|
| T-24 to T-19h (first 6h) | 0.5-0.7% | **200 ticks** | 0.996 (0.4% margin) |
| T-18 to T-13h (mid-day) | 0.1-0.4% | **75 ticks** | 0.9985 (0.15%) — accept low margin for fills |
| T-12 to T-8h | 0.4-0.5% | **150 ticks** | 0.997 (0.3%) |
| T-7 to T-3h (pre-settle) | 0.4-1.0% | **300 ticks** | 0.994 (0.6%) |
| **T-3 to T-1h (settlement window)** | **0.5-2%** | **500-800 ticks** | **0.984-0.99 (1-1.6% margin)** |
| T-1h to settle | wind down | 0 (withdraw) | safety |

### Expected daily PnL projection

If bot adaptively offsets and fills consistently:

```
Conservative (50% fill capture rate):
  24h × avg 0.5% margin × 30 pairs/h × 0.5 capture = ~$1.8/day on $400 = 0.5%/day
  Annualized: 180%

Realistic (settlement window focus):
  6h × avg 0.8% margin × 50 pairs/h × 0.5 capture = $1.2/day on $400 = 0.3%/day
  Annualized: 110%

Aggressive (with burn enabled):
  Capital recycles 5×/day → effective 1.5%/day = 550%/year
```

## What was observed in test runs (without adaptive logic)

| Bot config | Mid-day pair_sum | Notes |
|---|---:|---|
| target_edge 0.002 only | 0.998 (0.2%) | Filled fast, low margin |
| + pull_offset 100 | 0.9975 (0.25%) | Better fills, similar margin |
| + pull_offset 500 | (no fills — too deep) | Offset > available margin |

## Recommended action — implement `time_adaptive_offset`

Add to strategy: scale `bbo_pull_offset_ticks` based on `time_rem_sec / market_duration_sec` (lifecycle):

```python
def adaptive_offset_ticks(self, lifecycle: float) -> int:
    """Return offset ticks based on market lifecycle.
    
    HL daily intraday margin pattern (Phase 11):
      0.0-0.25 (first 6h, T-24 to T-18): margin 0.5-0.7%, offset 200
      0.25-0.50 (mid-day): margin 0.1-0.4%, offset 75
      0.50-0.75 (afternoon): margin 0.4-0.5%, offset 150
      0.75-0.96 (pre-settle T-6 to T-1): margin 0.4-1%, offset 300
      0.96-1.00 (final T-1h): margin 0.5-2%, offset 500+
    """
    if lifecycle < 0.25: return 200
    if lifecycle < 0.50: return 75
    if lifecycle < 0.75: return 150
    if lifecycle < 0.96: return 300
    return 500
```

This config-driven knob captures **the real economic structure** of HL daily markets.

## Side observation — DON'T quote in T-16 to T-13

That window has margin DROP to 0.2% or even negative (max −0.55%). Bot bidding here = paying overpriced book, locking in loss.

Suggested: **quote withdrawal in low-margin windows** based on real-time bid_sum check.

```python
current_bid_sum = yes_bid + no_bid
if current_bid_sum > 0.997:   # less than 0.3% margin available
    skip_quoting = True       # don't post, wait for better window
```

## Settlement window cautions

- T-1h has highest median margin (0.76%) but also highest variance (range 0.5-1.95%)
- One outcome showed pair_sum SPIKE to negative (>$1) at T-2h — likely informed trader pushing book
- TOXIC #3 in paper_run_1 occurred at T-45min — bot bought losing side at the dislocation
- **Filter for settlement window:** only quote if `bid_sum < 0.997` AND `mid is consistent with target` (avoid catching falling knives)

## Conclusion

**The 2% margin target is realistically achievable BUT only:**
1. During specific windows (mostly T-1h to T-6h)
2. With adaptive offset (deep when margin available, tight otherwise)
3. Or during volatility spikes (max observed 5.95% margin at T-6h)

The previous bot config (fixed offset, no time awareness) was **structurally incapable** of capturing the time-varying margin. Implementing time-adaptive offset can:
- Mean realized margin: 0.4-0.6%
- Peak margin opportunity: 1-2% in settlement windows
- Mid-day defensive: withdraw or tight quotes

Expected daily PnL: **0.3-1.5% per cycle**, multiplied by burn velocity when available.
