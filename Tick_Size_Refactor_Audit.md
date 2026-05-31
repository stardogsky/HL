---
tags:
  - hyperliquid
  - refactor
  - audit
  - tick_size
  - in_progress
  - work_in_progress
  - execution_map
status: >-
  READY_FOR_REFACTOR — 11/11 passes done, 8/16 questions resolved, out-of-scope
  items documented
last_updated: '2026-05-08T02:00:00.000Z'
parent: HFT-Bot/Hyperliquid/Calibration_Plan.md
purpose: >
  Audit + executable refactor map для config-driven tick_size.

  Цель — стратегия применима к Polymarket (tick=0.01) И Hyperliquid (tick=0.001
  или меньше).

  Позиция: механика рынков та же (binary outcomes Y/N, Y+N=1, FV [0,1] space,
  pair-sum invariants).

  Меняется платформа (tick_size + SDK), не стратегия.
related:
  - HFT-Bot/Hyperliquid/Calibration_Plan.md
  - HFT-Bot/strategy_map.md
---

# 🔬 Tick Size Refactor — Multi-Venue Adaptation Map

> **При возврате — иди в [REFACTOR EXECUTION MAP](#refactor-execution-map--live-draft).**

---

# EXECUTIVE SUMMARY

## Status: READY_FOR_REFACTOR_EXECUTION ✅

**11 of 11 read passes done.** **8 of 16 questions fully resolved.** **~155 places identified** with file:line precision.

## Position statement (читай первым) ⭐

**Mechanic markets identical between PM and HL:**
- Binary outcomes (YES/NO conditional tokens, Y+N=1)
- 15-minute settlement (HL launched outcome markets, awaiting 15-min market availability)
- FV space [0, 1] = probability
- Pair-sum invariants (`profit_gate_ps_max=0.985`, `hunter_max_gate=1.03`, etc.)
- Healer mirror logic (`derived_no = 1.0 - yes`)
- DCS_KILL FV poles
- All strategy decision FSM (Hunter/Healer/Recovery)

**Что меняется при HL deployment:**
1. `tick_size` (0.01 → 0.001 or smaller)
2. SDK API surface (Polymarket CLOB → Hyperliquid Info/Exchange)
3. Identifier scheme (condition_id/token_id → HL outcome IDs)
4. Per-venue YAML calibration values (edge params, garbage_dist, etc.)
5. Magic constants tied to PM tick=0.01 (Q15 `0.35` floor)

**Что НЕ меняется:**
- Strategy decision logic
- Risk management (Triage, Knife protection)
- Pricing FSM (Hunter / Healer / Toxic Recovery / Mirror)
- Pair-sum economic invariants
- GLFT reservation pricing (simple_strategy)

**Tick refactor этого документа** покрывает item #1 и #5 above. Items #2-4 — **separate work** (см. секцию [OUT-OF-SCOPE](#-out-of-scope--что-не-покрыто-tick-refactor-map) в конце документа).

---

## Что добавляется в YAML

```yaml
# Control_Baseline.yaml (PM):
tick_size: 0.01
min_lot: 5
min_notional: 1.00

# HL_Test.yaml (HL):
tick_size: 0.001
min_lot: 5                       # ← TBD per HL outcomeMeta
min_notional: 1.00               # ← TBD
recovery_discount_cents: 0.0005  # half-tick at HL (vs 0.005 at PM)
```

## Три типа изменений

### Тип A — Mechanical replacements (low risk, ~30 places)

`TICK_SIZE` (constant) → `self.tick_size` (instance attr).

### Тип B — Decimal precision (medium risk, ~9 places)

`round(x, 2)` → `round(x, self.price_decimals)`.

**Insight:** end-of-pipeline в `_apply_maq_filter` (L3291-3292) уже proper tick-aware. Промежуточные `round(x, 2)` — inconsistency которую финал чинит. Меняем для bit-correctness.

### Тип C — Per-place decisions (high risk, ~30 places)

Hardcoded constants — каждое отдельное **бизнес-решение**:

**Tick-relative (РЕЗОЛВЛЕНЫ):**
- `0.998` ceiling (Q2 ✅) → `1.0 - 2*self.tick_size`
- All `N * TICK_SIZE` arithmetic — mechanical replace

**Absolute (РЕЗОЛВЛЕНЫ):**
- Profit margins (`MAQ_BASE`, `mirror_min_improvement`, `_healer_start - 0.02`)
- Loss tolerances (`knife_protection_cents=0.15`)
- Pair-sum thresholds (`0.985`, `0.990`, `0.995`, `1.005`, `1.03`, `1.05`)
- FV space, BTC USD, share counts, time

**Pending:**
- Q1 (0.03 token floor) — Likely absolute
- Q4 (MIN_NOTIONAL config) — Architectural, separate refactor
- Q11 (0.005 half-tick) — Per-venue YAML override
- Q12 (0.001 sub-tick) — Likely absolute small
- Q14 (`fv - 0.02` healer start) — Likely absolute (2 occurrences)
- Q15 (`0.35` magic floor) — Tick-calibrated, refactor needed
- Q16 (`0.15` gravity penalty cap) — Per-venue YAML или tick-rel

## Что НЕ меняется

| Категория | Примеры | Почему |
|---|---|---|
| **Profit margins** | `MAQ_BASE=0.06`, `maq_trend_value=0.025`, `empty_book_premium=0.10`, `mirror_min_improvement=0.04`, `_healer_start=fv-0.02` | Absolute money targets |
| **Loss tolerances** | `knife_protection_cents=0.15`, `unreal_loss<0.025`, `toxic_exit_fv_threshold=0.04` | Absolute risk floors |
| **Pair-sum thresholds** | `profit_gate_ps_max=0.985`, `0.990`, `0.995`, `hunter_locked_ps_guard=1.005`, `hunter_max_gate=1.03`, `veto_panic_gate=1.05` | Probability arithmetic |
| **Conservative caps** | `0.95` non-hunter price_cap | Absolute confidence zone |
| **FV thresholds** | DCS_KILL `0.55/0.45`, pole `0.15/0.85` | FV space [0,1] |
| **BTC-related** | `btc_vel_*`, `oracle_drift=0.004`, `dist_to_strike<150.0` | BTC USD space |
| **Share counts** | `MIN_LOT=5`, `hunter_imb_threshold`, `time_heal_q_min=15`, `effective_scale*1.5/3.0` | Discrete shares |
| **Time** | `time_heal_*=30s`, `45s`, `120s` panic | Seconds |
| **Display rounding** | `round(... * 100, 2)` | Percentage UI |
| **Risk floors** | `< 0.03` token kill | Settlement-near-zero |

## Detection strategy

```python
def _validate_tick_alignment(self, price, side):
    if price <= 0:
        return
    quantized = round(price / self.tick_size) * self.tick_size
    if abs(price - quantized) > self.tick_size * 0.01:
        logger.error(f"[TICK_VALIDATE] {side} price {price} NOT aligned to tick {self.tick_size}.")
```

Add at end of `_apply_maq_filter` (L3291-3292 area).

---

# REFACTOR EXECUTION MAP — LIVE DRAFT

> **STATUS:** Pass 1-7 done (~100 findings, 7 verified actual code).

## Pre-flight checklist

```bash
# Backup
cp ~/gabagool/strategies/gabagool/grid_strategy.py \
   ~/gabagool/strategies/gabagool/grid_strategy.py.bak.pre_tick_refactor
cp ~/gabagool/strategies/gabagool/grid_manager.py \
   ~/gabagool/strategies/gabagool/grid_manager.py.bak.pre_tick_refactor
cp ~/gabagool/strategies/gabagool/simple_strategy.py \
   ~/gabagool/strategies/gabagool/simple_strategy.py.bak.pre_tick_refactor
pm2 stop all
mkdir -p ~/gabagool-vault/HFT-Bot/Code_Snapshot/pre_tick_refactor_$(date -u +%Y%m%d)/
cp ~/gabagool/strategies/gabagool/grid_*.py \
   ~/gabagool-vault/HFT-Bot/Code_Snapshot/pre_tick_refactor_$(date -u +%Y%m%d)/
```

---

## Phase 0 — Config plumbing (~30 min)

### Step 0.1 — GridConfig dataclass (`grid_strategy.py:~190`)

```python
@dataclass
class GridConfig:
    # ── TICK / VENUE config (NEW) ──
    tick_size: float = 0.01
    min_lot: int = 5
    min_notional: float = 1.00
```

### Step 0.2 — Strategy `__init__` (L608 ✅ verified)

**File:** `grid_strategy.py:608`

```python
class GridStrategy:                                          # L606
    
    def __init__(self, config: GridConfig | None = None):    # L608
        # ... existing init ...
        # ── ADD HERE (after self.config setup): ──
        import math
        self.tick_size = self.config.tick_size               # 0.01 default
        self.price_decimals = abs(int(round(math.log10(self.tick_size))))
        # 0.01 → 2 decimals; 0.001 → 3 decimals
```

### Step 0.3 — YAML files

```yaml
# Control_Baseline.yaml etc (PM):
tick_size: 0.01

# HL_Test.yaml:
tick_size: 0.001
recovery_discount_cents: 0.0005       # NEW — half-tick at HL
adaptive_edge_default: 0.0038         # NEW — Q7 RESOLVED, was hardcoded 0.038 PM
edge_min: 0.0015                      # 1.5 ticks at HL (vs 0.015 = 1.5¢ PM)
edge_max: 0.005                       # 5 ticks
target_edge: 0.002                    # 2 ticks
cvd_skew_max_cents: 0.0015            # 1.5 ticks
garbage_dist_base: 0.008              # 8 ticks (vs 0.08 PM)
max_adaptive_edge: 0.012              # 12 ticks (vs 0.12 PM)
nudge_size: 0.001                     # 1 tick
alpha_ramp_min: 0.001                 # 1 tick
edge_vol_sensitivity: 0.001           # ← TBD — could be tick-rel coefficient OR absolute
```

### Step 0.4 — GridManager init signature + caller (L679 ✅ verified)

**File:** `grid_manager.py:~115` (GridManager.__init__)
```python
def __init__(self, ..., tick_size: float = 0.01, config = None):
    self.tick_size = tick_size
```

**Caller change** в `grid_strategy.py:679`:
```python
self.grid_manager = GridManager(
    # ... existing args ...
    tick_size=self.tick_size,    # ← ADD
    config=self.config,
)
```

---

## Phase 1 — 🟢 TICK_RELATIVE_BY_DESIGN (mechanical)

> Replace `TICK_SIZE` → `self.tick_size`.

### Phase 1.1 — `grid_manager.py` (9 places)

| File:Line | Current | Action |
|---|---|---|
| L67-69 | `TICK_SIZE=0.01`, `MIN_LOT=5`, `MIN_NOTIONAL=1.00` | Keep as `_DEFAULT_*` for compat OR remove |
| L178, L181 | `* TICK_SIZE * ...` (spacing) | Replace |
| L320, L321 | `4 * TICK_SIZE` (hunter tols) | Replace |
| L323, L324 | `2 * TICK_SIZE`, `3 * TICK_SIZE` (defcon) | Replace |
| L326, L327 | `self.X_threshold_ticks * TICK_SIZE` | Replace |

### Phase 1.2 — `grid_strategy.py` orchestrator (8 places)

| File:Line | Current | Action |
|---|---|---|
| L29 | `from grid_manager import TICK_SIZE` | Keep OR remove |
| **L1209** ⚠️ | `TICK_SIZE = 0.01` (LOCAL shadow) | **REMOVE** |
| L1542, L1554, L1680, L1694, L1713, L1723 | 6 plumbing points (`TICK_SIZE=TICK_SIZE`) | Option B: remove arg |

### Phase 1.3 — `grid_strategy.py` method signatures (6 methods)

| File:Line | Method | Verified? |
|---|---|---|
| **L3217** ✅ Pass 5 | `_apply_maq_filter(..., TICK_SIZE: float, ...)` | ✅ |
| **L3322** ✅ Pass 5 | `_apply_bbo_clamp(..., TICK_SIZE: float)` | ✅ |
| **L3519** ✅ Pass 6 | `_run_toxic_recovery_protocol(..., TICK_SIZE: float, is_active_y, is_active_n)` | ✅ |
| **L3775** ✅ Pass 7 (start) | `_compute_vector_pricing_and_hunter(..., TICK_SIZE: float, ...)` | ✅ partial |
| L4105 ⏳ | `_compute_healer(..., TICK_SIZE: float, fv_yes: float = 0.5)` | Pass 8 |
| **L5424** ✅ Pass 9 | `_compute_elastic_gravity(..., TICK_SIZE: float)` (no trailing args) | ✅ |

### Phase 1.4 — `grid_strategy.py` method bodies (TICK_SIZE arithmetic)

#### `_apply_maq_filter` (Pass 5 ✅)
| File:Line | Current | Notes |
|---|---|---|
| **L3291, L3292** ⭐ | `l0_y = round(l0_y / TICK_SIZE) * TICK_SIZE` | PROPER quantization (end-of-pipeline) |

#### `_apply_bbo_clamp` (Pass 5 ✅)
| File:Line | Current |
|---|---|
| **L3346** | `l0_y = safe_ask_y - TICK_SIZE` |
| **L3358** | `l0_n = safe_ask_n - TICK_SIZE` |

#### `_run_toxic_recovery_protocol` (Pass 6 ✅)
| File:Line | Current |
|---|---|
| **L3693** | `_market_floor = max(0.01, _bid - TICK_SIZE)` (Q3) |
| **L3706** | `safe_bid = _market_bid_side - TICK_SIZE` |
| **L3710** | `_healer_ceiling = min(_ask_side - TICK_SIZE, _probe_safe)` |
| **L3718** | `healer_price = min(healer_price, _avg - TICK_SIZE)` |

#### `_compute_vector_pricing_and_hunter` (Pass 7 ✅)
| File:Line | Current | Branch |
|---|---|---|
| **L3927** ✅ | `target_price_y = yes_ask - (TICK_SIZE * (1.0 - max(pressure, combined_panic)))` | Aggressive YES |
| **L3931** ✅ | `target_price_y = yes_bid + max(TICK_SIZE, spread_y * max(_min_pen, 0.4 * pressure))` | Passive YES |
| **L3951** ✅ | `target_price_n = no_ask - (TICK_SIZE * ...)` | Aggressive NO |
| **L3955** ✅ | `target_price_n = no_bid + max(TICK_SIZE, ...)` | Passive NO |

#### `_compute_healer` (Pass 8 ✅ verified actual code)
| File:Line | Current | Notes |
|---|---|---|
| **L4185** ✅ | `_our_leg_overpriced = (y_avg - mid_market) > TICK_SIZE` | YES leg overpriced check |
| **L4187** ✅ | `_our_leg_overpriced = (n_avg - (1.0 - mid_market)) > TICK_SIZE` | NO leg |
| **L4204** ✅ | `_closing_leg_available = derived_no_bid >= (_no_baseline - TICK_SIZE)` | NO closing avail |
| **L4208** ✅ | `_closing_leg_available = yes_bid >= (_y_baseline - TICK_SIZE)` | YES closing avail |
| **L4215** ✅ | `if q > 0 and mid_market < (y_avg - TICK_SIZE):` | YES recovery gate |
| **L4219** ✅ | `price_rec_y = max(0.01, min(yes_bid - TICK_SIZE, y_avg - TICK_SIZE, fv_yes + _hl_cap))` | YES healer price; **0.01 = Q3** |
| **L4225** ✅ | `elif q < 0 and ((1.0 - mid_market) < (n_avg - TICK_SIZE)):` | NO recovery gate |
| **L4229** ✅ | `price_rec_n = max(0.01, min(derived_no_bid - TICK_SIZE, n_avg - TICK_SIZE, (1.0 - fv_yes) + _hl_cap))` | NO healer price; **0.01 = Q3** |

#### `_compute_elastic_gravity` (Pass 9 ✅ verified actual code)
| File:Line | Current | Notes |
|---|---|---|
| **L5472** ✅ | `raw_penalty = (side_linear_steps ** power) * TICK_SIZE * p_stress_mult` | Central penalty formula. **Penalty уже tick-relative by design** — на HL automatically 10x smaller. Replace TICK_SIZE → self.tick_size. |

### Phase 1.5 — `simple_strategy.py` (Pass 11 ✅ verified actual code, 9 places)

| File:Line | Code | Cat | Action |
|---|---|---|---|
| L56 | `from grid_manager import TICK_SIZE` | 🟢 import | Same as L29 grid_strategy |
| **L455** ✅ | `l0_yes_price = min(l0_yes_price, yes_ask - TICK_SIZE)` | 🟢 | Replace TICK_SIZE → self.tick_size |
| **L457** ✅ | `l0_no_price = min(l0_no_price, no_ask - TICK_SIZE)` | 🟢 | Same |
| **L460** ✅ NEW | `l0_yes_price = max(0.01, min(0.99, l0_yes_price))` | 🟠 (Q3+Q2) | `0.01` → `self.tick_size`; `0.99` → `1.0 - self.tick_size` |
| **L461** ✅ NEW | `l0_no_price = max(0.01, min(0.99, l0_no_price))` | 🟠 (Q3+Q2) | Same |
| **L464** ✅ | `l0_yes_price = round(l0_yes_price, 2)` | 🟡 | `round(..., self.price_decimals)` |
| **L465** ✅ | `l0_no_price = round(l0_no_price, 2)` | 🟡 | Same |
| **L475** ✅ | `l0_yes_price = round(l0_yes_price - overflow - TICK_SIZE, 2)` | 🟢 + 🟡 | Both replacements |
| **L476** ✅ NEW | `l0_yes_price = max(0.01, l0_yes_price)` | 🟠 (Q3) | Replace |
| **L478** ✅ | `l0_no_price = round(l0_no_price - overflow - TICK_SIZE, 2)` | 🟢 + 🟡 | Both |
| **L479** ✅ NEW | `l0_no_price = max(0.01, l0_no_price)` | 🟠 (Q3) | Replace |

**NOT TOUCH** (config-driven):
- `if pair_cost > self.config.abs_max_pair_cost:` (`abs_max_pair_cost = 1.02` default) — pair-sum, NOT tick

### Phase 1.6 — `execution_engine_v6.py` (Pass 10 ✅ verified actual code)

> Pass 10 critical finding: `execution_engine_v6.py:L791` показывает что **CLOB передаёт dynamic tick_size через `get_tick_size(tid)`**. Это **подтверждает** что architecture поддерживает multi-venue, но hardcoded constants leak this abstraction.

| File:Line | Code | Cat | Action |
|---|---|---|---|
| **L125** | comment `"При TICK_SIZE = 0.01 минимальный сдвиг — это 1 цент"` | comment | **Update comment** to remove tick=0.01 assumption |
| **L127** ✅ NEW | `shift = 0.01` (in `_nudge_price`) | 🟢 | Replace `0.01` → `self.tick_size` (or `self.config.tick_size`) |
| **L128** | `if 'SELL_' in side: return round(price + shift, 2)` | 🟡 | `round(..., self.price_decimals)` |
| **L131** | `else: return round(price - shift, 2)` | 🟡 | Same |
| **L225** ⚠️ | `options = CreateOrderOptions(tick_size="0.01", neg_risk=False)` | 🔵 | **PM-specific Polymarket SDK call**. На HL — другой SDK entirely. Mark as Polymarket-only code path. |
| **L507** ⚠️ | `options = CreateOrderOptions(tick_size="0.01", neg_risk=False)` | 🔵 | Same |
| **L791** ⭐ | `tick_size = float(self.clob_client.get_tick_size(tid))` | ✅ DYNAMIC | **Already correct** — uses CLOB-provided tick. No change. |
| **L799** | `'tick_size': 0.01` (fallback в strategy_data dict) | 🟢 | Replace with `getattr(self, 'tick_size', 0.01)` OR keep PM default + override per-venue |

**Architectural insight:** L791 показывает что **infrastructure уже multi-venue ready** (CLOB API). Strategy class должен принимать tick_size from this dynamic value. Phase 0.4 caller change нужно verify что Strategy получает tick_size from CLOB при init, не hardcoded.

⚠️ **L225/L507 Polymarket-only:** При HL deployment эти лines не используются (другой SDK). Можно либо:
- (Quick) Leave hardcoded `tick_size="0.01"` для PM path
- (Clean) Make параметризуемым: `CreateOrderOptions(tick_size=str(self.tick_size), neg_risk=False)`

---

## Phase 2 — 🟡 IMPLICIT_DECIMAL_ASSUMPTION

### Phase 2.1 — `grid_manager.py` (2 places)

| File:Line | Current | Action |
|---|---|---|
| L190, L191 | `yes_price = round(... , 2)` / `no_price = round(... , 2)` | `round(..., self.price_decimals)` |

### Phase 2.2 — `grid_strategy.py`

| File:Line | Current | Notes |
|---|---|---|
| L1154 | `recovery_p = max(floor, round(recovery_p, 2))` | TBD context |
| L2621 | `price=round(taker_p, 2)` | Emergency dump |
| L2753 | `price=round(safe_price, 2)` | TBD |
| **L3659** ✅ Pass 6 | `healer_price = round(side_mkt_bid, 2)` | HEAL_MIRROR |
| **L3699** ✅ Pass 6 | `healer_price = round(_healer_start - ..., 2)` | TIME_HEAL formula |
| **L3711** ✅ Pass 6 | `healer_price = round(min(recovery_price, _healer_ceiling), 2)` | Deadlock |
| **L3716** ✅ Pass 6 | `healer_price = round(min(recovery_price, safe_bid), 2)` | Standard |
| L6728 | `sell_price = round(sell_price, 2)` | TBD |

### Phase 2.3 — Mysterious `round(..., 3)` (Q10 ✅ RESOLVED Pass 8)

> **RESOLUTION:** Эти `round(x, 3)` — **floating-point safety** для inverse pricing (`derived_no_X = 1.0 - yes_X`). Не tick-related — защита от FP drift типа `1.0 - 0.55 = 0.4499999...`.
> **Refactor:** `3` → `self.price_decimals + 1` (extra precision buffer для FP safety).
> На PM: 2+1=3 (current). На HL: 3+1=4 (safer).

| File:Line | Current | Action |
|---|---|---|
| **L4119** ✅ Pass 8 | `derived_no_ask = round(1.0 - yes_bid, 3) if yes_bid > 0 else 0.99` | `round(..., self.price_decimals + 1)`; `0.99` → `1.0 - self.tick_size` |
| **L4199** ✅ Pass 8 | `derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01` | Same; `0.01` → `self.tick_size` (Q3) |
| **L4226** ✅ Pass 8 | `derived_no_bid = round(1.0 - yes_ask, 3) ...` | Same |
| L6913, L6923 | `return max(0.01, round(safe_price, 3))` | `round(..., self.price_decimals + 1)`; `0.01` → `self.tick_size` (Q3) |

### Phase 2.5 — DO NOT TOUCH (telemetry)

`round(... * 100, 2)` percentage display in ~25 places. См. предыдущие версии для full list.

---

## Phase 3 — 🟠 / 🟣 HARDCODED_PRICE_VALUE

### Phase 3.1 — `0.01` minimum price floor (Q3 ✅ RESOLVED Pass 10) — FULL ENUMERATED LIST

> **Q3 RESOLVED Pass 10:** `execution_engine_v6.py:L791` shows `tick_size = float(self.clob_client.get_tick_size(tid))` — CLOB передаёт **dynamic tick** through API. L799 stores `tick_size: 0.01` as fallback default. Все internal `0.01` floors означают **"minimum tradable = 1 tick"** = `self.tick_size`.

**Refactor:** mechanical replace `0.01` → `self.tick_size` для всех ниже. Total: **41 + 4 = 45 places**.

#### `grid_strategy.py` (41 places)

| File:Line | Code | Cat |
|---|---|---|
| **L1046** ✅ | `p_clamped = max(0.01, min(mid_market, 0.99))` (Strike calc Black-Scholes inverse) | Q3 + Q2 (`0.99` = `1.0 - tick`) |
| **L1151** ✅ | `recovery_p = min(bid_p, target_exit_p) if bid_p > 0.01 else target_exit_p` | Q3 |
| **L1209** ⚠️ | `TICK_SIZE = 0.01` (LOCAL shadow в on_tick) | **REMOVE LINE** |
| **L2614** ✅ | `taker_p = max(0.01, bid_p - emergency_dump_slippage)` (Emergency dump) | Q3 |
| **L3349** ✅ | `if l0_y <= 0.01:` (BBO CLAMP_KILL warning) | Q3 |
| **L3361** ✅ | `if l0_n <= 0.01:` (BBO CLAMP_KILL warning) | Q3 |
| **L3460** ✅ | `if l0_y > 0.01:` (BBO post-clamp) | Q3 |
| **L3461** ✅ | `if safe_y <= 0.01:` | Q3 |
| **L3467** ✅ | `l0_y = safe_y if safe_y > 0.01 else 0.0` | Q3 |
| **L3470** ✅ | `if l0_n > 0.01:` | Q3 |
| **L3471** ✅ | `if safe_n <= 0.01:` | Q3 |
| **L3477** ✅ | `l0_n = safe_n if safe_n > 0.01 else 0.0` | Q3 |
| **L3693** ✅ | `_market_floor = max(0.01, _bid - TICK_SIZE)` (TIME_HEAL floor) | Q3 + Phase 1.4 |
| **L3719** ✅ | `healer_price = max(healer_price, 0.01)` (Standard recovery floor) | Q3 |
| **L3923** ✅ | `if safe_price_y > 0.01:` (Hunter YES check) | Q3 |
| **L3948** ✅ | `if safe_price_n > 0.01:` (Hunter NO check) | Q3 |
| **L4199** ✅ | `derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01` | Q3 + Q10 |
| **L4219** ✅ | `price_rec_y = max(0.01, min(yes_bid - TICK_SIZE, y_avg - TICK_SIZE, fv_yes + _hl_cap))` | Q3 + Phase 1.4 |
| **L4226** ✅ | `derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01` | Q3 + Q10 |
| **L4229** ✅ | `price_rec_n = max(0.01, min(derived_no_bid - TICK_SIZE, n_avg - TICK_SIZE, (1.0 - fv_yes) + _hl_cap))` | Q3 + Phase 1.4 |
| **L5138** ✅ | `dyn_thr = max(0.01, _base_thr - ((q_ratio ** 1.5) * 0.03))` | Q3 (threshold floor) |
| **L5551** ✅ | `y_exit_p = yes_bid if yes_bid > 0 else 0.01` (Exit price fallback) | Q3 |
| **L5552** ✅ | `n_exit_p = no_bid if no_bid > 0 else 0.01` | Q3 |
| **L5719** ✅ | `is_gate_blocked = (l0_y <= 0.01 and q < 0) or (l0_n <= 0.01 and q > 0)` | Q3 |
| **L6710** ✅ | `min_sell_price = max(0.01, min_sell_price)  # Не дешевле 1 цента` | Q3 + **update comment** |
| **L6824** ✅ | `target_price = max(0.01, bid_price - slippage)` | Q3 |
| **L6838** ✅ | `target_price = max(0.01, bid_price - slippage)` | Q3 |
| **L6913** ✅ | `return max(0.01, round(safe_price, 3))` | Q3 + Q10 |
| **L6923** ✅ | `return max(0.01, round(safe_price, 3))` | Q3 + Q10 |

#### Hardcoded `0.01` config defaults (Q3 — Phase 3.13 — tick-relative)

| File:Line | Code | Action |
|---|---|---|
| **L48** ✅ | `self.skew_max_cents = getattr(cfg, 'cvd_skew_max_cents', 0.015)` | Phase 5.5 — per-venue YAML |
| **L212** ✅ | `edge_min: float = 0.015` (1.5 cents PM) | Phase 5.5 — per-venue YAML |
| **L214** ✅ | `edge_vol_sensitivity: float = 0.01` | TBD — coefficient or tick-rel? |
| **L222** ✅ | `cvd_skew_max_cents: float = 0.015` | Phase 5.5 |
| **L306** ✅ | `alpha_ramp_min: float = 0.01` (1 cent gap) | Phase 5.5 — likely `1 * tick` |
| **L339** ✅ | `nudge_size: float = 0.01` | Phase 5.5 — `1 * tick` |
| **L1960** ✅ | `n_size = getattr(self.config, 'nudge_size', 0.01)` | Same as L339 |
| **L4649** ✅ | `base_edge = getattr(self.config, 'target_edge', getattr(self.config, 'edge_min', 0.015))` | Same as L212 — per-venue YAML |

#### NOT-Q3 occurrences (NOT_TICK — confirmed)

| File:Line | Code | Why NOT Q3 |
|---|---|---|
| L1973 | `if abs(q) > 20 and (active_gate_limit - self.config.gate_min) < 0.01:` | pair-sum diff threshold |
| L3407 | `base_gate += min(0.015, (abs(q) - 5) * 0.0015)` | pair-sum gate adjustment |
| L3428 | `max_gate_val = min(veto_panic_gate, max_gate_val + 0.015)` | pair-sum |
| L3882 | `... + (market_stress * 0.01)` | pair-sum coefficient |
| L3895 | comment "за red line (inv_ps >= 1.01 при tick=0.01)" | comment only |
| L4155 | comment "минимум 1 тик (0.01) дисконта" | Q15 comment ✅ |

#### `grid_manager.py` (4 places)

| File:Line | Code | Cat |
|---|---|---|
| **L69** ⚠️ | `TICK_SIZE = 0.01` (module-level) | **REMOVE or rename `_DEFAULT_TICK_SIZE`** |
| **L230** ✅ | `if yes_price < 0.01 or no_price < 0.01: continue` | Q3 |
| **L238** ✅ | `if yes_price >= 0.01 and yes_lot > 0:` | Q3 |
| **L245** ✅ | `if no_price >= 0.01 and no_lot > 0:` | Q3 |

### Phase 3.2 — `0.03` token floor (Q1 — likely absolute risk)

| File:Line | Current |
|---|---|
| `grid_manager.py:230` | `if yes_price < 0.03: yes_lot = 0` (БЕЗОПАСНОСТИ comment) |
| `grid_manager.py:230` | `if no_price < 0.03: no_lot = 0` |

### Phase 3.3 — `0.998` ceiling — **Q2 RESOLVED ✅ Pass 7** — TICK-RELATIVE (exact lines verified Pass 10)

> Pass 7 + GROUP D verification: `0.998` used as `price_cap = min(0.998, ...)` в **5 branches** of vector_pricing/ps_limit. Семантика: "never quote 2+ ticks below 1.0".

**Replace `0.998` → `1.0 - 2 * self.tick_size`** в **7 confirmed places**:

| File:Line | Code | Branch |
|---|---|---|
| **`grid_manager.py:227`** ✅ | `if yes_price > 0.998: yes_lot = 0` | Grid level filter |
| **`grid_manager.py:228`** ✅ | `if no_price > 0.998: no_lot = 0` | Grid level filter |
| **`grid_strategy.py:3997`** ✅ | `price_cap = min(0.998, 0.995 + boost)` | Desperate branch |
| **`grid_strategy.py:3999`** ✅ | `price_cap = min(0.998, hunter_gate + boost)` | Toxic flow + aggressive hunter |
| **`grid_strategy.py:4003`** ✅ | `price_cap = min(0.998, hunter_gate + boost)` | Hunter active |
| **`grid_strategy.py:4005`** ✅ | `price_cap = min(0.998, 0.95 + boost)` | Conservative branch |
| **`grid_strategy.py:4024`** ✅ | `ps_limit = min(0.998, 0.995 + boost)` | PS limit desperate |

### Phase 3.4 — `0.005` half-tick / discount (Q11 — per-venue YAML)

| File:Line | Current | Notes |
|---|---|---|
| L394 | `urgency_discount_base: float = 0.005` (config default) | YAML override |
| L3098 | `target = [... if not (... > (avg - 0.005))]` | Hardcoded — TBD |
| **L3529** ✅ Pass 6 | `disc_cents = ... 'recovery_discount_cents', 0.005` | Already config-driven |
| L6368 | `if p_range > 0.005:` | TBD |

### Phase 3.5 — `0.001` sub-tick (Q12)

| File:Line | Current |
|---|---|
| L2817, L2821 | `if l0 <= 0.001:` |
| **L3260** ✅ | `eff_maq = 0.001 if is_healing_now else dynamic_maq` |
| L4218 | (comment) |
| L4760 | `pressure = ... / max(0.001, ...)` (NOT_TICK division safety) |

### Phase 3.6 — Profit margins / loss tolerances (CONFIRMED ABSOLUTE)

> Не менять — absolute money values.

| File:Line | Param | Default | Cat |
|---|---|---|---|
| **L3527** ✅ Pass 6 | `toxic_exit_fv_threshold` | 0.04 | ⚪ FV space |
| **L3567** ✅ Pass 6 | `knife_protection_cents` | 0.15 | ⚪ TRIAGE absolute (Q6 ✅) |
| **L3640** ✅ Pass 6 | `mirror_min_improvement` | 0.04 | ⚪ profit margin |
| **L3641** ✅ Pass 6 | `unreal_loss < 0.025` | 0.025 | ⚪ profit threshold |
| **L3697** ✅ Pass 6 | `_healer_start = fv - 0.02` | hardcoded | ⚪ profit margin (Q14) |

### Phase 3.7 — Pair-sum thresholds (CONFIRMED NOT TICK — Q9 strengthened Pass 7)

> **Все эти thresholds — pair-sum (Y+N price)** в [0, 1.05] space. **NOT tick-related.** Don't replace.

| File:Line | Param | Value | Notes |
|---|---|---|---|
| (Pass 4) | `profit_gate_ps_max` (default in GridConfig) | 0.985 | Q8 ✅ pair-sum |
| (Pass 7) | `hunter_max_gate` (config) | 1.03 | NEW — panic ceiling, NOT tick |
| **Pass 7** | `hunter_locked_ps_guard` (config) | 1.005 | NEW — locked PS guard, NOT tick |
| **Pass 7** | `0.995` ceiling в multiple branches | hardcoded | NOT tick (pair-sum) |
| **Pass 7** | `0.990` (high stress branch) | hardcoded | NOT tick |
| **Pass 7** | `0.95` (else branch — non-hunter) | hardcoded | NOT tick (conservative cap) |
| (Pass 5) | `veto_panic_gate` | 1.050 | NOT tick |

### Phase 3.8 — GC gap kill `0.05` — **Q13 REVISED Pass 10** ⚠️

> **Q13 REVISED:** Pass 10 found `garbage_dist_base = 0.08` (NOT 0.05!). Это **отдельный** GC threshold от 0.05 occurrences. 
> 
> Hierarchy:
> - `garbage_dist_base = 0.08` — outer GC perimeter (`max_allowed_spread = 0.068 = 0.08 * 0.85`)
> - `0.05` — inner death zone — НЕ derived from garbage_dist_base
>
> **Hypothesis revised:** `0.05` likely **tick-relative `5 * self.tick_size`** OR separate hardcoded "5¢ death zone" constant. Не connected to garbage_dist_base.

| File:Line | Current | Action |
|---|---|---|
| **L3622** ✅ Pass 6 | `if (_side_bid - healer_price) > 0.05: warning(HEALER_GAP_KILL)` | `5 * self.tick_size` |
| **L3669** ✅ Pass 6 | Same warning re-occurrence | `5 * self.tick_size` |
| **PS_SQUASH ~L4040** ✅ Pass 7 | `if (bid - val) > 0.05: SQUEEZE_DEATH` (2 places) | `5 * self.tick_size` |
| **~L5495, ~L5500** ✅ Pass 9 | `if p_side.get('YES'/'NO', 0.0) >= 0.05: POISON_MATH` | `5 * self.tick_size` |
| **L4639** ✅ Pass 10 | `spread_penalty = max(0, (current_mkt_spread - 0.05) / 2.0)` | **DIFFERENT** — spread normalization point. NOT_TICK (formula coefficient). |

### Phase 3.9 — Aggressive Hunter `max_panic_price` formula (NEW Pass 7)

```python
# Pass 7 confirmed:
max_panic_price = fv_yes + (max_gate - 1.0)        # YES branch
max_panic_price = (1.0 - fv_yes) + (max_gate - 1.0)  # NO branch
```

`(max_gate - 1.0) = 0.03` derived from `hunter_max_gate=1.03` config. **Already config-driven** through `max_gate`. **NOT tick-related.** Leave as-is.

### Phase 3.10 — Tick-calibrated magic constants (Q15 NEW Pass 8) ⭐

> **CRITICAL FINDING Pass 8:** `0.35` floor в `_compute_healer` **explicitly calibrated to PM tick=0.01**.
> Comment в коде: *"floor 0.30→0.35: минимум 1 тик (0.01) дисконта при любом InvL. При InvL=1.0: 3.0c × 0.35 = 1.05c → 1 тик ✓. floor<0.33 → discount<1 тика → 0"*.

| File:Line | Current | Action |
|---|---|---|
| **~L4140** ✅ Pass 8 | `discount_cents = discount_cents * max(0.35, 1.0 - _il)` | **DERIVE FROM tick_size:**<br>`min_floor = self.tick_size / 0.030  # ensure >= 1 tick after scaling`<br>`discount_cents = discount_cents * max(min_floor, 1.0 - _il)`<br>На PM: `0.01/0.030 = 0.333` ≈ current `0.35`<br>На HL: `0.001/0.030 = 0.0333` (much smaller floor needed) |

**Альтернативный refactor (cleaner):**
```python
# Replace the floor logic entirely with explicit guarantee:
discount_cents = max(self.tick_size, discount_cents * (1.0 - _il))
```

Это **guarantees** discount >= 1 tick без magic constants.

### Phase 3.11 — `0.99` ceiling fallback (Q2 nuance Pass 8)

> Pass 8 discovered: `else 0.99` fallback в derived_no_ask — это **`1.0 - 1*self.tick_size`** (single tick from 1.0). Different scale от `0.998 = 1.0 - 2*tick`.

| File:Line | Current | Action |
|---|---|---|
| **L4119** ✅ Pass 8 | `derived_no_ask = round(... , 3) if yes_bid > 0 else 0.99` | `else 1.0 - self.tick_size` |
| L1046 | `p_clamped = max(0.01, min(mid_market, 0.99))` | `0.99` → `1.0 - self.tick_size` |

### Phase 3.12 — Gravity penalty cap `0.15` (Q16 NEW Pass 9) ⭐

> **Pass 9 finding:** `p_side[_side] = min(0.15, raw_penalty * asym_factor)` — penalty cap.
> `0.15` matches **3 other locations**: `knife_protection_cents=0.15` (TRIAGE_DEATH absolute loss), `max_penalty_dev=0.15` (penalty fraction).
> 
> **Note:** `raw_penalty` уже includes TICK_SIZE multiplier (L5472). Cap `0.15` действует as outer ceiling.
> На HL tick=0.001: `raw_penalty` natural value 10x smaller, cap rarely triggered → effectively becomes irrelevant.
>
> **Two refactor options:**
>
> **Option A (Per-venue YAML):** Move to config `gravity_penalty_cap`. PM=0.15, HL=0.015 (tick-relative scaling). Recommended.
>
> **Option B (Tick-rel formula):** `min(15 * self.tick_size, raw_penalty * asym_factor)`. На PM same value, на HL becomes 0.015 = 15 ticks.

| File:Line | Current | Action |
|---|---|---|
| **~L5485** ✅ Pass 9 | `p_side[_side] = min(0.15, raw_penalty * asym_factor)` | Option A: config `gravity_penalty_cap` (default 0.15 PM, 0.015 HL). Option B: `min(15 * self.tick_size, ...)` |

### Phase 3.13 — `adaptive_edge` hardcoded magic (Q7 ✅ RESOLVED Pass 10) ⭐

> **Q7 RESOLVED Pass 10:** `adaptive_edge = 0.038` is **hardcoded local var** в `on_tick`, NOT a GridConfig default!
> Calibrated на PM tick=0.01. На HL это 38 ticks — слишком широкий spread.

| File:Line | Current | Action |
|---|---|---|
| **L1207** ✅ Pass 10 | `adaptive_edge = 0.038` (local declaration в on_tick) | **Option A:** Make config-driven: `adaptive_edge = getattr(self.config, 'adaptive_edge_default', 0.038)`. Per-venue YAML override.<br>**Option B:** Tick-relative: `adaptive_edge = 3.8 * self.tick_size` (= 0.038 PM, 0.0038 HL).<br>Recommended: **Option A** (cleaner, explicit per-venue tuning). |

### Phase 3.14 — `_compute_spread_and_shield` config defaults (NEW Pass 10) — Per-venue YAML

> **Pass 10 GROUP E findings:** `_compute_spread_and_shield` (L4613) **does NOT take TICK_SIZE parameter** — confirms architectural assumption. Edge params live в `self.config`.
> 
> Recommended: **per-venue YAML override**, no code refactor нужен.

| File:Line | Param | PM Default | HL Recommendation | Notes |
|---|---|---|---|---|
| **L4669** | `edge_min_v = getattr(self.config, 'edge_min', 0.003)` | 0.015 (dataclass default) / 0.003 (fallback) | 0.0015 / 0.0003 | ⚠️ **Inconsistency**: dataclass=0.015, getattr fallback=0.003. Verify YAML override |
| **L4649** | `base_edge = getattr('target_edge', getattr('edge_min', 0.015))` | 0.015 | 0.0015 | Per-venue YAML |
| **L4702** ⭐ | `dist_base = getattr(self.config, 'garbage_dist_base', 0.08)` | 0.08 | 0.008 | Per-venue YAML — **Q13 revision** |
| **L4703** | `max_allowed_spread = dist_base * 0.85` | 0.068 (derived) | 0.0068 | Auto-scaled from dist_base |
| **L4704** | `max_adaptive = getattr('max_adaptive_edge', 0.12)` | 0.12 | 0.012 | Per-venue YAML |
| **L4691** | `if current_btc_delta >= 0.020 or btc_vel > 15.0:` | hardcoded | NOT tick (BTC USD threshold) | Skip |
| **L4692-4693** | `edge_y *= 1.5` / `edge_n *= 1.5` (Crossfire) | hardcoded | NOT tick (multiplier) | Skip |
| **L4639** | `spread_penalty = max(0, (current_mkt_spread - 0.05) / 2.0)` | 0.05 | TBD | **DIFFERENT 0.05** from Q13 — spread normalization midpoint. Likely tick-rel `5 * self.tick_size` OR absolute. |

---

## Phase 4 — 🔵 VENUE_CONSTRAINT (separate refactor)

| File:Line | Current | Notes |
|---|---|---|
| `grid_manager.py:69` | `MIN_LOT=5`, `MIN_NOTIONAL=1.00` | Module-level |
| `grid_manager.py:218, 224` | `min_lot = int(1.05 / price) + 1` | MIN_NOTIONAL+cushion |
| `grid_manager.py:240, 244` | `if notional >= 1.01` | MIN_NOTIONAL+1tick |
| `grid_strategy.py:1772, 5169` | `MIN_MKT_LOT=5` | Local refs |

---

## Phase 5 — 🟣 UNCLEAR_SEMANTICS (Q-table)

| Q# | Question | Status |
|---|---|---|
| Q1 | `< 0.03` token floor — abs или tick-rel? | Likely absolute (БЕЗОПАСНОСТИ) |
| Q2 ✅ | `> 0.998` ceiling — `1.0 - 2*tick`? | **RESOLVED Pass 7** — tick-relative confirmed |
| Q3 ✅ | `< 0.01` minimum — `self.tick_size`? | **RESOLVED Pass 10** — `execution_engine_v6.py:L791` shows `tick_size = float(self.clob_client.get_tick_size(tid))` — CLOB provides dynamic tick. L799 fallback `0.01`. All internal floors = `self.tick_size`. **41 places in grid_strategy.py + 4 in grid_manager.py + 4 in simple_strategy.py + 2 in execution_engine.py = 51 total places**. |
| Q4 | `MIN_NOTIONAL = 1.00` should be config? | Yes — separate refactor |
| Q5 | `*_cents` / `edge_*` — tick-rel или abs? | Per-param. PARTIAL: profit margins = abs; recovery_discount = per-venue |
| Q6 ✅ | `toxic_price_threshold: 0.15` — abs? | **STRENGTHENED Pass 6** — `knife_protection_cents=0.15` confirmed abs |
| Q7 ✅ | `adaptive_edge = 0.038` default — tick-rel? | **RESOLVED Pass 10** — `grid_strategy.py:L1207` `adaptive_edge = 0.038` is **hardcoded local var в on_tick** (NOT GridConfig default!). Magic value calibrated на PM tick=0.01. Refactor: make config-driven `getattr(self.config, 'adaptive_edge_default', 0.038)` OR tick-relative `3.8 * self.tick_size`. |
| Q8 ✅ | `profit_gate_ps_max: 0.985` — pair-sum? | RESOLVED Pass 4 |
| Q9 ✅ | Pair-sum thresholds — NOT tick? | **STRENGTHENED Pass 7** — confirmed via hunter_max_gate=1.03, hunter_locked_ps_guard=1.005, 0.995/0.990/0.95 caps |
| Q10 ✅ | `round(x, 3)` — bug? | **RESOLVED Pass 8** — floating-point safety для inverse pricing (`1.0 - yes_X`); refactor: `3` → `self.price_decimals + 1` |
| Q11 | `0.005` half-tick — abs или `tick/2`? | PARTIAL Pass 6 — recovery_discount per-venue YAML |
| Q12 | `0.001` "almost zero" — abs или `tick/10`? | WEAK Pass 5 — likely abs |
| Q13 ✅ | `0.05` GC gap kill — tick-rel или config? | **REVISED Pass 10** — `garbage_dist_base = 0.08` (NOT 0.05!) confirmed at `grid_strategy.py:L4702`. The 5 occurrences of `0.05` are **separate** from garbage_dist_base. Hierarchy: `garbage_dist_base=0.08` (outer GC perimeter), `0.05` (inner death zone). Refactor: `0.05` → `5 * self.tick_size`. На HL tick=0.001 → 0.005 (5 ticks). |
| Q14 | `_healer_start = fv - 0.02` — abs? | **STRENGTHENED Pass 8** — `0.02` value used в 2 places: TIME_HEAL `_healer_start` (Pass 6) + Mirror `trigger_gap` (Pass 8). Absolute "2¢ profit margin" pattern confirmed |
| Q15 ⭐ | `max(0.35, 1.0 - _il)` — magic floor для discount_cents calibrated to PM tick=0.01? | **NEW Pass 8** — comment explicit: "минимум 1 тик дисконта при любом InvL. При InvL=1.0: 3.0c × 0.35 = 1.05c → 1 тик ✓". HL refactor: derive floor from `self.tick_size / discount_cap`. |
| Q16 ⭐ | `p_side = min(0.15, raw_penalty * asym_factor)` — gravity penalty cap tick-rel? | **NEW Pass 9** — `0.15` matches `knife_protection_cents=0.15` and `max_penalty_dev=0.15`. Hypothesis: tick-relative `15 * self.tick_size` (на HL → 0.015 = 15 ticks). Note: `raw_penalty` уже includes TICK_SIZE multiplier (L5472), так что cap может быть absolute "max 15¢ skew" by design. **Per-venue YAML override** — recommended approach. |

**Resolution score:** 8/16 fully resolved (Q2, Q3, Q6, Q7, Q8, Q9, Q10, Q13), 6/16 partial (Q5, Q11, Q14, Q15, Q16, Q4-architectural), 2/16 pending (Q1, Q12).

**Q5 final architectural decision:** edge params в `_compute_spread_and_shield` (Pass 10 GROUP E confirmed) **NOT use TICK_SIZE arithmetic** — оперируют через `self.config` напрямую. **Refactor approach:** **per-venue YAML override only** (Step 0.3 includes scaled defaults для HL). См. Phase 3.14.

**⚠️ Inconsistency found Pass 10:** `edge_min` имеет 2 different defaults:
- GridConfig dataclass L212: `edge_min: float = 0.015`
- `_compute_spread_and_shield` L4669 fallback: `getattr(self.config, 'edge_min', 0.003)`

Dataclass default (0.015) wins на runtime если YAML не override. L4669 fallback unreachable если GridConfig fully populated. **Document for YAML setup verification**.

---

## Phase 6 — ⚪ NOT_TICK_RELATED (skip — confirmed)

### Pass 1-6 list
- `max_penalty_dev`, velocity_*, btc_vel_*, oracle_drift, FV thresholds
- `MAQ_BASE`, `trend_maq`, `empty_book_premium`, `gamma_maq_min_discount`
- `maq_asym_hedge_threshold`, `veto_panic_gate=1.050`
- `toxic_exit_fv_threshold`, `avg_tranche_max_size`, `time_heal_*`
- `knife_protection_cents=0.15`, `mirror_min_improvement=0.04`, `unreal_loss<0.025`
- Telemetry rounds, USD display, BTC display

### Pass 7 NEW NOT_TICK additions
- **`_dynamic_hard_cutoff: 35`** default — Q hard cutoff threshold (shares) для pressure calc
- **PING-PONG FV GUARD** — `if fv_yes > 0.70: l0_n_std = 0.0` / `if fv_yes < 0.30: l0_y_std = 0.0` — blocks counter-trend leg при extreme FV (FV space [0,1])
- **`endgame_hunter_buffer_sec`** — time
- **`hunter_max_gate: 1.03`** — pair-sum panic ceiling
- **`hunter_locked_ps_guard: 1.005`** — pair-sum locked PS guard
- **`hunter_min_penetration: 0.25`** — fraction [0,1]
- **`survival_start = effective_scale * 1.5`** — share scale
- **`survival_max = effective_scale * 3.0`** — share scale
- **`profit_buffer = realized_pnl / 400.0`** — USD normalizer (deposit baseline)
- **`stuck_time_ratio = (time_since_fill - 45.0) / 120.0`** — time arithmetic
- **`combined_panic ** 1.5`** — exponential
- **`market_stress * 0.01`** — additive coefficient (NOT tick — pair-sum space)
- **`max_panic_price = fv + (max_gate - 1.0)`** — derived from hunter_max_gate
- **`0.95` price_cap conservative branch** — absolute confidence cap
- **`0.990` ps_limit high-stress** — pair-sum
- **`abs(q) > 10`** — share count
- **`reduction_ratio = ps_limit / current_ps_sum`** — proportional scaling
- **`(1 - reduction_ratio) * 100`** — percentage display
- **`_min_q_flow = max(5, imb_threshold // 2)`** — share count

### Pass 8 NEW NOT_TICK additions
- **`recovery_inv_ps_threshold: 0.99`** — pair-sum threshold для healer activation (NOT tick)
- **`0.95` floor** в `toxic_threshold = max(0.95, ...)` — pair-sum minimum
- **`_il * 0.04`** adjustment — absolute scale (same as `mirror_min_improvement`)
- **`healer_max_overpay: 0.030`** — absolute overpay tolerance (3¢)
- **`discount_cents` hard cap `0.030`** — absolute (comment: "10c было нереалистично")
- **`healer_mult = 1.0 + fv_distance * 2.0`** — formula (FV-based)
- **`fv_distance = abs(fv_yes - 0.5) * 2.0`** — FV space [0,1]
- **`q >= 3` / `q <= -3`** — share count
- **`_intent_load * 0.04`** — adjustment scale (absolute)

### Pass 9 NEW NOT_TICK additions
- **`raw_price_factor = 1.0 - (heavy_price - 0.5)`** — formula (FV-based)
- **`price_factor = max(0.85, min(1.15, raw_price_factor))`** — bounds [0.85, 1.15]
- **`knife_threshold = 0.025`** — FV velocity threshold (rate-of-change)
- **`vel_panic = 1.5 if is_knife_falling else 1.0`** — multiplier
- **`q >= 5` / `q <= -5`** — share count thresholds
- **`risk_weight_power: 2.0`** default — power exponent (config-driven, NOT tick)
- **`_prev_dyn_scale: 25.0`** default — dynamic inverse scale baseline
- **`aggression_scale = max(10.0, _dyn_inv_scale - (abs(_q_eff) * 0.5))`** — share scale formula
- **`asym_factor = max(0.5, min(2.0, ...))`** — asymmetry bounds
- **`_pair_state` FRESH multipliers `0.3 / 1.5`** — penalty modulation (closing/opening leg)
- **`side_deadband * 0.5`** — weak leg deadband fraction

---

## Architecture decision — Option A vs B

**Option B recommended** (remove TICK_SIZE from method signatures, methods read `self.tick_size` directly). Defer **final** decision until Pass 8-11.

---

## Order of operations

1. Phase 0 (config plumbing)
2. Phase 1.1 (grid_manager)
3. Phase 1.2 (orchestrator + remove L1209)
4. Phase 2.1 (grid_manager round)
5. Phase 1.3-1.4 (method signatures + bodies)
6. Phase 2.2 (grid_strategy round)
7. Phase 3 (hardcoded values per Q resolution)
8. Phase 1.5 + 2.4 (simple_strategy)
9. Smoke test PM tick=0.01 — bit-identical
10. Smoke test HL tick=0.001 — observe new behavior

---

# AUDIT DETAILS (per-pass)

## Read passes plan

```
Pass 1:  grid_manager.py             ✅ DONE — 18 findings
Pass 2:  grid_strategy.py 1-250      ✅ DONE — 11 findings
Pass 3:  grid_strategy.py 1180-1260  ✅ DONE — 5 findings (TICK_SIZE shadow)
Pass 4:  grid_strategy.py 1500-1760  ✅ DONE — 9 findings (orchestrator)
Pass 5:  grid_strategy.py 3200-3400  ✅ DONE — 17 findings (maq+bbo)
Pass 6:  grid_strategy.py 3500-3800  ✅ DONE — 21 findings (recovery)
Pass 7:  grid_strategy.py 3850-4100  ✅ DONE — 19 findings (verified actual code)
Pass 8:  grid_strategy.py 4100-4300  ✅ DONE — 22 findings (verified actual code)
Pass 9:  grid_strategy.py 5400-5550  ✅ DONE — 13 findings (verified actual code; Q5/Q7 NOT in this method)
Pass 10: execution_engine_v6.py      ✅ DONE — 7 findings (verified actual code; Q3 RESOLVED ✅)
Pass 11: simple_strategy.py 440-490  ✅ DONE — 11 findings (verified actual code; new clamps found L460-461, L476, L479)
```

## Cumulative running totals (FINAL)

| Category | Count |
|---|---|
| 🟢 TICK_RELATIVE_BY_DESIGN | **45** (mechanical replacements: 36 grid_strategy + 9 grid_manager/simple/exec_engine) |
| 🟡 IMPLICIT_DECIMAL_ASSUMPTION | **13** (5 grid_strategy `round(,2)` + 4 round(,3) Q10 ✅ + 2 simple_strategy `round(,2)` + 2 exec_engine `round(,2)`) |
| 🟠 HARDCODED_PRICE_VALUE | **51 Q3 ✅** + 7 Q2 ✅ + 5 Q13 ✅ + 1 Q15 + 2 Q14 + 1 Q16 + 1 Q7 ✅ = **68 places** |
| 🔵 VENUE_CONSTRAINT | 3 + 2 PM SDK calls (exec_engine L225/507) = 5 |
| 🟣 UNCLEAR_SEMANTICS | 16 (Q1-Q16, **8 fully resolved**) |
| ⚪ NOT_TICK_RELATED | 70+ |
| **TOTAL identified** | **~155 confirmed places** |

## Pass 7 — `_compute_vector_pricing_and_hunter` ✅ DONE

### Key findings — 4 pricing branches

#### Branch 1 — Aggressive Hunter YES (`q < -imb_threshold AND is_aggressive_hunter`)

```python
target_price_y = yes_ask - (TICK_SIZE * (1.0 - max(pressure, combined_panic)))   # L3927
target_price_y = max(yes_bid, target_price_y)
# Then:
max_panic_price = fv_yes + (max_gate - 1.0)
if target_price_y <= max_panic_price:
    l0_y_hunter = target_price_y      # TEETH
else:
    l0_y_hunter = safe_price_y        # SQUASH
```

#### Branch 2 — Passive Hunter YES

```python
_min_pen = getattr(self.config, 'hunter_min_penetration', 0.25)
target_price_y = yes_bid + max(TICK_SIZE, spread_y * max(_min_pen, 0.4 * pressure))   # L3931
l0_y_hunter = min(target_price_y, safe_price_y)
```

#### Branch 3-4 — NO mirror logic (L3951, L3955)

#### Final arbitration (line ~end)

```python
boost = getattr(self, '_emergency_hunter_boost', 0.0)
if is_desperate:
    price_cap = min(0.998, 0.995 + boost)        # ← Q2 RESOLVED
elif is_flow_toxic and is_aggressive_hunter:
    price_cap = min(0.998, hunter_gate + boost)
elif l0_y_hunter > 0 or l0_n_hunter > 0:
    price_cap = min(0.998, hunter_gate + boost)
else:
    price_cap = min(0.998, 0.95 + boost)         # conservative

l0_y = min(price_cap, max(l0_y_std, price_rec_y, l0_y_hunter))
l0_n = min(price_cap, max(l0_n_std, price_rec_n, l0_n_hunter))
```

#### PS_LIMIT formula

```python
if is_desperate:
    ps_limit = min(0.998, 0.995 + boost)
elif self._unified_stress_level > 0.75:
    ps_limit = 0.990
else:
    raw_gate = getattr(self, '_tick_base_gate', 
                       getattr(self.config, 'profit_gate_ps_max', 0.985))
    ps_limit = min(raw_gate, 0.995) if abs(q) > 10 and not is_toxic_bag else raw_gate
```

#### PS_SQUASH section (asymmetric squeezing — 4 branches confirmed actual code)

```python
current_ps_sum = l0_y + l0_n
if current_ps_sum > ps_limit:
    is_rescue_y = (l0_y_hunter > 0) or (price_rec_y > 0)
    is_rescue_n = (l0_n_hunter > 0) or (price_rec_n > 0)
    
    if is_desperate:
        # DESPERATE SQUEEZE — cap heavy leg
        if q > 0:    l0_y = max(0.0, ps_limit - l0_n)
        elif q < 0:  l0_n = max(0.0, ps_limit - l0_y)
    elif is_rescue_y and not is_rescue_n:
        # ASYM_Y — спасаем YES, срезаем passive NO
        l0_n = max(0.0, ps_limit - l0_y)
    elif is_rescue_n and not is_rescue_y:
        # ASYM_N — спасаем NO, срезаем passive YES
        l0_y = max(0.0, ps_limit - l0_n)
    else:
        # SOFT PRESS — proportional reduction
        reduction_ratio = ps_limit / current_ps_sum
        l0_y *= reduction_ratio
        l0_n *= reduction_ratio
    
    # SQUEEZE_DEATH warning (Q13 — 0.05 gap kill)
    for s, val, bid in [('YES', l0_y, yes_bid), ('NO', l0_n, no_bid)]:
        if val > 0 and bid > 0 and (bid - val) > 0.05:
            warning(SQUEEZE_DEATH)
```

End of PS_SQUASH:
```python
if val > 0 and bid > 0 and (bid - val) > 0.05:
    warning(SQUEEZE_DEATH)   # ← Q13 strengthened
```

### Critical resolutions

#### Q2 RESOLVED ✅ — `0.998` ceiling = `1.0 - 2*self.tick_size`

`0.998` used as **price_cap** в multiple branches. Семантика: "never quote within 2 ticks of 1.0 — saturation territory".

**Refactor:** все hardcoded `0.998` → `1.0 - 2 * self.tick_size`. Total ~7 places (4 in vector_pricing, 1 in ps_limit, 2 in grid_manager).

#### Q9 STRENGTHENED — pair-sum thresholds confirmed NOT tick

Discovered config params:
- `hunter_max_gate: 1.03` (>1.0 — definitely pair-sum panic ceiling)
- `hunter_locked_ps_guard: 1.005` (>1.0 — locked PS guard)
- Hardcoded: `0.995`, `0.990`, `0.95` все в pair-sum logic

#### Q13 STRENGTHENED — `0.05` GC gap kill appears 4 times

Pass 6: HEALER_GAP_KILL (L3622, L3669)
Pass 7: SQUEEZE_DEATH (2 places)

Pattern: `if (bid - price) > 0.05: warning("will be killed by GC")`. Likely either tick-relative `5 * self.tick_size` OR config-driven through `garbage_dist_base`.

### Findings table (compact)

| # | Line | Code | Cat |
|---|---|---|---|
| 82 | ~3855 | `hc_limit = self._dynamic_hard_cutoff` | ⚪ shares |
| 83 | ~3858 | `endgame_hunter_buffer_sec` | ⚪ time |
| 84 | ~3859 | `hunter_max_gate = 1.03` | ⚪ pair-sum |
| 85 | ~3860 | `survival_start = effective_scale * 1.5` | ⚪ shares |
| 86 | ~3861 | `survival_max = effective_scale * 3.0` | ⚪ shares |
| 87 | ~3862 | `profit_buffer = realized_pnl / 400.0` | ⚪ USD norm |
| 88 | ~3866 | `current_base = min(tick_base + profit_buffer, 0.995)` | ⚪ pair-sum |
| 89 | ~3870 | `stuck_time_ratio = (... - 45.0) / 120.0` | ⚪ time |
| 90 | ~3878 | `combined_panic = q_panic_ratio + stuck_time_ratio**1.5` | ⚪ math |
| 91 | ~3882 | `calculated_gate = ... + market_stress * 0.01` | ⚪ pair-sum coef |
| 92 | ~3892 | `_min_q_flow = max(5, imb_threshold // 2)` | ⚪ shares |
| 93 | ~3901 | `hunter_locked_ps_guard = 1.005` | ⚪ pair-sum |
| 94 | ~3920 | `if safe_price_y > 0.01:` | 🟠 (Q3) |
| 95 | **L3927** | `target_price_y = yes_ask - (TICK_SIZE * (1.0 - max(pressure, combined_panic)))` | 🟢 |
| 96 | **L3931** | `target_price_y = yes_bid + max(TICK_SIZE, spread_y * max(_min_pen, 0.4 * pressure))` | 🟢 |
| 97 | ~3933 | `_min_pen = ... 'hunter_min_penetration', 0.25` | ⚪ fraction |
| 98 | ~3937 | `max_panic_price = fv_yes + (max_gate - 1.0)` | ⚪ derived |
| 99 | **L3951** | `target_price_n = no_ask - (TICK_SIZE * ...)` | 🟢 |
| 100 | **L3955** | `target_price_n = no_bid + max(TICK_SIZE, ...)` | 🟢 |
| ~ | (4 places) | `price_cap = min(0.998, ...)` | 🟢 (Q2 ✅) |
| ~ | (1 place) | `ps_limit = min(0.998, 0.995 + boost)` desperate | 🟢 (Q2 ✅) |
| ~ | (2 places) | `if (bid - val) > 0.05: SQUEEZE_DEATH` | 🟣 (Q13) |

**Pass 7 summary:** 19 findings + 7 Q2-resolution places + PING-PONG GUARD + _dynamic_hard_cutoff. Cumulative: ~100 places identified.

### Pass 7 verification status

**ALL Pass 7 findings VERIFIED with actual code (chunk gs6_hunter.py):**

✅ Q2 RESOLVED — 4 occurrences of `price_cap = min(0.998, ...)` confirmed verbatim:
   - `is_desperate` branch: `min(0.998, 0.995 + boost)`
   - `is_flow_toxic and is_aggressive_hunter`: `min(0.998, hunter_gate + boost)`
   - `l0_y_hunter > 0 or l0_n_hunter > 0`: `min(0.998, hunter_gate + boost)`
   - `else (conservative)`: `min(0.998, 0.95 + boost)`

✅ Hunter pricing (L3927/L3931/L3951/L3955) verified verbatim — Aggressive/Passive YES/NO formulas.

✅ HUNTER_LOCKED_PS_GUARD logic confirmed:
```python
_existing_locked_ps = (yes_cost / yes) + (no_cost / no)
_hunter_locked_guard = getattr(self.config, 'hunter_locked_ps_guard', 1.005)
if _existing_locked_ps > _hunter_locked_guard:
    is_aggressive_hunter = False  # disable bypass — let healer work
```
> Защита от deepening locked position в panic mode. **NOT_TICK_RELATED** (pair-sum).

✅ PS_LIMIT formula verified:
```python
if is_desperate:                              ps_limit = min(0.998, 0.995 + boost)
elif _unified_stress_level > 0.75:            ps_limit = 0.990
else:
    raw_gate = ... 'profit_gate_ps_max', 0.985
    ps_limit = min(raw_gate, 0.995) if abs(q) > 10 and not is_toxic_bag else raw_gate
```

✅ PS_SQUASH section: 4 branches confirmed (was 3 in inference).

### Pass 7 NEW additions from actual code

1. **PING-PONG FV GUARD** (NEW finding):
   ```python
   if getattr(self, '_is_pingpong', False):
       if fv_yes > 0.70:    l0_n_std = 0.0    # block counter-trend NO
       elif fv_yes < 0.30:  l0_y_std = 0.0    # block counter-trend YES
   ```
   > Blocks counter-trend leg при extreme FV в TORPEDO/RECOVERY regime. **NOT_TICK_RELATED** (FV space [0,1]).

2. **`_dynamic_hard_cutoff`** default 35 — Q hard cutoff для pressure formula:
   ```python
   hc_limit = getattr(self, '_dynamic_hard_cutoff', 35)
   pressure = min(1.0, abs(q) / max(1, hc_limit))
   ```
   > **NOT_TICK_RELATED** (share count).

3. **Hunter SLEEP state** (`_hunter_sleeping` block_state) — separate decision branch.

---

## Pass 1-6 details (compact)

См. предыдущие версии этого файла в git history для full breakdown. Compact summary:

- **Pass 1** (`grid_manager.py`): module-level TICK_SIZE/MIN_LOT/MIN_NOTIONAL. 9 mechanical, 2 round, Q1-Q4.
- **Pass 2** (`grid_strategy.py:1-250`): GridConfig central registry. Q5 setup.
- **Pass 3** (`grid_strategy.py:1180-1260`): TICK_SIZE shadow declaration L1209 ⚠️. Q7/Q8/Q9 setup.
- **Pass 4** (`grid_strategy.py:1500-1760`): Pipeline mapping. Q8 ✅ resolved (pair-sum NOT tick).
- **Pass 5** (`grid_strategy.py:3200-3400`): _apply_maq_filter / _apply_bbo_clamp. End-of-pipeline proper quantization (L3291-3292). MAQ_BASE/trend_maq/empty_book_premium = ABSOLUTE.
- **Pass 6** (`grid_strategy.py:3500-3800`): _run_toxic_recovery_protocol. 3 healer branches (MIRROR/TIME_HEAL/Standard). Q6 ✅ strengthened (knife_protection abs). Q11 partial (per-venue YAML). Q13/Q14 NEW.

---

## Pass 8 — `_compute_healer` ✅ DONE (verified actual code)

### Method signature confirmed (L4105):

```python
def _compute_healer(self, q: int, mid_market: float, yes_ask: float, yes_bid: float, TICK_SIZE: float, fv_yes: float = 0.5) -> dict:
```

### Critical findings

#### 1. Q10 RESOLVED ✅ — `round(x, 3)` is FP safety, not tick

Three places use `round(1.0 - yes_X, 3)` for inverse pricing:

```python
# L4119: derived NO ask from YES bid
derived_no_ask = round(1.0 - yes_bid, 3) if yes_bid > 0 else 0.99

# L4199, L4226: derived NO bid from YES ask
derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01
```

**Reasoning:** `1.0 - 0.55` в Python = `0.4499999...` или `0.4500000001...` (float drift). `round(..., 3)` truncates that drift to predictable value. **Not tick-related.**

**Refactor:** `3` → `self.price_decimals + 1` (extra digit safety buffer).

#### 2. Q15 NEW ⭐ — Tick-calibrated magic floor `0.35`

```python
discount_cents = discount_cents * max(0.35, 1.0 - _il)
# Comment: "floor 0.30→0.35: минимум 1 тик (0.01) дисконта при любом InvL.
# При InvL=1.0: 3.0c × 0.35 = 1.05c → 1 тик ✓. floor<0.33 → discount<1 тика → 0"
```

**This is the most subtle bug for HL refactor!** `0.35` was tuned specifically для PM tick=0.01. На HL это **не гарантирует** "минимум 1 тик дисконта" — формула ломается.

**Refactor:** Use explicit guarantee:
```python
discount_cents = max(self.tick_size, discount_cents * (1.0 - _il))
```

OR derived floor:
```python
min_floor = self.tick_size / 0.030  # ensure ≥ 1 tick after scaling
discount_cents = discount_cents * max(min_floor, 1.0 - _il)
```

#### 3. Q14 STRENGTHENED — `0.02` "2¢ trigger" pattern (2 places now)

```python
# Pass 6: TIME_HEAL start
_healer_start = _fv_side - 0.02

# Pass 8: Mirror activation gap (NEW)
trigger_gap = 0.02  # "Начинаем усреднять при разнице в 2 цента"
if q > 0 and mid_market < (y_avg - trigger_gap) and q >= 3:
    mirror_opportunity = True
```

Both confirmed **absolute "2¢ profit margin"** semantics. Leave hardcoded.

#### 4. Q3 STRENGTHENED — 4 more `0.01` floors confirmed

```python
# L4199: derived_no_bid fallback
derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01

# L4219: YES healer price floor
price_rec_y = max(0.01, min(yes_bid - TICK_SIZE, y_avg - TICK_SIZE, fv_yes + _hl_cap))

# L4229: NO healer price floor
price_rec_n = max(0.01, min(derived_no_bid - TICK_SIZE, n_avg - TICK_SIZE, (1.0 - fv_yes) + _hl_cap))

# L4226: derived_no_bid (re-occurrence)
```

Все 4 — `self.tick_size` after Q3 final resolution (Pass 10).

#### 5. Q2 NUANCE — `0.99` as `1.0 - tick`

```python
derived_no_ask = round(1.0 - yes_bid, 3) if yes_bid > 0 else 0.99
```

`0.99` = `1.0 - self.tick_size` (1 tick from 1.0). Different scale from `0.998 = 1.0 - 2*tick`.

#### 6. NEW config params discovered

- **`recovery_inv_ps_threshold: 0.99`** — healer activation pair-sum threshold (NOT tick)
- **`healer_max_overpay: 0.030`** — max acceptable overpay above FV в healer recovery (absolute, 3¢)

#### 7. Inconsistency: `recovery_discount_cents` defaults

| Code path | Default | Comment |
|---|---|---|
| Pass 6 `_run_toxic_recovery_protocol` | `0.005` | Half-tick at PM |
| Pass 8 `_compute_healer` | `0.050` | Capped to `0.030` after multiplier |

⚠️ Same config name, different defaults. Не refactor concern (already config-driven), но **note for YAML setup** — need to verify which default user actually overrides.

### Findings table (compact)

| # | Line | Code | Cat |
|---|---|---|---|
| 101 | ~4119 | `derived_no_ask = round(1.0 - yes_bid, 3) if yes_bid > 0 else 0.99` | 🟡+🟠 (Q10/Q2) |
| 102 | ~4124 | `inv_ps = y_avg + derived_no_ask` (or `n_avg + yes_ask`) | ⚪ pair-sum |
| 103 | ~4135 | `recovery_inv_ps_threshold: 0.99` default | ⚪ pair-sum |
| 104 | ~4136 | `_discount_base = ... 'recovery_discount_cents', 0.050` | 🟣 (Q11 — Pass 8 default differs from Pass 6!) |
| 105 | ~4137 | `fv_distance = abs(fv_yes - 0.5) * 2.0` | ⚪ FV |
| 106 | ~4138 | `healer_mult = 1.0 + fv_distance * 2.0` | ⚪ formula |
| 107 | ~4140 | `discount_cents = min(... , 0.030)` hard cap | ⚪ absolute |
| 108 | ~4145 | `toxic_threshold = max(0.95, ... - _il * 0.04)` | ⚪ pair-sum + scale |
| 109 | **~4148** | `discount_cents = discount_cents * max(0.35, 1.0 - _il)` | 🟣 (Q15 NEW ⭐ tick-calibrated!) |
| 110 | ~4170 | `trigger_gap = 0.02` | 🟣 (Q14 strengthened) |
| 111 | ~4172 | `if q > 0 and ... q >= 3` | ⚪ shares |
| 112 | **L4185** | `_our_leg_overpriced = (y_avg - mid_market) > TICK_SIZE` | 🟢 |
| 113 | **L4187** | `_our_leg_overpriced = (n_avg - (1.0 - mid_market)) > TICK_SIZE` | 🟢 |
| 114 | **L4199** | `derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01` | 🟡+🟠 (Q10/Q3) |
| 115 | **L4204** | `_closing_leg_available = derived_no_bid >= (_no_baseline - TICK_SIZE)` | 🟢 |
| 116 | **L4208** | `_closing_leg_available = yes_bid >= (_y_baseline - TICK_SIZE)` | 🟢 |
| 117 | **L4215** | `if q > 0 and mid_market < (y_avg - TICK_SIZE):` | 🟢 |
| 118 | ~4216 | `_hl_cap = ... 'healer_max_overpay', 0.030` | ⚪ absolute |
| 119 | **L4219** | `price_rec_y = max(0.01, min(yes_bid - TICK_SIZE, y_avg - TICK_SIZE, fv_yes + _hl_cap))` | 🟢 + Q3 |
| 120 | **L4225** | `elif q < 0 and ((1.0 - mid_market) < (n_avg - TICK_SIZE)):` | 🟢 |
| 121 | **L4226** | `derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01` | 🟡+🟠 (Q10/Q3) |
| 122 | **L4229** | `price_rec_n = max(0.01, min(derived_no_bid - TICK_SIZE, n_avg - TICK_SIZE, (1.0 - fv_yes) + _hl_cap))` | 🟢 + Q3 |

**Pass 8 summary:** 22 findings (101-122). Cumulative: ~122 places identified.

---

## Pass 9 — `_compute_elastic_gravity` ✅ DONE (verified actual code)

### Method signature confirmed (L5424):

```python
def _compute_elastic_gravity(
    self,
    fv_yes: float,
    q: int,
    eff_delta: float,
    dyn_base_deadband: float,
    effective_scale: float,
    p_stress_mult: float,
    heavy_leg: str,
    TICK_SIZE: float,
) -> dict:
```

### Critical findings

#### 1. Q13 RESOLVED ✅ — `0.05` GC gap kill via 5th occurrence (POISON_MATH)

Found третий контекст где `0.05` triggers GC kill warning:

```python
# Pass 9 NEW context — POISON_MATH:
if p_side.get('YES', 0.0) >= 0.05:
    warning(f"🪦☢️ [POISON_MATH] Штраф YES достиг {p_side.get('YES'):.3f} (Гарантированное убийство в GC)")
if p_side.get('NO', 0.0) >= 0.05:
    warning(f"🪦☢️ [POISON_MATH] Штраф NO достиг {p_side.get('NO'):.3f} (Гарантированное убийство в GC)")
```

Combined evidence — `0.05` появляется в 5 places across 3 code paths:
- HEALER_GAP_KILL (Pass 6 x2): `if (_side_bid - healer_price) > 0.05`
- SQUEEZE_DEATH (Pass 7 x2): `if val > 0 and bid > 0 and (bid - val) > 0.05`
- POISON_MATH (Pass 9 x2): `if p_side.get('YES'/'NO', 0.0) >= 0.05`

Все три места имеют **общий semantic** — "5¢ = max distance from market before GC kills order".

**Refactor decision:** Replace hardcoded `0.05` → `5 * self.tick_size` OR config-driven `garbage_dist_base`. На HL tick=0.001 это становится `0.005` (5 ticks) — much tighter GC tolerance.

#### 2. Q16 NEW ⭐ — Gravity penalty cap `0.15`

```python
# After multipliers and FRESH modulation:
p_side[_side] = min(0.15, raw_penalty * asym_factor)
```

Cap value matches:
- `knife_protection_cents=0.15` (TRIAGE_DEATH absolute loss tolerance, Pass 6)
- `max_penalty_dev=0.15` (Pass 2 — penalty fraction)

**`raw_penalty` уже включает TICK_SIZE** (L5472):
```python
raw_penalty = (side_linear_steps ** power) * TICK_SIZE * p_stress_mult
```

На HL tick=0.001, `raw_penalty` natural value 10x smaller. Cap 0.15 effectively becomes irrelevant.

**Refactor:** Per-venue YAML config OR tick-relative `15 * self.tick_size`. См. Phase 3.12.

#### 3. L5472 confirmed verbatim — Central penalty formula

```python
raw_penalty = (side_linear_steps ** power) * TICK_SIZE * p_stress_mult
```

**Penalty уже tick-relative by design.** На HL автоматически 10x smaller. Mechanical replace `TICK_SIZE` → `self.tick_size`.

**Implication:** The strategy's penalty system **scales with venue tick** by default. Это **intentional architecture** — penalties measured в "tick units" rather than absolute money.

#### 4. PAIR_STATE FRESH penalty modulation (NEW finding)

```python
_pair_state = getattr(self, '_pair_state', 'BALANCED')
_closing_side = getattr(self, '_closing_side', None)
if _pair_state == 'FRESH':
    if _side == _closing_side:
        raw_penalty *= 0.3      # closing leg: more aggressive
    else:
        raw_penalty *= 1.5      # opening leg: push away
```

`0.3` / `1.5` multipliers — penalty modulation в FRESH FSM state. **NOT_TICK_RELATED** (formula coefficients).

#### 5. NEW config param: `risk_weight_power: 2.0`

```python
power = getattr(self.config, 'risk_weight_power', 2.0)
```

Power exponent для penalty curve. NOT tick. Could be tunable per venue but architectural, not tick-related.

### ⚠️ Q5/Q7 NOT in this method

`_compute_elastic_gravity` **does NOT use** `edge_min`, `edge_max`, `target_edge`, `cvd_skew_max_cents`, `adaptive_edge`, `edge_vol_sensitivity`. Эти параметры используются в `_compute_spread_and_shield` (Pass 4 confirmed it doesn't take TICK_SIZE).

**Implication for Q5/Q7:** **Architecturally not tick-related** — оперируют через `self.config` без tick arithmetic. **Recommended approach:** per-venue YAML override без code refactor:

```yaml
# Control_Baseline.yaml (PM):
edge_min: 0.015          # 1.5¢ minimum spread
edge_max: 0.050          # 5¢ maximum spread
target_edge: 0.02        # 2¢ target
adaptive_edge: 0.038     # 3.8¢ default

# HL_Test.yaml (HL):
edge_min: 0.0015         # 1.5 ticks
edge_max: 0.005          # 5 ticks
target_edge: 0.002       # 2 ticks
adaptive_edge: 0.0038    # 3.8 ticks
```

### Findings table (compact)

| # | Line | Code | Cat |
|---|---|---|---|
| 123 | ~5435 | `heavy_price = fv_yes if q > 0 else (1.0 - fv_yes)` | ⚪ FV |
| 124 | ~5436 | `raw_price_factor = 1.0 - (heavy_price - 0.5)` | ⚪ formula |
| 125 | ~5437 | `price_factor = max(0.85, min(1.15, raw_price_factor))` | ⚪ bounds |
| 126 | ~5440 | `knife_threshold = 0.025` | ⚪ FV velocity |
| 127 | ~5441 | `vel_panic = 1.5 if is_knife_falling else 1.0` | ⚪ multiplier |
| 128 | ~5455 | `side_deadband * (0.5 if is_weak_leg else 1.0)` | ⚪ fraction |
| 129 | ~5460 | `risk_weight_power: 2.0` default | ⚪ exponent |
| 130 | ~5463 | `_prev_dyn_scale: 25.0` default | ⚪ scale |
| 131 | ~5464 | `aggression_scale = max(10.0, _dyn_inv_scale - abs(_q_eff) * 0.5)` | ⚪ shares |
| 132 | ~5470 | `asym_factor = max(0.5, min(2.0, ...))` | ⚪ bounds |
| 133 | **L5472** | `raw_penalty = (side_linear_steps ** power) * TICK_SIZE * p_stress_mult` | 🟢 ⭐ central |
| 134 | ~5479 | FRESH `raw_penalty *= 0.3 / 1.5` | ⚪ multiplier |
| 135 | **~L5485** | `p_side[_side] = min(0.15, raw_penalty * asym_factor)` | 🟣 (Q16 NEW) |
| 136 | **~L5495** | `if p_side.get('YES', 0.0) >= 0.05: POISON_MATH` | 🟣 (Q13 ✅ resolved) |
| 137 | **~L5500** | `if p_side.get('NO', 0.0) >= 0.05: POISON_MATH` | 🟣 (Q13 ✅ resolved) |

**Pass 9 summary:** 13 findings (123-137). Q13 ✅ RESOLVED, Q16 NEW. Cumulative: ~135 places identified.

---

## Связи

- **Calibration Plan parent:** [[Calibration_Plan]]
- **HL entry point:** [[00_HL_START_HERE]]
- **Strategy map:** [[../strategy_map]]
- **PROJECT_PASSPORT v3.4 tick rule:** [[../PROJECT_PASSPORT]] section 4 `[v3.4]`

---

# 🚧 OUT-OF-SCOPE — что НЕ покрыто tick refactor map

> **Position:** Mechanic markets та же — binary outcomes (Y/N с conditional tokens, Y+N=1), 15-min settlement, FV [0,1] space, pair-sum invariants, healer mirror logic. Strategy logic **полностью переносится** на HL outcomes. **Меняется только платформа** — tick_size меньше + другой SDK.
>
> Этот раздел документирует **integration work** который остаётся **after** tick refactor, но НЕ является tick refactor.

## 1. SDK Adapter Layer (HIGH effort, separate refactor) ⚠️

**Что:** `execution_engine_v6.py` сейчас написан под Polymarket CLOB API:
- `clob_client.create_and_post_order(...)`
- `CreateOrderOptions(tick_size, neg_risk)`
- `clob_client.get_tick_size(tid)` — dynamic tick query
- `condition_id` + `token_id` (YES/NO) ID scheme

**HL API surface:** Hyperliquid Python SDK (`hyperliquid.info`, `hyperliquid.exchange`):
- `exchange.order(coin, is_buy, sz, limit_px, order_type, ...)`
- Different identifier scheme для outcomes (TBD specific HL outcome API)
- Mark price + funding rate как additional market data

**Approach:** Polymorphic adapter pattern с venue dispatch. Strategy unchanged, execution layer abstracted:
```python
class ExecutionAdapter(ABC):
    @abstractmethod
    def place_limit_order(self, side, price, size, ...): ...
    @abstractmethod
    def get_tick_size(self, outcome_id): ...
    @abstractmethod
    def get_outcome_meta(self, outcome_id): ...

class PolymarketAdapter(ExecutionAdapter):  # current execution_engine_v6.py
class HyperliquidAdapter(ExecutionAdapter):  # new, mirrors PM API surface
```

**Mechanics identical** (limit orders, IOC, position tracking). API translation layer.

**Estimated effort:** 8-15 hours (depends on HL SDK familiarity).

**NOTE:** Tick refactor **enables** this adapter to receive correct tick from venue, но НЕ создает adapter сам.

## 2. Symbol / Outcome ID Resolution (MEDIUM effort)

**Что:** Strategy expects PM-style identifiers:
- `condition_id` (market-level)
- `token_id_yes`, `token_id_no` (outcome-level)

**HL outcome markets** возможно используют другой ID scheme. Нужен mapping layer:
- HL outcome listing API → discovery
- HL outcome ID → strategy's `(condition_id, token_id_yes, token_id_no)` triplet

**Mechanics identical** (binary outcome with two tokens). Just ID translation.

**Estimated effort:** 3-5 hours после понимания HL outcome API.

## 3. MIN_LOT / MIN_NOTIONAL Per-Venue (Phase 4 — separate refactor)

**Что:** `grid_manager.py:69` имеет `MIN_LOT = 5`, `MIN_NOTIONAL = 1.00` hardcoded.

**HL:** values приходят из `outcomeMeta` API per-outcome (могут быть разные для разных markets).

**Approach:** Move to GridConfig + per-outcome dynamic load:
```python
@dataclass
class GridConfig:
    min_lot_default: int = 5            # fallback
    min_notional_default: float = 1.00  # fallback

# At outcome init time:
meta = adapter.get_outcome_meta(outcome_id)
self.min_lot = meta.get('min_lot', self.config.min_lot_default)
self.min_notional = meta.get('min_notional', self.config.min_notional_default)
```

**Already noted в documente** как Phase 4 separate refactor track.

**Estimated effort:** 2-3 hours.

## 4. Per-Venue YAML Calibration (LOW effort, MEDIUM risk)

**Что:** Tick refactor unlocks `tick_size` config, но **edge params** (`edge_min`, `target_edge`, `adaptive_edge_default`, `cvd_skew_max_cents`, `garbage_dist_base`, `max_adaptive_edge`) — architecturally **не tick-aware** (НЕ оперируют через TICK_SIZE arithmetic).

**Risk:** На HL без правильного YAML override strategy будет **тихо мисбехавит** — quoting 15 ticks wide spread вместо intended 1.5. Не throws errors. Silent EV leak.

**Approach:** Explicit `HL_Test.yaml` с scaled defaults (Step 0.3 в documente lists it).

**Mechanics identical** — strategy treats edge params одинаково на обеих venues. Just numerical scaling.

**Estimated effort:** 1 hour (если у нас есть HL data для proper calibration). 4-8 hours (если нужна fresh calibration round на HL data).

## 5. Pending Q-resolutions (LOW effort)

| Q# | Pending | Effort |
|---|---|---|
| Q1 | `< 0.03` token floor — verify absolute | 15 min (read context) |
| Q11 remaining | `0.005` places at L394, L3098, L6368 — context reads | 30 min |
| Q12 | `0.001` places verify likely absolute | 15 min |
| Q14 final | `0.02` trigger gap consistency decision | 15 min |
| `edge_vol_sensitivity` | L214 — coefficient or tick-rel | 15 min |
| `recovery_discount_cents` inconsistency | Pass 6 default 0.005 vs Pass 8 default 0.050 — verify which YAML overrides | 15 min |

**Total:** ~2 hours.

## 6. Q15 / Q16 Implementation Decisions (MEDIUM effort)

**Q15 (`0.35` magic floor):** Refactor approach documented (Phase 3.10), но не implemented. Two options listed; user must choose:
- Option A: explicit guarantee `discount = max(self.tick_size, ...)` (cleaner)
- Option B: derived floor `min_floor = self.tick_size / 0.030` (preserves current scaling)

**Recommended:** Option A. Cleaner, removes tick-calibrated magic.

**Q16 (`0.15` penalty cap):** Phase 3.12 lists Option A (per-venue YAML config) vs Option B (tick-relative `15 * self.tick_size`). Decision needed.

**Recommended:** Option A — explicit YAML config `gravity_penalty_cap` per venue.

**Estimated effort:** 1 hour decision + 1 hour testing.

## 7. Detection / Runtime Validation (LOW effort)

**Что:** Document provides `_validate_tick_alignment` runtime validator code в Detection strategy section. Not implemented.

**Where to add:** End of `_apply_maq_filter` (after L3291-3292 final quantization). Catches любые missed quantization places по runtime.

**Estimated effort:** 30 min.

## 8. Smoke Test Framework (LOW effort)

**Что:** Order of operations Step 9-10:
- Smoke test PM tick=0.01 — should be **bit-identical** к pre-refactor PM behavior
- Smoke test HL tick=0.001 — observe new behavior, validate fills happen на correct tick boundaries

**Approach:** Run identical paper session pre/post refactor on PM, diff order placements. Should be zero diffs (config tick_size=0.01 should yield identical behavior).

**Estimated effort:** 2-3 hours setup + 4-6 hours observation.

## 9. HL Infrastructure Readiness Verification (BLOCKING — not code work)

**Что:** Tick refactor unlocks **code-level** multi-venue. Actual HL deployment requires:
- Confirm HL **15-min binary outcomes available** (was broken on testnet HYPE per prev paused state)
- Confirm HL outcome markets **liquid enough** для market making strategy (≥ ~$100 daily volume per outcome)
- Confirm HL **outcomeMeta API** возвращает tick_size + min_lot + min_notional per outcome
- Confirm HL **funding rate impact** на outcome pricing (если HL outcomes settle через perpetual mechanism vs spot binary)

**Mechanics:** Same binary Y/N outcomes на HL — это user's confirmation. Refactor этим займётся как только infrastructure ready.

**Effort:** Discovery work, не coding. ~2-4 hours verification cycle.

## 10. Calibration Round on HL Data (NORMAL workflow, не refactor)

**Что:** После tick refactor + adapter + YAML override, strategy будет работать на HL syntactically. Но parameters tuned для PM markets могут needing minor recalibration на HL data:
- Spread tuning (`edge_min`, `target_edge`) — based on HL spread distribution
- Recovery discount (`recovery_discount_cents`) — based on HL toxic flow patterns
- GC distance (`garbage_dist_base`) — based on HL orderbook depth
- MAQ thresholds — based on HL fee structure

**This is EXPECTED normal calibration workflow** — same like calibrating new market type на PM. Не considered tick refactor.

**Mechanics identical**. Just numerical tuning.

**Estimated effort:** 4-8 hours (paper testing + parameter sweeps).

---

## Out-of-scope effort estimate (summary)

| Item | Effort | Risk |
|---|---|---|
| 1. SDK Adapter | 8-15h | HIGH (architectural) |
| 2. Symbol/Outcome ID | 3-5h | MEDIUM |
| 3. MIN_LOT/MIN_NOTIONAL | 2-3h | LOW |
| 4. Per-Venue YAML | 1-8h | MEDIUM (silent leak risk) |
| 5. Pending Q-resolutions | 2h | LOW |
| 6. Q15/Q16 implementation | 2h | MEDIUM |
| 7. Detection validator | 30min | LOW |
| 8. Smoke tests | 6-9h | LOW |
| 9. HL infra verification | 2-4h | BLOCKING (external) |
| 10. HL calibration | 4-8h | NORMAL workflow |
| **TOTAL out-of-scope** | **30-56h** | — |
| **Tick refactor itself (in-scope)** | **10-12h** | LOW-MEDIUM |
| **GRAND TOTAL для full HL deployment** | **40-68h** | — |

## Critical path for HL deployment

```
1. HL outcome markets available  [BLOCKING — external]
        ↓
2. Tick refactor (this document) [10-12h]
        ↓
3. SDK Adapter for HL            [8-15h]
        ↓
4. Symbol/Outcome ID mapping     [3-5h]
        ↓
5. Per-venue YAML setup          [1-8h]
        ↓
6. Smoke test PM (regression)    [2-3h]
        ↓
7. Paper test HL                 [4-8h]
        ↓
8. HL calibration tuning         [4-8h ongoing]
```

## What stays IDENTICAL between PM and HL

> **Confirmation:** Mechanic markets та же. Strategy logic переносится **as-is**.

| Aspect | PM | HL | Same? |
|---|---|---|---|
| Binary outcomes (Y/N) | ✅ conditional tokens | ✅ outcome markets | ✅ |
| Pair-sum invariant (Y+N=1) | ✅ | ✅ | ✅ |
| FV space [0,1] | ✅ probability | ✅ probability | ✅ |
| 15-min binary settlement | ✅ | ✅ (after launch) | ✅ |
| Healer mirror (derived_no_X = 1.0 - yes_X) | ✅ valid | ✅ valid | ✅ |
| DCS_KILL FV poles | ✅ | ✅ | ✅ |
| Pair-sum gates (0.985, 0.995, 1.005, 1.03) | ✅ | ✅ | ✅ |
| Hunter / Healer / Toxic Recovery FSM | ✅ | ✅ | ✅ |
| GLFT reservation pricing (simple_strategy) | ✅ | ✅ | ✅ |
| Strategy parameters (with calibration) | ✅ tuned | ⚠️ needs HL retune | similar mechanics |

**Что меняется:**
- Tick size: 0.01 → 0.001 (or whatever HL gives)
- SDK API surface (adapter layer)
- Identifier scheme (outcome ID mapping)
- Some hardcoded magic constants (Q15, Q16 — calibration leaks, not strategy logic)

**Что НЕ меняется:**
- Strategy decision tree
- Risk management logic
- Pricing FSM (Hunter/Healer/Recovery)
- Pair-sum economic invariants
- Calibration approach (paper testing → tune → deploy)

## Conclusion

Tick refactor этого документа покрывает **~25-30% полной HL deployment work**, но это **самая критичная** часть — без неё ничего другое не работает correctly.

После tick refactor + SDK adapter + YAML calibration — strategy будет работать на HL **с такой же performance** как на PM (modulo normal calibration cycle для нового market data).

**Mechanics identical. Refactor это chiefly о синтаксической adaptation платформы, не strategy redesign.**
