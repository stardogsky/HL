# Phase 0b — YAML Quick Wins

**Time:** 2026-05-13 18:05 UTC
**Duration:** 15 min

## Changes to `configs/HL_Test.yaml`

### Block 1 — Identity + market timing
| Param | Was (PM) | Now (HL) | Reason |
|---|---|---|---|
| `variant` | `fifteen` | `daily` | Documentation, HL gives daily not 15min |
| **`market_duration_sec`** | **900** | **86400** | **CRITICAL** — was activating THE FADE endgame mode every tick |
| `tick_size` (NEW) | — | `0.00001` | HL native granularity (1000× thinner than PM) |
| `price_decimals` (NEW) | — | `5` | Used by `round(x, self.price_decimals)` after Phase 2 refactor |
| `min_lot` (NEW) | — | `5` | TBD per outcomeMeta |
| `min_notional` (NEW) | — | `1.00` | TBD |

### Block 3 — Edge/spread (scaled by 10×, not full 1000× — preserve effective economic meaning)
| Param | Was (PM) | Now (HL) | HL-tick equivalent |
|---|---|---|---|
| `edge_min` | 0.010 | 0.0010 | 100 ticks |
| `edge_max` | 0.035 | 0.0035 | 350 ticks |
| `edge_vol_sensitivity` | 0.012 | 0.001 | scaled |
| `nudge_size` | 0.02 | 0.00002 | 2 ticks |
| `target_edge` (NEW) | — | 0.0020 | 200 ticks |
| `adaptive_edge_default` (NEW) | — | 0.0038 | 380 ticks (Q7) |

### Section "Контур безопасности" — MAQ + GC
| Param | Was (PM) | Now (HL) | Notes |
|---|---|---|---|
| `maq_trend_value` | 0.004 | 0.0004 | scaled |
| `garbage_dist_base` | 0.05 | 0.005 | 500 ticks GC perimeter (Q13) |
| `MAQ_BASE` | 0.003 | 0.0003 | 30 ticks |
| `cvd_skew_max_cents` (NEW) | — | 0.0015 | 150 ticks |
| `max_adaptive_edge` (NEW) | — | 0.012 | 1200 ticks (was 0.12 PM via dataclass) |
| `alpha_ramp_min` | 0.005 | 0.0010 | 100 ticks |
| `recovery_discount_cents` (NEW) | — | 0.00050 | half-tick on HL |

### NOT changed (ABSOLUTE values — probability/USD space)
- `empty_book_premium: 0.05` — premium over FV (5pp probability)
- `maq_trend_threshold: 0.30` — FV space [0,1]
- `toxic_max_premium: 0.08` — premium over FV (8pp)
- `gamma_maq_min_discount: 0.50` — fraction
- `maq_asym_hedge_threshold: 11` — shares

## Observable changes (10s after restart)

### Before
```
🧠 [THETA_CORE] Progress: 0.05 | Time_Left: 43s
📉 [THE FADE] Эндшпиль! T-Factor: 0.18 | Limit Y:41 / N:62
```

### After
```
🧮 [SKEW] T:42847s | Edge:0.001 | Quote_Y:0.144_x10 | BBO_Y:0.149-0.161 | Pos:0/0 | InvPS:0.000
🔬 [PRICING_TRACE] FV:0.1552 | edge_y:0.0027 edge_n:0.0023 | l0_y:0.1514 l0_n:0.8431
```

✅ THE FADE gone — `T:42847s` correctly reads ~12h to expiry
✅ Edge:0.001 (tiny, HL-correct)
✅ PRICING_TRACE shows `edge_y:0.0027 edge_n:0.0023` (sub-1pp edges)
✅ Bot states `Intent: NORMAL` (was `Intent: WARMUP` stuck)
✅ DCS_KILL still active correctly (FV<0.45 → blocks NO opening)

### Remaining issue (Phase 1-3 will fix)
```
Quote_Y:0.144  at  BBO_Y:0.149-0.161
```
Bot quotes 0.144 (5 ticks below bid 0.149). Reason: `round(x, 2)` in code coarsifies prices to 2-decimal precision. After Phase 2 refactor (`round(x, self.price_decimals=5)`), bot will quote 0.14900 or 0.14899 — proper HL precision.

## Verdict

✅ Strategy operates in correct regime. Will not get filled efficiently yet due to coarse rounding, but no longer panics into endgame.

**Next:** Phase 1 — config plumbing for `self.tick_size`.
