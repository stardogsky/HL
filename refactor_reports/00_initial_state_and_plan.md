# HL Refactor — Initial State + Plan

**Date:** 2026-05-13 18:03 UTC
**Trigger:** User goal — refactor HL bot per docs, key goals: pair_sum≤$1, max volume, balanced inventory for positive EV.

## Initial state snapshot

| Component | State |
|---|---|
| `hl_collector` | RUNNING (clean, ~7 days uptime) |
| `hl_feeder` | RUNNING but **STALE** — `OUTCOME_ID=5` hardcoded, current active = **35** (30 outcomes missed since 2026-05-08) |
| `bot_HL_Test` | RUNNING but **WAITING** (no data after feeder freeze) |
| Total fills lifetime | 51 (frozen ~5 days ago) |
| Lifetime cancels | 552 (CFR 10.8:1) |
| Live PnL | unknown — last known +$1.79 at outcome 3 (paper run #1) |

**Current mainnet outcome 35:**
- Underlying: BTC daily
- Expiry: 2026-05-14 06:00 UTC (~12h from now)
- Target: $80,983
- Current BTC: ~$79,158 (below target → NO is leading)

## Strategy alignment with user goals

| Goal | Strategy current state | Gap |
|---|---|---|
| Pair sum ≤ $1 | `profit_gate_ps_max=0.990` for HL (≤ $0.99 lock) | None — invariant intact |
| Max volume | Strategy quotes 4-level grids both sides | Tick mismatch (0.01 PM vs 0.00001 HL) → coarse quotes → fewer fills |
| Inventory balance | Hunter/Healer FSM works venue-agnostic | DCS_KILL filter active (works) |
| Pair merge mechanism | PM has CTF merge; HL HIP-4 outcome markets have **automatic settlement** (no merge tx) | Different mechanism — HL pays out at expiry, no in-flight merge |

**Critical insight:** HL pays out at settlement, not via merge transaction. So "merge cost" parameters (`min_merge_size`, `merge_lock_sec`, `merge_cooldown_sec`) are PM-specific. On HL these don't apply — bot just holds to expiry.

## Refactor sequence (decision: tick refactor NOW)

**Rationale:**
- Tick refactor is documented as **low risk** (config-driven, doesn't break PM)
- 155+ places already identified with file:line precision in `Tick_Size_Refactor_Audit.md`
- Bot stale = no risk of running interference — restart inevitable
- Quick wins give immediate improvement

**Execution plan:**

### Phase 0a — Revive feeder (5 min, blocking)
- Patch `OUTCOME_ID=5` → `OUTCOME_ID=35` in `hl_feeder.py`
- Restart `hl_feeder` and `bot_HL_Test`
- Verify pipeline alive (orderbook + trade messages flowing)

### Phase 0b — YAML quick wins (15 min)
- `market_duration_sec: 86400` (HL daily)
- `tick_size: 0.00001` (new field)
- Per-venue scaled defaults: `edge_min`, `target_edge`, `garbage_dist_base`, etc. (per Tick_Size_Refactor_Audit Step 0.3)

### Phase 1 — Config plumbing (30 min)
- `GridConfig` dataclass: add `tick_size`, `min_lot`, `min_notional`
- `GridStrategy.__init__`: introduce `self.tick_size`, `self.price_decimals`
- `GridManager`: accept `tick_size` param

### Phase 2 — Mechanical replacements (60 min)
- `TICK_SIZE` constant → `self.tick_size` in ~30 places
- `round(x, 2)` → `round(x, self.price_decimals)` in ~9 places

### Phase 3 — Hardcoded value resolution (90 min)
- `0.01` floors → `self.tick_size` (~51 places, Q3 resolved)
- `0.998` ceilings → `1.0 - 2*self.tick_size` (~7 places, Q2 resolved)
- `0.99` fallback → `1.0 - self.tick_size`
- `0.05` GC kills → `5 * self.tick_size` (~5 places, Q13)
- `0.35` magic floor → `max(tick_size, ...)` (Q15)
- `adaptive_edge` 0.038 → config-driven

### Phase 4 — Smoke test PM (15 min)
- Restart 3 PM anchors, verify bit-identical behavior
- 99 Hunter tests must still pass
- gabagool tests: 29 pre-existing fails must remain unchanged

### Phase 5 — Deploy HL (10 min)
- Restart `bot_HL_Test` with new code + calibrated config
- Verify quotes generated, fills happening
- 30-min observation, report

### Phase 6 — Forward observation (24-48h passive)
- Track WR, realized_ps, max_q distribution
- Compare to paper run #1 baseline (+$1.79/16h)

## Reports plan

Each phase produces a report in `/home/moltbot/HL/refactor_reports/`:
- `00_initial_state_and_plan.md` (this file)
- `01_phase0a_feeder_revive.md`
- `02_phase0b_yaml_quickwins.md`
- `03_phase1_config_plumbing.md`
- `04_phase2_mechanical_replacements.md`
- `05_phase3_hardcoded_values.md`
- `06_phase4_pm_smoke_test.md`
- `07_phase5_hl_deployment.md`
- `08_phase6_observation_results.md` (after 1-2h observation minimum)

## Key risks identified

1. **TICK_SIZE in PM code** — must remain config-driven so PM stays bit-identical at 0.01
2. **HL pair-merge mismatch** — `min_merge_size=9999` in HL_Test.yaml effectively disables merge logic (good, HL doesn't merge)
3. **TICK_SIZE shadow at L1209** — local variable in `on_tick` masks instance attr. Must remove.
4. **`adaptive_edge=0.038` hardcoded** — PM-tuned, will be 38 ticks on HL (way too wide)

## Estimated total time

8-10 hours active work + 30 min verification per phase. Will compress by deploying iteratively.
