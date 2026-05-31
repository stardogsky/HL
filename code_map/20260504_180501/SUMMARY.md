# Code Map — Summary
_Generated: 20260504_180501 UTC_

## Counts
- Total files: **162**
- Total lines: **57,573**

## Distribution by classification

| Label | Count | Lines | What it means |
|---|---|---|---|
| PLATFORM | 67 | 40,540 | 🔴 точно менять для multi-venue (есть Polymarket-specific код) |
| TRANSPORT | 53 | 14,547 | 🟡 границы transport-слоя — обернуть в abstraction |
| CORE | 14 | 2,209 | 🟢 pure logic — оставлять как есть или минимально |
| UTIL | 28 | 277 | ⚪ utility — обычно platform-agnostic |

## Top 15 hubs (files imported by many others)
Critical mass = if you change them, lots of code rebreaks.

| File | Imported by | Label |
|---|---|---|
| `backtester/optimizer/param_space.py` | 13 | TRANSPORT |
| `strategies/gabagool/order_logger.py` | 12 | PLATFORM |
| `strategies/gabagool/bankroll_manager.py` | 11 | PLATFORM |
| `tbot_core/strategy/types.py` | 10 | PLATFORM |
| `backtester/models/base.py` | 9 | CORE |
| `strategies/gabagool/phase_manager.py` | 9 | PLATFORM |
| `backtester/models/queue_aware.py` | 8 | TRANSPORT |
| `backtester/core/orderbook_replay.py` | 7 | TRANSPORT |
| `backtester/core/engine.py` | 6 | PLATFORM |
| `backtester/strategy/strategy_sim.py` | 6 | PLATFORM |
| `strategies/gabagool/grid_strategy.py` | 6 | PLATFORM |
| `strategies/gabagool/order_pricer.py` | 6 | TRANSPORT |
| `backtester/strategy/grid_strategy_sim.py` | 5 | PLATFORM |
| `backtester/optimizer/param_space_v6.py` | 5 | TRANSPORT |
| `strategies/gabagool/grid_manager.py` | 5 | PLATFORM |

## 🔴 PLATFORM files (must refactor for multi-venue)
Sorted by Polymarket-coupling intensity.

| File | Lines | Platform hits | Constants | Top keywords |
|---|---|---|---|---|
| `strategies/gabagool/grid_strategy.py` | 7029 | 351 | 3 | CTF, MIN_MKT_LOT, condition_id, ctf |
| `strategies/gabagool/gabagool_strat.py` | 2437 | 164 | 2 | condition_id, no_ask, no_bid, no_shares |
| `tbot_integration/bvmm_strategy.py` | 741 | 78 | 0 | no_ask, no_bid, no_shares, polymarket |
| `tbot_integration/grid_adapter.py` | 1287 | 64 | 0 | condition_id, no_ask, no_bid, no_shares |
| `scripts/claim_resolved.py` | 707 | 43 | 0 | CTF, condition_id, ctf, no_shares |
| `backtester/strategy/position_tracker.py` | 266 | 42 | 0 | no_shares, yes_shares |
| `strategies/gabagool/live_trading_bridge.py` | 1046 | 37 | 0 | condition_id, no_ask, no_bid, no_shares |
| `backtester/strategy/grid_strategy_sim.py` | 458 | 36 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `strategies/gabagool/strategy_adapter.py` | 2321 | 35 | 0 | condition_id, no_shares, polygon, polymarket |
| `tbot_integration/strategy_adapter.py` | 2331 | 35 | 0 | condition_id, no_shares, polygon, polymarket |
| `strategies/gabagool/opportunity_evaluator.py` | 717 | 34 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `backtester/strategy/strategy_sim.py` | 1228 | 32 | 0 | no_shares, yes_shares |
| `dashboard/server.py` | 1141 | 29 | 0 | condition_id, no_shares, yes_shares |
| `tbot_integration/live_trading_bridge.py` | 1767 | 29 | 0 | CTF, condition_id, ctf, no_shares |
| `strategies/gabagool/results_tracker.py` | 580 | 25 | 0 | condition_id, no_shares, polymarket, yes_shares |
| `strategies/gabagool/lot_sizer.py` | 578 | 24 | 0 | no_shares, yes_shares |
| `strategies/gabagool/bankroll_manager.py` | 657 | 22 | 0 | no_shares, yes_shares |
| `replayer.py` | 575 | 20 | 0 | no_ask, no_bid, total_no, total_yes |
| `tbot_risk/guards.py` | 277 | 20 | 0 | no_shares, yes_shares |
| `backtester/optimizer/profiles_v6_calibrated.py` | 608 | 0 | 19 |  |
| `tbot_core/api/ws_client.py` | 364 | 19 | 0 | condition_id, polymarket, token_id |
| `strategies/gabagool/rebalancer.py` | 444 | 18 | 0 | no_shares, yes_shares |
| `tbot_core/strategy/enhanced_bvmm.py` | 284 | 18 | 0 | no_ask, no_bid, yes_ask, yes_bid |
| `dashboard/microstructure/tape_renderer.py` | 203 | 17 | 0 | condition_id, no_ask, no_bid, yes_ask |
| `tbot_core/api/models.py` | 294 | 17 | 0 | no_shares, polymarket, yes_shares |

## 🟡 TRANSPORT files (boundaries to abstract)

| File | Lines | Transport hits | Imports |
|---|---|---|---|
| `scripts/health_check.py` | 432 | 54 |  |
| `backtester/reporting/funnel_report.py` | 337 | 40 |  |
| `backtester/optimizer/param_space.py` | 824 | 34 |  |
| `unified_analysis.py` | 658 | 27 |  |
| `backtester/optimizer/optuna_optimizer.py` | 1318 | 26 |  |
| `monitor.py` | 116 | 18 | zmq |
| `analysis/views/leaderboard.py` | 155 | 17 |  |
| `data_gateway.py` | 261 | 16 | zmq, zmq.asyncio |
| `tbot_risk/limits.py` | 178 | 13 |  |
| `tbot_logger/poly_orderbook_swarm.py` | 503 | 12 | aiohttp |
| `backtester/optimizer/tier_inheritance.py` | 376 | 11 |  |
| `scripts/analyze_fanova.py` | 347 | 11 |  |
| `backtester/optimizer/lhs_screening.py` | 697 | 10 |  |
| `backtester/scripts/hard_mode_autopsy.py` | 266 | 10 |  |
| `tbot_core/strategy/optimizer.py` | 173 | 10 |  |

---

## Architectural recommendations

1. **Files marked PLATFORM** — твой список «что точно менять» при multi-venue. Открой `polymarket_specific.md` для конкретных строк.
2. **Files marked TRANSPORT** — поверхность для abstraction. Создавай `BridgeAdapter` interface, эти файлы общаются через него.
3. **Top hubs** — менять в последнюю очередь. Чем больше importers, тем больше тестов прогонять.
4. **CORE files** — большинство можно оставить нетронутым. Но проверить `polymarket_specific.md` — иногда хардкод проникает в CORE через имена методов.

См. также:
- `import_graph.md` — полный граф зависимостей
- `polymarket_specific.md` — все строки с platform-coupling
- `transport_boundary.md` — все I/O границы
- `class_inventory.md` — все классы