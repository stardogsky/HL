# Code Map — Summary
_Generated: 20260504_174247 UTC_

## Counts
- Total files: **483**
- Total lines: **116,943**

## Distribution by classification

| Label | Count | Lines | What it means |
|---|---|---|---|
| PLATFORM | 253 | 84,208 | 🔴 точно менять для multi-venue (есть Polymarket-specific код) |
| TRANSPORT | 114 | 27,677 | 🟡 границы transport-слоя — обернуть в abstraction |
| CORE | 37 | 4,257 | 🟢 pure logic — оставлять как есть или минимально |
| UTIL | 79 | 801 | ⚪ utility — обычно platform-agnostic |

## Top 15 hubs (files imported by many others)
Critical mass = if you change them, lots of code rebreaks.

| File | Imported by | Label |
|---|---|---|
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/types.py` | 26 | PLATFORM |
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/client.py` | 23 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/bankroll_manager.py` | 21 | PLATFORM |
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/models.py` | 20 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/order_logger.py` | 19 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/phase_manager.py` | 18 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/backtester/models/queue_aware.py` | 17 | TRANSPORT |
| `archive/hesoyam_with_fill_rate_limits/backtester/models/base.py` | 16 | CORE |
| `archive/hesoyam_with_fill_rate_limits/backtester/core/orderbook_replay.py` | 15 | TRANSPORT |
| `archive/hesoyam_with_fill_rate_limits/backtester/core/engine.py` | 13 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/backtester/strategy/strategy_sim.py` | 13 | PLATFORM |
| `backtester/optimizer/param_space.py` | 13 | TRANSPORT |
| `archive/hesoyam_with_fill_rate_limits/tbot_logger/orderbook_logger.py` | 12 | PLATFORM |
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/core.py` | 12 | PLATFORM |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/order_pricer.py` | 12 | TRANSPORT |

## 🔴 PLATFORM files (must refactor for multi-venue)
Sorted by Polymarket-coupling intensity.

| File | Lines | Platform hits | Constants | Top keywords |
|---|---|---|---|---|
| `strategies/gabagool/grid_strategy.py` | 7029 | 351 | 3 | CTF, MIN_MKT_LOT, condition_id, ctf |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/gabagool_strat.py` | 2210 | 164 | 2 | condition_id, no_ask, no_bid, no_shares |
| `strategies/gabagool/gabagool_strat.py` | 2437 | 164 | 2 | condition_id, no_ask, no_bid, no_shares |
| `archive/mag_knowledge/legacy/Well start here/poly_claim/ctf_core.py` | 1364 | 137 | 0 | CTF, GNOSIS, condition_id, ctf |
| `archive/hesoyam_with_fill_rate_limits/tbot_integration/bvmm_strategy.py` | 741 | 78 | 0 | no_ask, no_bid, no_shares, polymarket |
| `tbot_integration/bvmm_strategy.py` | 741 | 78 | 0 | no_ask, no_bid, no_shares, polymarket |
| `tbot_integration/grid_adapter.py` | 1287 | 64 | 0 | condition_id, no_ask, no_bid, no_shares |
| `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/client.py` | 1044 | 51 | 0 | condition_id, token_id |
| `archive/dead_2026-03-04/grid_adapter.py` | 658 | 45 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `scripts/claim_resolved.py` | 707 | 43 | 0 | CTF, condition_id, ctf, no_shares |
| `backtester/strategy/position_tracker.py` | 266 | 42 | 0 | no_shares, yes_shares |
| `strategies/gabagool/live_trading_bridge.py` | 1046 | 37 | 0 | condition_id, no_ask, no_bid, no_shares |
| `backtester/strategy/grid_strategy_sim.py` | 458 | 36 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `strategies/gabagool/strategy_adapter.py` | 2321 | 35 | 0 | condition_id, no_shares, polygon, polymarket |
| `tbot_integration/strategy_adapter.py` | 2331 | 35 | 0 | condition_id, no_shares, polygon, polymarket |
| `archive/dead_2026-03-04/tbot_core_blockchain/ctf_client.py` | 327 | 34 | 0 | CTF, condition_id, ctf, polygon |
| `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/opportunity_evaluator.py` | 717 | 34 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `archive/hesoyam_with_fill_rate_limits/tbot_core/blockchain/ctf_client.py` | 327 | 34 | 0 | CTF, condition_id, ctf, polygon |
| `strategies/gabagool/opportunity_evaluator.py` | 717 | 34 | 0 | no_ask, no_bid, no_shares, yes_ask |
| `backtester/strategy/strategy_sim.py` | 1228 | 32 | 0 | no_shares, yes_shares |
| `dashboard/server.py` | 1141 | 29 | 0 | condition_id, no_shares, yes_shares |
| `tbot_integration/live_trading_bridge.py` | 1767 | 29 | 0 | CTF, condition_id, ctf, no_shares |
| `archive/hesoyam_with_fill_rate_limits/backtester/strategy/position_tracker.py` | 196 | 28 | 0 | no_shares, yes_shares |
| `archive/dead_2026-03-04/ws_implementation_code.py` | 983 | 27 | 0 | condition_id, polymarket, token_id |
| `archive/hesoyam_with_fill_rate_limits/tbot_integration/strategy_adapter.py` | 2027 | 26 | 0 | condition_id, no_shares, polygon, polymarket |

## 🟡 TRANSPORT files (boundaries to abstract)

| File | Lines | Transport hits | Imports |
|---|---|---|---|
| `archive/hesoyam_with_fill_rate_limits/scripts/health_check.py` | 432 | 54 |  |
| `scripts/health_check.py` | 432 | 54 |  |
| `backtester/reporting/funnel_report.py` | 337 | 40 |  |
| `backtester/optimizer/param_space.py` | 824 | 34 |  |
| `unified_analysis.py` | 658 | 27 |  |
| `backtester/optimizer/optuna_optimizer.py` | 1318 | 26 |  |
| `archive/optimizer/angel_optimizer.py` | 659 | 22 |  |
| `monitor.py` | 116 | 18 | zmq |
| `analysis/views/leaderboard.py` | 155 | 17 |  |
| `data_gateway.py` | 261 | 16 | zmq, zmq.asyncio |
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/market/analyzer.py` | 234 | 13 |  |
| `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_risk/limits.py` | 178 | 13 |  |
| `archive/dead_2026-03-04/tbot_core_market/analyzer.py` | 234 | 13 |  |
| `archive/hesoyam_with_fill_rate_limits/tbot_core/market/analyzer.py` | 234 | 13 |  |
| `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/market/analyzer.py` | 234 | 13 |  |

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