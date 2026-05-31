# Class Inventory

Все классы кодовой базы — где определены и где используются.

| Class | Defined in | File label |
|---|---|---|
| `ASPricer` | `strategies/gabagool/as_pricer.py` | PLATFORM |
| `ASPrices` | `strategies/gabagool/as_pricer.py` | PLATFORM |
| `Aggressiveness` | `strategies/gabagool/phase_manager.py` | PLATFORM |
| `AlphaSignal` | `analysis/signals/alpha_signals.py` | PLATFORM |
| `AnalysisContext` | `analysis/signals/alpha_signals.py` | PLATFORM |
| `ApiCredentials` | `tbot_core/api/signing.py` | PLATFORM |
| `BBODistanceDist` | `tbot_integration/core/metrics.py` | CORE |
| `BVMMStrategy` | `tbot_integration/bvmm_strategy.py` | PLATFORM |
| `BacktestConfig` | `backtester/strategy/strategy_sim.py` | PLATFORM |
| `BankrollConfig` | `strategies/gabagool/bankroll_manager.py` | PLATFORM |
| `BankrollManager` | `strategies/gabagool/bankroll_manager.py` | PLATFORM |
| `BookLevel` | `tbot_core/strategy/types.py` | PLATFORM |
| `BotData` | `tbot_integration/core/parser.py` | PLATFORM |
| `CapacityCrushRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `ChronosStream` | `replayer.py` | PLATFORM |
| `CompletedEpoch` | `tbot_integration/core/epoch_tracker.py` | PLATFORM |
| `DataGateway` | `data_gateway.py` | TRANSPORT |
| `DualCoreDefense` | `strategies/gabagool/grid_strategy.py` | PLATFORM |
| `EdgeStats` | `tbot_integration/core/metrics.py` | CORE |
| `EnhancedBVMM` | `tbot_core/strategy/enhanced_bvmm.py` | PLATFORM |
| `EnhancedOrderbookLogger` | `tbot_logger/enhanced_logger.py` | TRANSPORT |
| `EpochSummary` | `tbot_integration/core/metrics.py` | CORE |
| `EpochTracker` | `unified_analysis.py` | TRANSPORT |
| `Event` | `backtester/core/orderbook_replay.py` | TRANSPORT |
| `ExecutionEngine` | `strategies/gabagool/execution_engine.py` | TRANSPORT |
| `ExecutionEngineV6` | `strategies/gabagool/execution_engine_v6.py` | PLATFORM |
| `Fill` | `tbot_core/api/models.py` | PLATFORM |
| `FillEvent` | `strategies/gabagool/execution_engine_v6.py` | PLATFORM |
| `FillModel` | `backtester/models/base.py` | CORE |
| `FillRateLogger` | `strategies/gabagool/fillrate_logger.py` | PLATFORM |
| `FillRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `FixedProbFillModel` | `backtester/models/fixed_prob.py` | CORE |
| `FullSnapshot` | `tbot_logger/enhanced_logger.py` | TRANSPORT |
| `GabagoolStrat` | `tbot_integration/strategy_adapter.py` | PLATFORM |
| `GridAdapter` | `tbot_integration/grid_adapter.py` | PLATFORM |
| `GridBacktestConfig` | `backtester/strategy/grid_strategy_sim.py` | PLATFORM |
| `GridBridgeAdapter` | `tbot_integration/grid_adapter.py` | PLATFORM |
| `GridConfig` | `strategies/gabagool/grid_strategy.py` | PLATFORM |
| `GridLevel` | `strategies/gabagool/grid_manager.py` | PLATFORM |
| `GridManager` | `strategies/gabagool/grid_manager.py` | PLATFORM |
| `GridStrategy` | `strategies/gabagool/grid_strategy.py` | PLATFORM |
| `GridStrategySim` | `backtester/strategy/grid_strategy_sim.py` | PLATFORM |
| `GuardCheckResult` | `tbot_risk/guards.py` | PLATFORM |
| `GuardResult` | `tbot_risk/guards.py` | PLATFORM |
| `HedgeLockRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `HybridAddress` | `tbot_integration/grid_adapter.py` | PLATFORM |
| `ImbalanceMode` | `tbot_integration/bvmm_strategy.py` | PLATFORM |
| `LDMAnalyzer` | `scripts/ldm_analyzer.py` | TRANSPORT |
| `LimitOrder` | `tbot_integration/bvmm_strategy.py` | PLATFORM |
| `LinkedOrderManager` | `strategies/gabagool/linked_orders.py` | TRANSPORT |
| `LiveTradingBridge` | `tbot_integration/live_trading_bridge.py` | PLATFORM |
| `LogParser` | `tbot_integration/core/parser.py` | PLATFORM |
| `LogReader` | `tbot_core/strategy/log_reader.py` | PLATFORM |
| `LotSizer` | `strategies/gabagool/lot_sizer.py` | PLATFORM |
| `MarketInfo` | `tbot_core/strategy/types.py` | PLATFORM |
| `MarketOptimizer` | `tbot_core/strategy/optimizer.py` | TRANSPORT |
| `MarketResult` | `strategies/gabagool/results_tracker.py` | PLATFORM |
| `MarketState` | `tbot_core/strategy/types.py` | PLATFORM |
| `MarketUpdate` | `tbot_core/api/models.py` | PLATFORM |
| `MockAdapter` | `strategies/gabagool/execution_engine.py` | TRANSPORT |
| `MockConfig` | `strategies/gabagool/lot_sizer.py` | PLATFORM |
| `MockEngine` | `replayer.py` | PLATFORM |
| `MockExchange` | `replayer.py` | PLATFORM |
| `MockPhaseConfig` | `strategies/gabagool/execution_engine.py` | TRANSPORT |
| `MockPos` | `strategies/gabagool/opportunity_evaluator.py` | PLATFORM |
| `MockPosition` | `strategies/gabagool/results_tracker.py` | PLATFORM |
| `NoCacheMiddleware` | `dashboard/server.py` | PLATFORM |
| `OBTick` | `backtester/core/orderbook_replay.py` | TRANSPORT |
| `OpportunityEvaluator` | `strategies/gabagool/opportunity_evaluator.py` | PLATFORM |
| `OpportunityResult` | `strategies/gabagool/opportunity_evaluator.py` | PLATFORM |
| `OptimizationResult` | `tbot_core/strategy/optimizer.py` | TRANSPORT |
| `OracleEngine` | `strategies/gabagool/oracle_engine.py` | TRANSPORT |
| `OrderAction` | `strategies/gabagool/grid_manager.py` | PLATFORM |
| `OrderBook` | `tbot_core/api/models.py` | PLATFORM |
| `OrderBookLevel` | `tbot_core/api/models.py` | PLATFORM |
| `OrderBookState` | `backtester/models/base.py` | CORE |
| `OrderEvent` | `tbot_core/api/ws_user_client.py` | PLATFORM |
| `OrderIntent` | `tbot_integration/strategy_adapter.py` | PLATFORM |
| `OrderLogger` | `strategies/gabagool/order_logger.py` | PLATFORM |
| `OrderManager` | `backtester/strategy/order_manager.py` | TRANSPORT |
| `OrderPricer` | `strategies/gabagool/order_pricer.py` | TRANSPORT |
| `OrderQueue` | `tbot_core/strategy/simple_strat2.py` | TRANSPORT |
| `OrderRecord` | `strategies/gabagool/order_logger.py` | PLATFORM |
| `OrderRequest` | `tbot_core/api/models.py` | PLATFORM |
| `OrderResponse` | `tbot_core/api/models.py` | PLATFORM |
| `OrderSigner` | `tbot_core/api/signing.py` | PLATFORM |
| `OrderSimulator` | `tbot_core/strategy/order_simulator.py` | CORE |
| `OrderSnapshot` | `strategies/gabagool/fillrate_logger.py` | PLATFORM |
| `OrderStatus` | `strategies/gabagool/order_logger.py` | PLATFORM |
| `OrderType` | `tbot_core/strategy/types.py` | PLATFORM |
| `OrderUpdate` | `tbot_core/strategy/types.py` | PLATFORM |
| `OrderbookDelta` | `tbot_logger/enhanced_logger.py` | TRANSPORT |
| `OrderbookLogger` | `tbot_logger/orderbook_logger.py` | PLATFORM |
| `OrderbookMirror` | `tbot_logger/poly_orderbook_swarm.py` | TRANSPORT |
| `PairStateSummary` | `tbot_integration/core/metrics.py` | CORE |
| `PairStateTransition` | `tbot_integration/core/parser.py` | PLATFORM |
| `PairTracker` | `strategies/gabagool/gabagool_strat.py` | PLATFORM |
| `ParamConvergence` | `backtester/optimizer/tier_inheritance.py` | TRANSPORT |
| `PendingOrder` | `strategies/gabagool/grid_manager.py` | PLATFORM |
| `Phase` | `strategies/gabagool/phase_manager.py` | PLATFORM |
| `PhaseConfig` | `strategies/gabagool/phase_manager.py` | PLATFORM |
| `PhaseManager` | `strategies/gabagool/phase_manager.py` | PLATFORM |
| `PolyOrderbookSwarm` | `tbot_logger/poly_orderbook_swarm.py` | TRANSPORT |
| `PolymarketAPI` | `tbot_core/api/market_api.py` | TRANSPORT |
| `PolymarketClient` | `tbot_core/api/client.py` | PLATFORM |
| `PolymarketWSClient` | `tbot_core/api/ws_client.py` | PLATFORM |
| `Position` | `tbot_core/strategy/types.py` | PLATFORM |
| `PositionState` | `tbot_integration/bvmm_strategy.py` | PLATFORM |
| `PositionTracker` | `backtester/strategy/position_tracker.py` | PLATFORM |
| `PriceFilter` | `strategies/gabagool/price_filter.py` | PLATFORM |
| `PriceManager` | `tbot_core/strategy/simple_strat2.py` | TRANSPORT |
| `PricingTraceRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `Profile` | `backtester/optimizer/profiles.py` | PLATFORM |
| `ProfileV6` | `backtester/optimizer/profiles_v6.py` | PLATFORM |
| `Quantiles` | `tbot_integration/core/metrics.py` | CORE |
| `QueueAwareFillModel` | `backtester/models/queue_aware.py` | TRANSPORT |
| `QuotingHealthSummary` | `tbot_integration/core/metrics.py` | CORE |
| `QuotingTickRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `RebalanceAction` | `strategies/gabagool/rebalancer.py` | PLATFORM |
| `RebalanceStats` | `strategies/gabagool/rebalancer.py` | PLATFORM |
| `Rebalancer` | `strategies/gabagool/rebalancer.py` | PLATFORM |
| `RecoveryPlan` | `strategies/gabagool/recovery_module.py` | PLATFORM |
| `RegimeSummary` | `tbot_integration/core/metrics.py` | CORE |
| `RelayerValue` | `tbot_integration/grid_adapter.py` | PLATFORM |
| `ReplayClock` | `backtester/core/clock.py` | CORE |
| `Replayer` | `replayer.py` | PLATFORM |
| `ResultsDB` | `backtester/results_db.py` | PLATFORM |
| `ResultsTracker` | `strategies/gabagool/results_tracker.py` | PLATFORM |
| `RiskGuards` | `tbot_risk/guards.py` | PLATFORM |
| `RiskLimits` | `tbot_risk/limits.py` | TRANSPORT |
| `RunningNormalizer` | `backtester/optimizer/optuna_optimizer.py` | TRANSPORT |
| `SessionStats` | `dashboard/server.py` | PLATFORM |
| `Side` | `tbot_core/strategy/types.py` | PLATFORM |
| `SimpleStrat2` | `tbot_core/strategy/simple_strat2.py` | TRANSPORT |
| `StrategyAdapter` | `tbot_integration/strategy_adapter.py` | PLATFORM |
| `StrategyMode` | `tbot_integration/bvmm_strategy.py` | PLATFORM |
| `StrategySim` | `backtester/strategy/strategy_sim.py` | PLATFORM |
| `StrikeFetcher` | `tbot_integration/strike_fetcher.py` | TRANSPORT |
| `SwarmSocket` | `tbot_logger/poly_orderbook_swarm.py` | TRANSPORT |
| `TakerRecoveryModule` | `strategies/gabagool/recovery_module.py` | PLATFORM |
| `TelegramAlerter` | `tbot_integration/telegram_alerts.py` | TRANSPORT |
| `TickTelemetry` | `strategies/gabagool/grid_strategy.py` | PLATFORM |
| `TimeMachine` | `replayer.py` | PLATFORM |
| `ToxicRecord` | `tbot_integration/core/parser.py` | PLATFORM |
| `ToxicSummary` | `tbot_integration/core/metrics.py` | CORE |
| `Trade` | `backtester/core/orderbook_replay.py` | TRANSPORT |
| `TradeEvent` | `tbot_logger/enhanced_logger.py` | TRANSPORT |
| `TradeIntent` | `tbot_core/strategy/types.py` | PLATFORM |
| `TradeSignal` | `tbot_core/strategy/types.py` | PLATFORM |
| `TradingEngine` | `tbot_core/engine.py` | PLATFORM |
| `TradingMode` | `tbot_core/strategy/types.py` | PLATFORM |
| `UserChannelClient` | `tbot_core/api/ws_user_client.py` | PLATFORM |
| `VPINCalculator` | `strategies/gabagool/vpin.py` | TRANSPORT |
| `ZmqMarketSubscriber` | `tbot_integration/live_trading_bridge.py` | PLATFORM |
| `ZmqPublisher` | `data_gateway.py` | TRANSPORT |
| `_BridgeStrategyProxy` | `tbot_integration/grid_adapter.py` | PLATFORM |
| `_Trade` | `tbot_integration/grid_adapter.py` | PLATFORM |

## Functions (top-level + async) per file

### `analysis/cli.py` [PLATFORM]
- `parse_args`
- `main`

### `analysis/exports/tableau_csv.py` [CORE]
- `export_epochs_csv`
- `export_fills_csv`
- `export_toxics_csv`
- `export_all`

### `analysis/signals/alpha_signals.py` [PLATFORM]
- `build_context`
- `detect_regime_zero_winrate`
- `detect_neutral_loss_paradox`
- `detect_torpedo_success`
- `detect_avg_down_inefficiency`
- `detect_pair_state_balance`
- `detect_pair_state_efficiency`
- `detect_entry_from_zero_pattern`
- `detect_pingpong_pattern`
- `detect_healer_fail_dominant`
- `detect_overpay_by_regime`
- `run_all_detectors`
- `render_signals`
- `render`

### `analysis/views/edge_view.py` [TRANSPORT]
- `render_edge_view`

### `analysis/views/leaderboard.py` [TRANSPORT]
- `compute_score`
- `render_leaderboard`

### `analysis/views/pair_state_view.py` [TRANSPORT]
- `render_pair_state_view`

### `analysis/views/quoting_health.py` [TRANSPORT]
- `_fmt_lot_dist`
- `_fmt_hc_dist`
- `render_quoting_health`

### `analysis/views/regime_view.py` [TRANSPORT]
- `render_regime_breakdown`
- `render_worst_epochs`

### `analysis/views/toxic_view.py` [TRANSPORT]
- `render_toxic_view`

### `api_xray.py` [PLATFORM]
- `async fetch_json`
- `async run_xray`

### `backtester/bridge/paper_bridge.py` [TRANSPORT]
- `load_params`
- `evaluate_fill`
- `get_model_info`

### `backtester/calibration/calibrator.py` [TRANSPORT]
- `calibrate`
- `load_calibrated_params`

### `backtester/configs/market_configs.py` [CORE]
- `detect_market_duration`
- `_scale_timing`
- `get_5m_configs`
- `get_configs_for_duration`
- `count_all`

### `backtester/configs/test_configs.py` [PLATFORM]
- `get_deposit_params`
- `_tag_deposit`
- `get_ab_test_configs`
- `get_imbalancer_sweep_configs`
- `get_param_sweep_configs`
- `get_recovery_sweep_configs`
- `get_momentum_sweep_configs`
- `get_bid_sum_sweep_configs`
- `get_drawdown_sweep_configs`
- `get_ladder_sweep_configs`
- `get_vol_pricing_sweep_configs`
- `get_vol_interval_sweep_configs`
- `get_depth_lot_sweep_configs`
- `get_market_pnl_sweep_configs`
- `get_edge_recovery_sweep_configs`
- `get_start_delay_sweep_configs`
- `get_all_configs`
- `count_configs`

### `backtester/core/clock.py` [CORE]
- `__init__`
- `advance`
- `elapsed_since`
- `time_in_market`
- `current_time`
- `start_time`
- `reset`

### `backtester/core/engine.py` [PLATFORM]
- `determine_winner`
- `replay_market`
- `_replay_worker`
- `replay_all`

### `backtester/core/engine_v6.py` [PLATFORM]
- `replay_market_v6`

### `backtester/core/orderbook_replay.py` [TRANSPORT]
- `load_orderbook_ticks`
- `_parse_book_levels`
- `load_trades`
- `merge_timeline`
- `get_all_market_ids`

### `backtester/core/trade_flow.py` [TRANSPORT]
- `get_volume_at_price`
- `get_trade_frequency`
- `get_depth_at_price`

### `backtester/daemon/runner_v2.py` [PLATFORM]
- `results_dir_for_duration`
- `load_processed`
- `save_processed`
- `_detect_symbol`
- `find_completed_markets`
- `save_market_results`
- `save_market_results_db`
- `run_once`
- `main`

### `backtester/daemon/runner_v3.py` [PLATFORM]
- `get_v3_configs`
- `get_v3_configs_for_duration`
- `get_cached_configs`
- `results_dir_for_duration`
- `load_processed`
- `save_processed`
- `_detect_symbol`
- `find_completed_markets`
- `save_market_results_db`
- `run_once`
- `main`

### `backtester/models/base.py` [CORE]
- `__post_init__`
- `check_fills`
- `reset`

### `backtester/models/fixed_prob.py` [CORE]
- `__init__`
- `check_fills`
- `reset`

### `backtester/models/queue_aware.py` [TRANSPORT]
- `__init__`
- `check_fills`
- `_trade_can_fill`
- `_get_queue_ahead`
- `reset`

### `backtester/optimizer/deposit_scaler.py` [TRANSPORT]
- `scale_config`
- `generate_all_tiers`
- `main`

### `backtester/optimizer/dsr_validator.py` [TRANSPORT]
- `compute_sr0`
- `compute_psr`
- `compute_dsr`
- `get_oos_market_ids`
- `run_oos_backtest`
- `main`

### `backtester/optimizer/lhs_screening.py` [TRANSPORT]
- `_init_strategy`
- `get_allowed_values`
- `get_all_param_names`
- `check_constraints`
- `generate_lhs_samples`
- `run_screening`
- `sensitivity_analysis_vom`
- `sensitivity_analysis_rf`
- `sensitivity_analysis`
- `select_significant_params`
- `save_screening_results`
- `get_market_ids_by_type`
- `main`
- `_params_to_config_v6`

### `backtester/optimizer/optuna_optimizer.py` [TRANSPORT]
- `_init_strategy_optuna`
- `_get_storage_for_strategy`
- `_get_storage`
- `values_to_enqueue`
- `resolve_trial_params`
- `_check_memory`
- `preload_market_data`
- `create_objective`
- `run_multi_start`
- `_prior_aggressive_A`
- `_prior_conservative_C`
- `_prior_balance_focus`
- `_prior_util_focus`
- `_prior_interblock`
- `run_block_refinement`
- `run_final_crossblock`
- `extract_top_configs`
- `save_funnel_results`
- `run_full_pipeline`
- `main`
- `__init__`
- `update`
- `is_ready`
- `score`
- `objective`
- `_ptbc_v6`
- `_suggest_v6`
- `_check_v6`

### `backtester/optimizer/param_space.py` [TRANSPORT]
- `check_constraints`
- `get_allowed_values`
- `get_optimizable_params`
- `get_frozen_params`
- `params_to_backtest_config`
- `suggest_params`
- `resolve_trial_params`
- `values_to_enqueue`
- `get_param_names_for_block`
- `get_all_param_names`
- `get_param_values`
- `validate_space`

### `backtester/optimizer/param_space_v6.py` [TRANSPORT]
- `get_optimizable_params`
- `get_frozen_params`
- `count_combinations`
- `suggest_params_lhs`
- `params_to_config`
- `validate_space`

### `backtester/optimizer/profiles.py` [PLATFORM]
- `_merge`
- `_register`
- `get_profile`
- `list_profiles`
- `count_optimizable`
- `count_frozen`
- `count_combinations`
- `main`
- `apply`
- `summary`

### `backtester/optimizer/profiles_v6.py` [PLATFORM]
- `_register`
- `get_profile_v6`
- `apply`
- `summary`

### `backtester/optimizer/tier_inheritance.py` [TRANSPORT]
- `analyze_convergence`
- `build_inherited_profile`
- `apply_inheritance`
- `print_report`
- `_normalize`
- `_get_narrow_range`
- `main`
- `__repr__`

### `backtester/reporting/funnel_report.py` [TRANSPORT]
- `generate_report`
- `update_decisions_md`
- `main`

### `backtester/reporting/report.py` [TRANSPORT]
- `generate_summary`
- `generate_comparison`
- `_avg_metric`
- `_avg_metric_nonzero`

### `backtester/results_db.py` [PLATFORM]
- `import_from_jsonl`
- `__init__`
- `_create_tables`
- `add_market_result`
- `commit`
- `top_configs`
- `worst_configs`
- `deposit_overview`
- `group_analysis`
- `market_count`
- `close`

### `backtester/scripts/acf_regime_analyzer.py` [TRANSPORT]
- `classify_market`
- `load_l1_yes`
- `resample_mid`
- `calc_log_returns`
- `calc_acf`
- `find_decay_time`
- `main`

### `backtester/scripts/hard_mode_autopsy.py` [TRANSPORT]
- `build_config`
- `run_autopsy`

### `backtester/scripts/mm_regime_shift.py` [CORE]
- `analyze_period`
- `main`
- `delta`

### `backtester/strategy/grid_strategy_sim.py` [PLATFORM]
- `__init__`
- `start_market`
- `update_orderbook`
- `on_tick`
- `on_fill`
- `on_trade`
- `_estimate_market_pnl`

### `backtester/strategy/order_manager.py` [TRANSPORT]
- `__init__`
- `place`
- `get_pending`
- `record_fill_time`
- `is_cooldown_active`
- `mark_filled`
- `expire_old`
- `mark_pending_cancel`
- `mark_stale_pending_cancel`
- `hysteresis_sync`
- `purge_expired_cancels`
- `is_pending_cancel`
- `record_toxic_fill`
- `toxic_fills`
- `toxic_fill_cost`
- `cancel_all`
- `cancel_by_token`
- `placed_count`
- `filled_count`
- `expired_count`
- `cancelled_count`
- `has_pending`
- `pending_count`
- `reset`

### `backtester/strategy/position_tracker.py` [PLATFORM]
- `__init__`
- `record_fill`
- `record_sell`
- `_update_pairs`
- `yes_avg_price`
- `no_avg_price`
- `current_imbalance`
- `weak_leg`
- `deficit_shares`
- `worst_case_pnl`
- `calculate_pnl`
- `avg_pair_sum`
- `roi`
- `get_metrics`
- `reset`

### `backtester/strategy/strategy_sim.py` [PLATFORM]
- `__init__`
- `start_market`
- `update_orderbook`
- `on_trade`
- `_calculate_vpin`
- `_get_phase`
- `_get_phase_config`
- `_get_safe_max_imbalance`
- `_evaluate_opportunity`
- `_get_effective_lot`
- `_rebalance_weak_leg`
- `_check_linked_order`
- `on_tick`
- `on_fill`
- `_generate_orders_alternating`
- `_make_single_order`
- `_get_current_vol`
- `_get_effective_interval`
- `_resolve_pricing_mode`
- `_get_price`
- `_get_as_price`
- `_generate_ladder_intents`
- `_check_recovery`

### `claim_probe.py` [TRANSPORT]
- `patch_relayer_client`
- `run_claim_probe`
- `_fixed_generate_headers`
- `value`

### `dashboard/microstructure/calculator.py` [TRANSPORT]
- `get_windows`
- `tick_intensity`
- `sample_entropy`
- `permutation_entropy`
- `contract_price_entropy`
- `hurst_exponent`
- `microprice_divergence`
- `calculate_microstructure`

### `dashboard/microstructure/kde_renderer.py` [TRANSPORT]
- `_kde_smooth`
- `render_kde`

### `dashboard/microstructure/post_market.py` [CORE]
- `get_bot_id`
- `analyze_market`
- `batch_analyze`
- `main`

### `dashboard/microstructure/tape_renderer.py` [PLATFORM]
- `render_market_tape`

### `dashboard/server.py` [PLATFORM]
- `load_bot_config`
- `get_bot_id`
- `load_bot_results`
- `_load_bot_live_state_file`
- `get_bot_live_state`
- `get_all_bots_status`
- `load_market_results`
- `load_live_state`
- `calculate_stats`
- `_maybe_render_kde_background`
- `_maybe_render_tape_background`
- `get_bot_live_state_cached`
- `_rotate_tape_pngs`
- `_render`
- `_lookup`
- `async architecture_page`
- `async monitor_page`
- `async root`
- `async get_markets`
- `async get_stats`
- `async get_pending_claims`
- `async health_check`
- `async get_live_state`
- `async get_bots`
- `async get_bot_stats`
- `async get_bot_markets`
- `async get_bot_live_state_endpoint`
- `async get_bot_microstructure`
- `async get_microstructure_by_slug`
- `async render_tape_by_slug`
- `async save_tape_screenshot`
- `async get_bot_market_replay`
- `async get_comparison`
- `async ws_bot`
- `async websocket_endpoint`
- `async get_ldm_metrics`
- `async dispatch`

### `data_gateway.py` [TRANSPORT]
- `main`
- `__init__`
- `close`
- `__init__`
- `_start_oracle`
- `_on_trade_wrapper`
- `_launch`
- `gateway_sync_wrapper`
- `async publish`
- `async _on_orderbook`
- `async _on_trade`
- `async _btc_broadcast_loop`
- `async _market_info_loop`
- `async _consolidated_processor`
- `async _on_trade`
- `async run`
- `async _heartbeat_loop`
- `async stop`
- `async gateway_trade_bridge`

### `fleet_results.py` [TRANSPORT]
- `discover_bots`
- `get_hypothesis`
- `parse_log`
- `compute_score`
- `print_leaderboard`
- `main`

### `generate_fleet.py` [TRANSPORT]
- `load_yaml`
- `save_yaml`
- `generate_bot_id`
- `generate_fleet`

### `main.py` [PLATFORM]
- `setup_logging`
- `load_bankroll_config`
- `_check_kill_switch`
- `handle_exception`
- `main`
- `oracle_zmq_subscriber`
- `launch_oracle`
- `async send_market_notification`
- `async run_live`
- `async run_logger`
- `async run_paper`
- `async run_live_bridge`
- `async _check_sufficient_balance`

### `merge_probe.py` [TRANSPORT]
- `patched_generate_headers`
- `run_probe_v17`
- `value`

### `monitor.py` [TRANSPORT]
- `create_layout`
- `make_bar`
- `get_cvd_bar`
- `get_dashboard`
- `async main`

### `oracle_daemon.py` [TRANSPORT]
- `async main`

### `replayer.py` [PLATFORM]
- `mock_time`
- `__init__`
- `purge_expired_cancels`
- `get_live_cfr`
- `get_some_other_thing`
- `process_tick_matching`
- `process_trade_matching`
- `_execute_fills`
- `__init__`
- `stream_events`
- `__init__`
- `process_trade`
- `place_order`
- `__init__`
- `async batch_place`
- `async batch_cancel`
- `async place_taker`
- `async execute_nuclear_cancel`
- `async run`

### `reports/gini_chart.py` [CORE]
- `cumulative_profit_curve`

### `reports/safety_table.py` [CORE]
- `count_lines`

### `run_logger.py` [PLATFORM]
- `parse_args`
- `handle_signal`
- `async main`

### `scanner.py` [PLATFORM]
- `async run_scanner`

### `scripts/analyze_fanova.py` [TRANSPORT]
- `find_latest_screening`
- `load_data`
- `analyze`
- `diagnose_gearbox`
- `print_report`
- `main`

### `scripts/claim_resolved.py` [PLATFORM]
- `patch_relayer_client`
- `get_w3`
- `load_queue`
- `save_queue`
- `load_token_cache`
- `save_token_cache`
- `_parse_token_ids`
- `gamma_lookup`
- `on_chain_scan`
- `scan_log_files`
- `scan_live_state`
- `scan_pm2_logs`
- `refresh_recent_markets`
- `get_relay_client`
- `submit_safe_claim`
- `check_and_claim`
- `main`
- `_fixed_generate_headers`
- `value`
- `get_strict`
- `value`

### `scripts/health_check.py` [TRANSPORT]
- `get_pm2_status`
- `get_live_state`
- `get_error_check`
- `read_jsonl`
- `get_market_results`
- `get_latency_stats`
- `get_position_sync`
- `generate_alerts`
- `run_health_check`
- `save_report`
- `main`

### `scripts/ldm_analyzer.py` [TRANSPORT]
- `__init__`
- `calculate_metrics`
- `run`

### `scripts/ldm_collector.py` [CORE]
- `parse_log`
- `percentile`
- `generate_report`
- `print_markdown`
- `main`

### `scripts/math_playground.py` [TRANSPORT]
- `run_scenario_explorer`

### `scripts/merge_probe.py` [PLATFORM]
- `run_probe_v3`
- `value`

### `scripts/safety_watchdog.py` [PLATFORM]
- `get_live_state`
- `get_pm2_info`
- `stop_bot`
- `check_safety`
- `main`

### `scripts/Сканнеры SDK/autopsy_engine_v2.py` [TRANSPORT]
- `async run_autopsy`

### `scripts/Сканнеры SDK/check_auth.py` [TRANSPORT]
- `check`

### `scripts/Сканнеры SDK/check_market_precision.py` [TRANSPORT]
- `check_target_market`

### `scripts/Сканнеры SDK/check_token.py` [PLATFORM]
- `check_book`

### `scripts/Сканнеры SDK/clob_truth.py` [PLATFORM]
- `get_precision`

### `scripts/Сканнеры SDK/get_truth.py` [PLATFORM]
- `get_clob_precision`

### `scripts/Сканнеры SDK/nuclear_scanner.py` [PLATFORM]
- `scan_sdk`

### `scripts/Сканнеры SDK/scan_sdk.py` [PLATFORM]
- `scan`

### `strategies/gabagool/as_pricer.py` [PLATFORM]
- `__init__`
- `calculate`
- `_get_sigma_sq`
- `_get_gamma_eff`

### `strategies/gabagool/bankroll_manager.py` [PLATFORM]
- `__init__`
- `get_base_lot_usd`
- `get_max_lot_usd`
- `get_base_lot_shares`
- `get_max_lot_shares`
- `get_lot_shares_for_usd`
- `get_imbalance_threshold_pct`
- `is_imbalanced`
- `get_imbalance_pct`
- `get_rebalance_shares`
- `get_max_position_usd`
- `get_max_position_shares`
- `get_capital_utilization`
- `can_place_order`
- `get_paced_lot_and_interval`
- `get_paced_lot_shares`
- `update_bankroll`
- `get_summary`
- `__repr__`

### `strategies/gabagool/execution_engine.py` [TRANSPORT]
- `__init__`
- `execute_action`
- `execute_both`
- `_place_order_with_lot`
- `_place_order`
- `_send_to_adapter`
- `cleanup_stale_orders`
- `_should_replace_order`
- `_get_best_bid`
- `_get_order_timeout`
- `_cancel_order`
- `on_fill`
- `get_active_orders`
- `get_stats`
- `__init__`
- `on_order`
- `__init__`

### `strategies/gabagool/execution_engine_v6.py` [PLATFORM]
- `safe_poly_serialize`
- `__init__`
- `_nudge_price`
- `_paper_place`
- `check_sell_fills`
- `get_active_sell_orders`
- `_clob_get_order`
- `purge_expired_cancels`
- `is_pending_cancel`
- `set_token_ids`
- `reset`
- `active_count`
- `get_stats`
- `_get_rust_headers`
- `_write_to_orders_log`
- `get_live_cfr`
- `get_avg_latency`
- `async batch_place`
- `async _live_place`
- `async cancel_stale_orders`
- `async batch_cancel`
- `async cancel_all_market`
- `async cancel_all_verified`
- `async place_taker`
- `async on_fill`
- `async poll_fills`
- `async _poll_fills_fallback`
- `async merge_positions`
- `async execute_nuclear_cancel`
- `async _call_api`

### `strategies/gabagool/fillrate_logger.py` [PLATFORM]
- `__init__`
- `log_order_placed`
- `log_fill`
- `log_instant_fill`
- `log_cancel`
- `log_expired`
- `get_stats`
- `reset`
- `_write`

### `strategies/gabagool/gabagool_strat.py` [PLATFORM]
- `avg_yes`
- `avg_no`
- `update_yes`
- `update_no`
- `all_in_sum`
- `total_cost`
- `imbalance_shares`
- `pair_ratio`
- `reset`
- `__init__`
- `on_fill`
- `_match_pairs`
- `unfilled_legs`
- `unfilled_yes_shares`
- `unfilled_no_shares`
- `get_stats`
- `reset`
- `__init__`
- `_default_config`
- `on_tick`
- `_execute_and_get_intents`
- `_on_tick_v21`
- `_calculate_unrealized_pnl`
- `on_fill`
- `on_trade`
- `_calculate_vpin`
- `_get_phase_config`
- `_get_safe_max_imbalance`
- `_try_imbalance_reserve`
- `_execute_recovery`
- `_check_and_execute_rebalance`
- `_get_best_bid`
- `_get_aggressive_price`
- `record_rebalance_fill`
- `get_rebalance_stats`
- `_handle_safe_mode`
- `on_market_switch`
- `_on_market_end`
- `_determine_winner`
- `on_market_start`
- `_update_orderbook`
- `_build_orderbook_dict`
- `_log_state`
- `get_status`
- `is_drawdown_stopped`
- `get_risk_status`
- `get_live_state`
- `make_market_data`

### `strategies/gabagool/grid_manager.py` [PLATFORM]
- `__init__`
- `register_sell_order`
- `on_sell_fill`
- `cancel_sell_order`
- `expire_stale_sells`
- `calculate_target_grid`
- `sync`
- `_cancel_with_event`
- `register_order`
- `on_fill`
- `on_cancel_confirmed`
- `cancel_all`
- `cancel_side`
- `clear_all`
- `get_pending_notional`
- `pending_count`

### `strategies/gabagool/grid_strategy.py` [PLATFORM]
- `__init__`
- `reset`
- `_compute_layer1_skew`
- `_compute_layer2_veto`
- `evaluate`
- `q`
- `total_cost`
- `locked_pairs`
- `active_total_cost`
- `imbalance_pct`
- `apply_ctf_merge`
- `reset`
- `__init__`
- `get_live_state`
- `dump_market_tape`
- `_emit_event`
- `_calculate_implied_strike`
- `_calculate_dynamic_pricing`
- `_calculate_dynamic_trust`
- `_apply_triage_logic`
- `on_tick`
- `_compute_oracle_fv`
- `_compute_elastic_iron_gate`
- `_run_safety_and_merge`
- `_run_preflight`
- `_run_oracle_data_prep`
- `_run_final_sync_and_triage`
- `_run_grid_orchestrator`
- `_run_hard_veto`
- `_run_hedge_immunity`
- `_run_grid_pruning`
- `_apply_smart_gc`
- `_apply_maq_filter`
- `_apply_bbo_clamp`
- `_apply_profit_gate_sanitizer`
- `_run_toxic_recovery_protocol`
- `_compute_vector_pricing_and_hunter`
- `_compute_healer`
- `_compute_pair_state`
- `_armor_edge_contribution`
- `_gravity_edge_contribution`
- `_toxicity_multiplier`
- `_compute_final_edge`
- `_compute_auto_armor`
- `_compute_intent_mode`
- `_compute_spread_and_shield`
- `_run_oracle_pipeline`
- `_compute_velocity`
- `_get_k_alpha_dynamic`
- `_compute_lot_sizing`
- `_compute_shadow_accounting`
- `_compute_elastic_gravity`
- `_run_forensic_telemetry`
- `_synthesize_master_intent`
- `on_trade`
- `_trigger_emergency_pull`
- `record_api_request`
- `api_requests_per_min`
- `on_fill`
- `on_market_switch`
- `_check_risk_stop`
- `update_session_pnl`
- `_check_recovery`
- `_read_parent_regime`
- `_broadcast_regime`
- `_check_recycling_sell`
- `_check_emergency_dump`
- `_calculate_max_safe_price`
- `_log_decision`
- `_std_ctx`
- `_log_block_state`
- `get_final_report_text`

### `strategies/gabagool/linked_orders.py` [TRANSPORT]
- `__init__`
- `should_link`
- `_get_best_ask`
- `get_stats`

### `strategies/gabagool/live_trading_bridge.py` [PLATFORM]
- `__init__`
- `_init_components`
- `_init_trading_components`
- `_init_grid_components`
- `_build_market_state`
- `_log_status`
- `_update_strike_price`
- `_check_rebate`
- `_get_live_state`
- `get_status`
- `async run_paper_trading`
- `async _on_orderbook_update`
- `async run`
- `async _resolution_checker_loop`
- `async _live_state_broadcaster`
- `async _price_ticker_loop`
- `async _fetch_asset_price`
- `async _prefetch_prev_close`
- `async _fetch_and_store_strike`
- `async _fetch_wallet_balance`
- `async stop`
- `async wrapped_handler`
- `async _register_vpin_trade_feed`
- `async vpin_wrapped`

### `strategies/gabagool/lot_sizer.py` [PLATFORM]
- `calculate`
- `calculate_balanced_lots`
- `_get_position_shares`
- `__init__`
- `calculate`
- `_calculate_liquidity`
- `_sum_top_levels`
- `_get_liquidity_multiplier`
- `_get_imbalance_multiplier_pct`
- `_get_imbalance_multiplier`
- `_get_time_multiplier`
- `_get_shares`
- `__init__`

### `strategies/gabagool/opportunity_evaluator.py` [PLATFORM]
- `to_dict`
- `__init__`
- `evaluate`
- `evaluate_dict`
- `_calculate_natural_spread`
- `_calculate_score`
- `_calculate_yes_score`
- `_calculate_no_score`
- `_passes_threshold`
- `_get_best_bid`
- `_get_best_ask`
- `_get_mid_price`
- `_get_avg_price`
- `_get_shares`
- `_build_reason`
- `evaluate_v21`
- `__init__`

### `strategies/gabagool/oracle_engine.py` [TRANSPORT]
- `__init__`
- `_handle_task_exception`
- `get_composite_price`
- `calculate_fv`
- `async run_forever`
- `async start`
- `async _listen_okx`
- `async _listen_binance`
- `async _listen_bybit`

### `strategies/gabagool/order_logger.py` [PLATFORM]
- `get_order_logger`
- `to_dict`
- `__init__`
- `_generate_local_id`
- `log_intent`
- `update_order`
- `log_simulated_fill`
- `log_live_sent`
- `log_live_fill`
- `log_error`
- `_write_record`
- `get_latency_stats`
- `get_session_stats`

### `strategies/gabagool/order_pricer.py` [TRANSPORT]
- `calculate`
- `get_time_adjusted_aggressiveness`
- `__init__`
- `calculate`
- `_get_best_bid`
- `_get_best_ask`

### `strategies/gabagool/phase_manager.py` [PLATFORM]
- `to_dict`
- `__init__`
- `update`
- `calculate_target_diff`
- `_update_target_diff`
- `_calculate_natural_spread`
- `_get_mid_price`
- `_update_volatility`
- `get_current_phase`
- `_calculate_current_diff`
- `_on_phase_transition`
- `get_phase_config`
- `_apply_custom_config`
- `get_natural_spread`
- `get_status`
- `__init__`

### `strategies/gabagool/price_filter.py` [PLATFORM]
- `__init__`
- `update`
- `should_skip`
- `reset`
- `check`

### `strategies/gabagool/rebalancer.py` [PLATFORM]
- `record`
- `summary`
- `__init__`
- `check_rebalance`
- `_get_ask_price`
- `_get_bid_price`
- `record_rebalance`
- `get_stats`
- `reset_stats`
- `__init__`

### `strategies/gabagool/recovery_module.py` [PLATFORM]
- `__init__`
- `reset`
- `evaluate`
- `mark_executed`
- `was_executed`
- `last_plan`
- `_get_best_ask`

### `strategies/gabagool/results_tracker.py` [PLATFORM]
- `_get_market_results_file`
- `get_tracker`
- `__init__`
- `on_market_end`
- `on_market_end_resolved`
- `_calculate_pnl`
- `_save_result`
- `_save_pending`
- `_load_pending`
- `get_daily_summary`
- `print_summary`
- `async check_resolutions`
- `async _check_market_resolve`

### `strategies/gabagool/strategy_adapter.py` [PLATFORM]
- `__init__`
- `_init_live_trading`
- `_build_strategy_config`
- `set_token_ids`
- `on_trade`
- `on_market_update`
- `_on_market_switch`
- `_simulate_fills`
- `_process_pending_queue_aware`
- `_process_pending_paper_orders`
- `_process_fill`
- `_execute_rebalance`
- `_build_orderbook_for_fillrate`
- `on_order_update`
- `get_pnl`
- `get_status`
- `async start_live_client`
- `async stop_live_client`
- `async _place_live_orders`
- `async _place_batch_orders`
- `async _place_single_order`
- `async _fill_tracking_loop`
- `async _lifecycle_retry_stale_orders`
- `async _lifecycle_aggressive_fill_partial_pairs`
- `async _place_rebalance_order`
- `async _cancel_order`
- `async _emergency_cancel_all`
- `async _cancel_all_orders`
- `async _cancel_orders_by_ids`

### `strategies/gabagool/vpin.py` [TRANSPORT]
- `on_trade`
- `get`
- `is_toxic`
- `reset`

### `tbot_core/api/client.py` [PLATFORM]
- `__init__`
- `_update_credentials`
- `is_healthy`
- `is_authenticated`
- `can_sign_orders`
- `async start`
- `async stop`
- `async _request`
- `async get_markets`
- `async get_market_info`
- `async get_orderbook`
- `async get_recent_trades`
- `async create_order`
- `async cancel_order`
- `async cancel_all_orders`
- `async get_order`
- `async get_orders`
- `async get_balances`
- `async get_positions`
- `async create_or_derive_api_key`
- `async _request_authenticated`
- `async create_signed_order`
- `async ping`

### `tbot_core/api/market_api.py` [TRANSPORT]
- `__init__`
- `async find_markets`
- `async find_market_by_timestamp`

### `tbot_core/api/models.py` [PLATFORM]
- `from_raw`
- `best_bid`
- `best_ask`
- `spread`
- `get_price_levels`
- `from_message`
- `from_message`
- `time_to_expiry_seconds`
- `get_theo_edge`
- `to_json`
- `from_json`
- `from_json`
- `total_cost`
- `imbalance`
- `avg_yes_price`
- `avg_no_price`
- `update`
- `calculate_pnl`
- `worst_case_pnl`

### `tbot_core/api/signing.py` [PLATFORM]
- `derive_proxy_wallet`
- `to_dict`
- `__init__`
- `get_clob_auth_domain`
- `sign_clob_auth_message`
- `get_l1_auth_headers`
- `build_hmac_signature`
- `get_l2_auth_headers`
- `get_order_domain`
- `sign_order`
- `create_signed_order_payload`

### `tbot_core/api/ws_client.py` [PLATFORM]
- `__init__`
- `async connect`
- `async _send_subscription`
- `async subscribe_by_market`
- `async unsubscribe`
- `async _handle_book_snapshot`
- `async _handle_price_change`
- `async _handle_last_trade`
- `async _dispatch_update`
- `async _process_message`
- `async _heartbeat`
- `async _check_connection`
- `async reconnect`
- `async run`
- `async stop`

### `tbot_core/api/ws_user_client.py` [PLATFORM]
- `from_message`
- `is_confirmed`
- `is_failed`
- `from_message`
- `remaining_size`
- `__init__`
- `set_trade_handler`
- `set_order_handler`
- `get_active_orders`
- `get_pending_trades`
- `async connect`
- `async _subscribe`
- `async _process_message`
- `async run`
- `async stop`

### `tbot_core/engine.py` [PLATFORM]
- `__init__`
- `_setup_logging`
- `get_status`
- `async main`
- `async start`
- `async stop`
- `async run_market`
- `async _on_market_update`
- `async _on_fill`
- `async _on_user_trade`
- `async _on_user_order`
- `async _panic_exit`
- `async _check_and_claim_profits`

### `tbot_core/strategy/core.py` [PLATFORM]
- `__init__`
- `yes_position`
- `no_position`
- `get_best_levels`
- `__init__`

### `tbot_core/strategy/enhanced_bvmm.py` [PLATFORM]
- `__init__`
- `validate_market_state`
- `analyze_market_state`
- `async get_active_market`
- `async get_next_market`
- `async prepare_next_market`
- `async run`

### `tbot_core/strategy/log_reader.py` [PLATFORM]
- `__init__`
- `switch_market`
- `_parse_orderbook_line`
- `get_latest_orderbook`

### `tbot_core/strategy/optimizer.py` [TRANSPORT]
- `__init__`
- `optimize_position`
- `_get_best_bid`
- `_get_best_ask`
- `_invalid_result`
- `cleanup`

### `tbot_core/strategy/order_simulator.py` [CORE]
- `__init__`
- `execute_order`
- `get_position_value`
- `get_total_volume`

### `tbot_core/strategy/simple_strat2.py` [TRANSPORT]
- `__init__`
- `on_market_update`
- `_check_and_handle_imbalance`
- `_handle_emergency_imbalance`
- `_handle_high_imbalance`
- `_can_place_order`
- `_place_new_orders`
- `_update_active_orders`
- `on_order_filled`
- `cancel_all_orders`
- `__init__`
- `add_order`
- `remove_order`
- `adjust_priorities`
- `clear`
- `__init__`
- `get_order_price`
- `get_aggressive_price`
- `adjust_prices_for_imbalance`
- `_validate_price`
- `check_and_update_price`

### `tbot_core/strategy/types.py` [PLATFORM]
- `__init__`
- `yes_position`
- `no_position`
- `get_best_levels`

### `tbot_integration/bvmm_strategy.py` [PLATFORM]
- `update_yes`
- `update_no`
- `all_in_sum`
- `total_cost`
- `imbalance_shares`
- `pair_ratio`
- `weak_leg`
- `reset`
- `__init__`
- `on_tick`
- `_update_orderbook`
- `_get_best_bid`
- `_get_best_ask`
- `_get_bid_depth`
- `_update_imbalance_mode`
- `_calculate_limit_prices`
- `_calculate_catchup_price`
- `_generate_pair_intents`
- `_generate_catchup_intent`
- `_calculate_worst_case`
- `on_fill`
- `on_market_switch`
- `_log_summary`
- `get_status`

### `tbot_integration/core/bot_selector.py` [CORE]
- `discover_bots`
- `get_hypothesis_group`
- `select_bots`

### `tbot_integration/core/epoch_tracker.py` [PLATFORM]
- `build_epochs_for_bot`
- `__init__`
- `_reset`
- `process`

### `tbot_integration/core/metrics.py` [CORE]
- `quantiles`
- `pct`
- `avg`
- `summarize_epochs`
- `edge_by_intent`
- `edge_by_regime`
- `summarize_toxics`
- `summarize_pair_state`
- `_bbo_dist`
- `_lot_distribution`
- `_hc_distribution`
- `_median`
- `summarize_quoting_health`

### `tbot_integration/core/parser.py` [PLATFORM]
- `fv_dist`
- `ps_delta`
- `fv_dist`
- `q_was_zero`
- `q_sign_changed`
- `yes_active`
- `no_active`
- `yes_bbo_distance_cents`
- `no_bbo_distance_cents`
- `__init__`
- `_line_after_filter`
- `parse_file`
- `_parse_fill`
- `_parse_toxic`
- `_parse_pair_state`
- `_parse_pricing_trace`
- `_parse_quoting_tick`
- `_parse_capacity_crush`
- `_parse_hedge_lock`
- `_grab`

### `tbot_integration/grid_adapter.py` [PLATFORM]
- `patch_relayer_client`
- `_fixed_generate_headers`
- `value`
- `__init__`
- `on_fill_event`
- `_update_fill_ob`
- `_process_trade_for_fills`
- `_simulate_fills`
- `_build_market_data`
- `_build_grid_config`
- `get_stats`
- `__init__`
- `engine`
- `on_market_update`
- `on_trade`
- `get_pnl`
- `stats`
- `__init__`
- `engine`
- `position`
- `on_market_switch`
- `on_trade`
- `get_live_state`
- `get_final_report_text`
- `_best`
- `_fetch_balance`
- `_submit_to_relayer_sync`
- `_check_status_sync`
- `__call__`
- `async get_session`
- `async sync_inventory_from_api`
- `async on_market_update`
- `async _execute_actions`
- `async _internal_handle_cancels`
- `async _internal_handle_makers`
- `async _run_background_merge`
- `async on_market_switch`
- `async _handle_fill`
- `async _safe_merge_sequence`
- `async record_confirmed_fill`
- `async start_live_client`
- `async stop_live_client`
- `async _do_async_tick`

### `tbot_integration/live_trading_bridge.py` [PLATFORM]
- `__init__`
- `__init__`
- `_load_persistence`
- `_init_components`
- `_init_trading_components`
- `_init_grid_components`
- `_build_market_state`
- `_log_status`
- `_handle_monitor_error`
- `_update_shared_strike`
- `_get_live_state`
- `get_status`
- `_launch`
- `_read_pnl_sync`
- `wrapped_handler`
- `_forensic_encoder`
- `_extract_price`
- `_extract_size`
- `zmq_trade_injector`
- `_save_brain`
- `async run_paper_trading`
- `async run`
- `async stop`
- `async _fetch_market_volume`
- `async _check_kill_switch_pnl`
- `async _on_orderbook_update`
- `async _ws_watchdog_loop`
- `async run`
- `async _poll_fills_loop`
- `async _resolution_checker_loop`
- `async _live_state_broadcaster`
- `async _price_ticker_loop`
- `async _fetch_asset_price`
- `async _prefetch_prev_close`
- `async _fetch_and_store_strike`
- `async _fetch_wallet_balance`
- `async stop`
- `async _register_vpin_trade_feed`
- `async vpin_wrapped`

### `tbot_integration/strategy_adapter.py` [PLATFORM]
- `__init__`
- `_init_live_trading`
- `_build_strategy_config`
- `set_token_ids`
- `on_trade`
- `on_market_update`
- `_on_market_switch`
- `_simulate_fills`
- `_process_pending_queue_aware`
- `_process_pending_paper_orders`
- `_process_fill`
- `_execute_rebalance`
- `_build_orderbook_for_fillrate`
- `on_order_update`
- `get_pnl`
- `get_status`
- `__init__`
- `get_status`
- `on_tick`
- `on_market_switch`
- `on_fill`
- `on_trade`
- `async start_live_client`
- `async stop_live_client`
- `async _place_live_orders`
- `async _place_batch_orders`
- `async _place_single_order`
- `async _fill_tracking_loop`
- `async _lifecycle_retry_stale_orders`
- `async _lifecycle_aggressive_fill_partial_pairs`
- `async _place_rebalance_order`
- `async _cancel_order`
- `async _emergency_cancel_all`
- `async _cancel_all_orders`
- `async _cancel_orders_by_ids`

### `tbot_integration/strike_fetcher.py` [TRANSPORT]
- `__init__`
- `_make_slug`
- `get_cached_strike`
- `set_strike`
- `async get_binance_open`
- `async get_previous_market_close`
- `async fetch_strike`
- `async verify_strike`

### `tbot_integration/telegram_alerts.py` [TRANSPORT]
- `_load_env`
- `get_alerter`
- `send_alert_sync`
- `__init__`
- `async _get_session`
- `async send_alert`
- `async alert_drawdown_stop`
- `async alert_warning`
- `async alert_safe_mode`
- `async alert_bot_start`
- `async alert_bot_stop`
- `async alert_market_resolved`
- `async close`

### `tbot_logger/enhanced_logger.py` [TRANSPORT]
- `create_enhanced_logger`
- `to_dict`
- `to_dict`
- `to_dict`
- `__init__`
- `_setup_directories`
- `_setup_database`
- `set_market`
- `_book_to_dict`
- `compute_deltas`
- `_compute_side_deltas`
- `_create_snapshot`
- `get_stats`
- `_get`
- `_to_json`
- `async process_book_update`
- `async process_trade`
- `async _store_deltas`
- `async _store_snapshot`
- `async _store_trade`
- `async cleanup_old_data`
- `async run_cleanup_scheduler`
- `async test`

### `tbot_logger/orderbook_logger.py` [PLATFORM]
- `__init__`
- `load_configs`
- `setup_database_connection`
- `_get_db_conn`
- `setup_database_schema`
- `_v`
- `async handle_orderbook_message`
- `async store_orderbook_data`
- `async handle_trade_message`
- `async run`
- `async monitor_market`
- `async monitor_connection`
- `async _rest_fallback_monitor`
- `async _fetch_rest_orderbook`
- `async force_market_check`
- `async _find_market_by_slug`
- `async get_active_market`
- `async get_next_market`

### `tbot_logger/poly_orderbook_swarm.py` [TRANSPORT]
- `_handle_task_result`
- `apply_delta`
- `get_formatted_bids`
- `get_formatted_asks`
- `__init__`
- `stop`
- `__init__`
- `_handle_task_result`
- `_fire_and_forget`
- `register_handler`
- `get_status`
- `async run`
- `async start`
- `async subscribe_by_market`
- `async _spawn_socket`
- `async _on_raw_message`
- `async _process_single_msg`
- `async _reaper_loop`
- `async _rotate_socket`
- `async stop`

### `tbot_risk/guards.py` [PLATFORM]
- `__init__`
- `check_all`
- `check_time_guard`
- `check_worst_case`
- `check_budget`
- `check_imbalance`
- `check_pairing`
- `should_panic_exit`

### `tbot_risk/limits.py` [TRANSPORT]
- `__init__`
- `get_deployable_capital`
- `get_available_capital`
- `get_market_budget`
- `can_open_new_market`
- `calculate_clip_size`
- `register_market`
- `update_market`
- `close_market`
- `get_session_stats`
- `adjust_for_drawdown`
- `reset_session`

### `unified_analysis.py` [TRANSPORT]
- `_discover_bots`
- `stats`
- `pct`
- `quantiles`
- `epoch_stat`
- `epoch_pct`
- `fills_metric`
- `epoch_metric`
- `__init__`
- `reset`
- `process`

### `who_is_owner.py` [CORE]
- `scout`
