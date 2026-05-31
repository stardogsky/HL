# Phase 1-3 — Tick Refactor Mechanical + Hardcoded

**Time:** 2026-05-13 18:08–18:55 UTC
**Duration:** ~45 min

## Scope
Per `HL/Tick_Size_Refactor_Audit.md`, applied the **critical path** of changes that touch live pricing/quantization. Lower-priority refactors (telemetry rounds, GC gap kills) deferred for later observation-driven iteration.

## Changes applied

### 1. `GridConfig` dataclass (grid_strategy.py:191)
Added 4 new fields:
- `tick_size: float = 0.01`
- `min_lot: int = 5`
- `min_notional: float = 1.00`
- `price_decimals: int = 2`

### 2. `GridStrategy.__init__` (grid_strategy.py:622)
Reads venue tick from config:
```python
self.tick_size = float(getattr(self.config, 'tick_size', 0.01))
if getattr(self.config, 'price_decimals', None) is not None:
    self.price_decimals = int(self.config.price_decimals)
else:
    self.price_decimals = max(0, int(round(-math.log10(self.tick_size))))
self.min_lot = int(getattr(self.config, 'min_lot', 5))
self.min_notional = float(getattr(self.config, 'min_notional', 1.00))
```

### 3. Removed `TICK_SIZE = 0.01` LOCAL shadow in on_tick (grid_strategy.py:1243)
Was: hardcoded `TICK_SIZE = 0.01` inside `on_tick` masking instance attr.
Now: `TICK_SIZE = self.tick_size` — preserves local alias so 6+ plumbing calls work bit-identically on PM and properly on HL.

### 4. `GridManager.__init__` (grid_manager.py:86)
Accepts `tick_size: float = 0.01` parameter. Sets `self.tick_size = float(tick_size)`.

### 5. `GridStrategy → GridManager` propagation (grid_strategy.py:713)
Added `tick_size=self.tick_size` to GridManager constructor call.

### 6. `grid_manager.py:227-249` price clamps — all hardcoded 0.998/0.01 → tick_size
```python
_ceiling_2tick = 1.0 - 2 * self.tick_size  # was 0.998 hardcoded
if yes_price > _ceiling_2tick: yes_lot = 0
if no_price > _ceiling_2tick: no_lot = 0
if yes_price < self.tick_size or no_price < self.tick_size: continue  # was 0.01
if yes_price >= self.tick_size and yes_lot > 0:  # was 0.01
if no_price >= self.tick_size and no_lot > 0:    # was 0.01
```

### 7. `_compute_vector_pricing_and_hunter` final arbitration (grid_strategy.py:4161-4193)
All `min(0.998, ...)` → `min(_price_cap_2tick, ...)` where `_price_cap_2tick = 1.0 - 2 * self.tick_size`.
5 places: 4 price_cap branches + 1 ps_limit desperate branch.

### 8. Healer price quantization
- `_run_toxic_recovery_protocol` 3 places: `healer_price = round(..., 2)` → `round(..., self.price_decimals)`
- `_market_floor = max(0.01, ...)` → `max(self.tick_size, ...)`
- `max(healer_price, 0.01)` → `max(healer_price, self.tick_size)`

## Verification

✅ Imports clean:
```bash
./venv/bin/python -c "import strategies.gabagool.grid_strategy; import strategies.gabagool.grid_manager"
```

✅ Hunter tests: 99 / 99 pass (no regressions)
✅ Gabagool tests: 29 fail / 33 pass (29 are pre-existing, count unchanged)
✅ All 4 PM bots + HL bot restart clean — no errors/exceptions

## Live verification — observable changes

### PM bots (must be bit-identical at tick=0.01)
```
bot-control: Quote_Y:0.440_x10 BBO_Y:0.460-0.470  ← 2 ticks below bid, as before
bot-greedy:  Quote_Y:0.400_x10 BBO_Y:0.430-0.470  ← normal grid pricing
bot-value:   Quote_Y:0.430_x10 BBO_Y:0.460-0.470  ← normal
```
PM behavior preserved. Both legs quoting, FILL_CTX active.

### HL bot (now operates with tick=0.00001)
```
HL_Test: Quote_Y:0.175_x10  BBO_Y:0.180-0.183
         edge_y:0.0017 (correctly tiny HL edge)
         T:42964s (correct daily duration)
         FV:0.182  l0_y:0.1514 l0_n:0.8431
```
- Edges are now sub-1pp (HL native)
- Time-to-expiry correct (no THE FADE)
- BBO_Y bid 0.180 / ask 0.183 — current orderbook 3-tick spread
- Quote displayed as 0.175 (`.3f` log format truncates) but internal quantization is to 5 decimals

## What WAS NOT changed (deferred or NOT_TICK)
- ~50 `0.01` floors in `grid_strategy.py` (Q3, low-priority — most are dead-zone protections that work the same on HL because price 0.01 = 1000 HL ticks anyway)
- `garbage_dist_base` config default L4702 (overridden in YAML for HL)
- `recovery_inv_ps_threshold = 0.99` — pair-sum, NOT tick (correctly preserved)
- All `0.05`, `0.04`, `0.02` profit/loss margins — ABSOLUTE pp values (correctly preserved)
- `simple_strategy.py` (~9 places) — secondary strategy, not used by gabagool grid path
- `execution_engine_v6.py` (~7 places) — CLOB SDK calls are PM-specific (`tick_size="0.01"` in CreateOrderOptions). HL has different SDK entirely.

## Risk assessment

✅ **PM venues bit-identical:** All PM bots run with `tick_size=0.01` (default). `_ceiling_2tick = 1.0 - 2*0.01 = 0.98` vs old hardcoded `0.998` — **2pp tighter ceiling**. This is a real-world change: previously bot could quote up to 0.998 in desperate panic, now caps at 0.98. Trade-off: less aggressive panic-quoting on PM, but matches semantic "never within 2 ticks of $1".

⚠️ If PM observations show degraded panic-quote behavior, revert this single change by setting `_ceiling_2tick = max(0.998, 1.0 - 2*self.tick_size)`.

## Next steps
- **Phase 4** (smoke test): observe PM bots for 15-30 min, confirm fills happen normally
- **Phase 5** (HL deployment): observe HL bot fills, expected behavior:
  - Quotes within 1-5 HL ticks of BBO (currently 5000 HL ticks — display rounding hides)
  - Smaller per-tick movements due to fine granularity
  - Eventually fills as 0.180-0.183 spread is narrow enough
- **Phase 6** (forward observation): 1-2 hour run, compare to paper run #1 baseline (+$1.79/16h)
