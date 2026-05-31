# Transport Boundary

Файлы которые общаются с внешним миром: WebSocket, HTTP, ZMQ, etc.
Это границы для transport abstraction.

## `tbot_integration/live_trading_bridge.py` [PLATFORM]
**External imports:** aiohttp, zmq, zmq.asyncio, zmq, zmq

**Transport calls in code:**
- L27 (`zmq`): `import zmq`
- L28 (`zmq`): `import zmq.asyncio`
- L48 (`SUB`): `ZMQ SUB агент. Использует нативный recv_json для минимизации задержек.`
- L51 (`zmq`): `self._ctx = zmq.asyncio.Context()`
- L52 (`zmq`): `self._sock = self._ctx.socket(zmq.SUB)`
- L52 (`SUB`): `self._sock = self._ctx.socket(zmq.SUB)`
- L53 (`zmq`): `self._sock.setsockopt_string(zmq.SUBSCRIBE, "")`
- L54 (`zmq`): `self._sock.setsockopt(zmq.RCVHWM, 5000)`
- L58 (`zmq`): `actual_addr = zmq_addr.replace('zmq://', 'tcp://')`
- L74 (`zmq`): `import zmq # <--- ГАРАНТИРОВАННЫЙ ИМПОРТ ВНУТРИ МЕТОДА`
- L80 (`.get`): `m_type, data = msg.get("type"), msg.get("data", {})`
- L87 (`.get`): `_p = data.get('price', 0)`
- L88 (`.get`): `_s = data.get('size', 0)`
- L89 (`.get`): `_side = str(data.get('side', 'UNKNOWN')).upper()`
- L90 (`.get`): `_asset = str(data.get('asset', 'UNKNOWN')).upper()`
- L91 (`.get`): `_maker = str(data.get('maker_address', ''))[:6]`
- L108 (`.get`): `self.transition_state = data.get('transition_state', 'SUBSCRIBED')`
- L113 (`.get`): `slug = data.get('slug', 'unknown')`
- L114 (`.get`): `t_rem = data.get('time_remaining_sec', 0)`
- L115 (`.get`): `state = data.get('transition_state', 'UNKNOWN')`
- L116 (`.get`): `updates = data.get('updates_count', 0)`
- L117 (`.get`): `trades = data.get('trades_count', 0)`
- L123 (`.get`): `self.last_btc_price = data.get('btc_price', 0.0)`
- L124 (`.get`): `self.last_btc_ts = data.get('btc_ts', 0.0)`
- L125 (`.get`): `self.last_vol_ratio = data.get('vol_ratio', 1.0)`
- L126 (`.get`): `self.last_btc_delta = data.get('btc_delta', 0.0)`
- L181 (`.get`): `self.symbol = config.get('symbol', 'BTC')`
- L182 (`.get`): `self.variant = config.get('variant', 'fifteen')`
- L183 (`.get`): `self.market_duration_sec = config.get('market_duration_sec', 900)`
- L184 (`.get`): `self._binance_ticker_url = config.get('binance_ticker_url', BINANCE_DEFAULT_URL)`

## `tbot_integration/strategy_adapter.py` [PLATFORM]
**Transport calls in code:**
- L70 (`.get`): `bankroll_usd = float(config.get('bankroll_usd', 1000))`
- L75 (`.get`): `base_lot_pct=float(config.get('base_lot_pct', 3)),`
- L76 (`.get`): `max_lot_pct=float(config.get('max_lot_pct', 5)),`
- L77 (`.get`): `imbalance_threshold_pct=float(config.get('imbalance_threshold_pct', 25)),`
- L78 (`.get`): `max_position_pct=float(config.get('max_position_pct', 50)),`
- L79 (`.get`): `min_lot_shares=int(config.get('min_lot_shares', 1))`
- L82 (`.get`): `if config.get('strategy') == 'grid':`
- L103 (`.get`): `self.paper_mode = config.get('paper_mode', True)`
- L137 (`.get`): `self._live_max_usd_per_market = float(config.get('bankroll_usd', 160)) * float(config.get('max_position_pct', 50)) / 100`
- L145 (`.get`): `fillrate_enabled = config.get('fillrate_logging', False) and not self.paper_mode`
- L166 (`.get`): `self._use_calibrated_fills = config.get('use_calibrated_fills', True)`
- L174 (`.get`): `self._qa_queue_discount = params.get('queue_discount', 2.0)`
- L201 (`.get`): `private_key = config.get('private_key') or os.getenv('PRIVATE_KEY') or os.getenv('POLY_PRIVATE_KEY')`
- L202 (`.get`): `funder_address = config.get('funder_address') or os.getenv('FUNDER_ADDRESS')`
- L203 (`.get`): `signature_type = int(config.get('signature_type', os.getenv('POLY_SIGNATURE_TYPE', os.getenv('SIGNATURE_TYPE', '0'))))`
- L206 (`.get`): `api_key = config.get('api_key') or os.getenv('CLOB_API_KEY')`
- L207 (`.get`): `api_secret = config.get('api_secret') or os.getenv('CLOB_SECRET')`
- L208 (`.get`): `api_passphrase = config.get('api_passphrase') or os.getenv('CLOB_PASS_PHRASE')`
- L236 (`.get`): `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- L300 (`.get`): `'entry_threshold': config.get('entry_threshold', '0.98'),`
- L301 (`.get`): `'fees_buffer': config.get('fees_buffer', '0.005'),`
- L302 (`.get`): `'target_profit': config.get('target_profit', '0.02'),`
- L305 (`.get`): `'base_clip_usd': config.get('base_clip_usd', '5'),`
- L306 (`.get`): `'target_size_total_usd': config.get('target_size_total_usd', '100'),`
- L307 (`.get`): `'per_market_budget_usd': config.get('per_market_budget_usd', '100'),`
- L308 (`.get`): `'max_clip_usd': config.get('max_clip_usd', '20'),`
- L311 (`.get`): `'max_imbalance_usd': config.get('max_imbalance_usd', '20'),`
- L312 (`.get`): `'min_pair_ratio': config.get('min_pair_ratio', '0.7'),`
- L313 (`.get`): `'min_pair_ratio_hard': config.get('min_pair_ratio_hard', '0.5'),`
- L316 (`.get`): `'entry_min_time_to_close_sec': config.get('entry_min_time_to_close_sec', 300),`

## `strategies/gabagool/strategy_adapter.py` [PLATFORM]
**Transport calls in code:**
- L64 (`.get`): `bankroll_usd = float(config.get('bankroll_usd', 1000))`
- L69 (`.get`): `base_lot_pct=float(config.get('base_lot_pct', 3)),`
- L70 (`.get`): `max_lot_pct=float(config.get('max_lot_pct', 5)),`
- L71 (`.get`): `imbalance_threshold_pct=float(config.get('imbalance_threshold_pct', 25)),`
- L72 (`.get`): `max_position_pct=float(config.get('max_position_pct', 50)),`
- L73 (`.get`): `min_lot_shares=int(config.get('min_lot_shares', 1))`
- L93 (`.get`): `self.paper_mode = config.get('paper_mode', True)`
- L127 (`.get`): `self._live_max_usd_per_market = float(config.get('bankroll_usd', 160)) * float(config.get('max_position_pct', 50)) / 100`
- L135 (`.get`): `fillrate_enabled = config.get('fillrate_logging', False) and not self.paper_mode`
- L156 (`.get`): `self._use_calibrated_fills = config.get('use_calibrated_fills', True)`
- L164 (`.get`): `self._qa_queue_discount = params.get('queue_discount', 2.0)`
- L191 (`.get`): `private_key = config.get('private_key') or os.getenv('PRIVATE_KEY') or os.getenv('POLY_PRIVATE_KEY')`
- L192 (`.get`): `funder_address = config.get('funder_address') or os.getenv('FUNDER_ADDRESS')`
- L193 (`.get`): `signature_type = int(config.get('signature_type', os.getenv('POLY_SIGNATURE_TYPE', os.getenv('SIGNATURE_TYPE', '0'))))`
- L196 (`.get`): `api_key = config.get('api_key') or os.getenv('CLOB_API_KEY')`
- L197 (`.get`): `api_secret = config.get('api_secret') or os.getenv('CLOB_SECRET')`
- L198 (`.get`): `api_passphrase = config.get('api_passphrase') or os.getenv('CLOB_PASS_PHRASE')`
- L226 (`.get`): `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- L290 (`.get`): `'entry_threshold': config.get('entry_threshold', '0.98'),`
- L291 (`.get`): `'fees_buffer': config.get('fees_buffer', '0.005'),`
- L292 (`.get`): `'target_profit': config.get('target_profit', '0.02'),`
- L295 (`.get`): `'base_clip_usd': config.get('base_clip_usd', '5'),`
- L296 (`.get`): `'target_size_total_usd': config.get('target_size_total_usd', '100'),`
- L297 (`.get`): `'per_market_budget_usd': config.get('per_market_budget_usd', '100'),`
- L298 (`.get`): `'max_clip_usd': config.get('max_clip_usd', '20'),`
- L301 (`.get`): `'max_imbalance_usd': config.get('max_imbalance_usd', '20'),`
- L302 (`.get`): `'min_pair_ratio': config.get('min_pair_ratio', '0.7'),`
- L303 (`.get`): `'min_pair_ratio_hard': config.get('min_pair_ratio_hard', '0.5'),`
- L306 (`.get`): `'entry_min_time_to_close_sec': config.get('entry_min_time_to_close_sec', 300),`
- L307 (`.get`): `'stop_before_close_sec': config.get('stop_before_close_sec', 60),`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/strategy_adapter.py` [PLATFORM]
**Transport calls in code:**
- L59 (`.get`): `bankroll_usd = float(config.get('bankroll_usd', 1000))`
- L64 (`.get`): `base_lot_pct=float(config.get('base_lot_pct', 3)),`
- L65 (`.get`): `max_lot_pct=float(config.get('max_lot_pct', 5)),`
- L66 (`.get`): `imbalance_threshold_pct=float(config.get('imbalance_threshold_pct', 25)),`
- L67 (`.get`): `max_position_pct=float(config.get('max_position_pct', 50)),`
- L68 (`.get`): `min_lot_shares=int(config.get('min_lot_shares', 1))`
- L88 (`.get`): `self.paper_mode = config.get('paper_mode', True)`
- L122 (`.get`): `self._live_max_usd_per_market = float(config.get('bankroll_usd', 160)) * float(config.get('max_position_pct', 50)) / 100`
- L130 (`.get`): `fillrate_enabled = config.get('fillrate_logging', False) and not self.paper_mode`
- L151 (`.get`): `self._use_calibrated_fills = config.get('use_calibrated_fills', True)`
- L159 (`.get`): `self._qa_queue_discount = params.get('queue_discount', 2.0)`
- L186 (`.get`): `private_key = config.get('private_key') or os.getenv('PRIVATE_KEY') or os.getenv('POLY_PRIVATE_KEY')`
- L187 (`.get`): `funder_address = config.get('funder_address') or os.getenv('FUNDER_ADDRESS')`
- L188 (`.get`): `signature_type = int(config.get('signature_type', os.getenv('POLY_SIGNATURE_TYPE', os.getenv('SIGNATURE_TYPE', '0'))))`
- L191 (`.get`): `api_key = config.get('api_key') or os.getenv('CLOB_API_KEY')`
- L192 (`.get`): `api_secret = config.get('api_secret') or os.getenv('CLOB_SECRET')`
- L193 (`.get`): `api_passphrase = config.get('api_passphrase') or os.getenv('CLOB_PASS_PHRASE')`
- L221 (`.get`): `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- L285 (`.get`): `'entry_threshold': config.get('entry_threshold', '0.98'),`
- L286 (`.get`): `'fees_buffer': config.get('fees_buffer', '0.005'),`
- L287 (`.get`): `'target_profit': config.get('target_profit', '0.02'),`
- L290 (`.get`): `'base_clip_usd': config.get('base_clip_usd', '5'),`
- L291 (`.get`): `'target_size_total_usd': config.get('target_size_total_usd', '100'),`
- L292 (`.get`): `'per_market_budget_usd': config.get('per_market_budget_usd', '100'),`
- L293 (`.get`): `'max_clip_usd': config.get('max_clip_usd', '20'),`
- L296 (`.get`): `'max_imbalance_usd': config.get('max_imbalance_usd', '20'),`
- L297 (`.get`): `'min_pair_ratio': config.get('min_pair_ratio', '0.7'),`
- L298 (`.get`): `'min_pair_ratio_hard': config.get('min_pair_ratio_hard', '0.5'),`
- L301 (`.get`): `'entry_min_time_to_close_sec': config.get('entry_min_time_to_close_sec', 300),`
- L302 (`.get`): `'stop_before_close_sec': config.get('stop_before_close_sec', 60),`

## `strategies/gabagool/gabagool_strat.py` [PLATFORM]
**Transport calls in code:**
- L324 (`.get`): `self.paper_mode: bool = self.config.get('paper_mode', True)`
- L327 (`.get`): `self.use_v21 = self.config.get("use_v21", True)  # По умолчанию v2.1`
- L341 (`.get`): `cooldown_sec=float(self.config.get('rebalance_cooldown_sec', 5.0)),`
- L342 (`.get`): `min_imbalance_shares=int(self.config.get('min_imbalance_shares', 5)),`
- L343 (`.get`): `critical_imbalance_pct=float(self.config.get('critical_imbalance_pct', 25.0)),  # v2.8: lowered from 40%`
- L344 (`.get`): `critical_cooldown_sec=float(self.config.get('critical_rebalance_cooldown_sec', 2.0))  # v2.8: 2s min delay`
- L355 (`.get`): `linked_orders_enabled = self.config.get('linked_orders_enabled', True)`
- L360 (`.get`): `lookback_sec=int(self.config.get('roc_lookback_sec', 10)),`
- L361 (`.get`): `max_change_pct=float(self.config.get('roc_max_change_pct', 5.0)),`
- L362 (`.get`): `cooldown_sec=float(self.config.get('roc_cooldown_sec', 5.0))`
- L369 (`.get`): `self.max_natural_spread = float(self.config.get('max_natural_spread', 1.05))`
- L372 (`.get`): `self.bid_sum_max = Decimal(str(self.config.get('bid_sum_max', '0.985')))`
- L373 (`.get`): `self.pair_sum_guard_threshold = float(self.config.get('pair_sum_guard_threshold', 1.005))`
- L374 (`.get`): `self.pair_sum_guard_min_pairs = int(self.config.get('pair_sum_guard_min_pairs', 3))`
- L375 (`.get`): `self.rebalancer_max_drift = float(self.config.get('rebalancer_max_drift', 0.04))`
- L376 (`.get`): `self.momentum_threshold_pct = float(self.config.get('momentum_threshold_pct', 3.0))`
- L377 (`.get`): `self.momentum_lookback_sec = float(self.config.get('momentum_lookback_sec', 10))`
- L378 (`.get`): `self.momentum_activation_sec = float(self.config.get('momentum_activation_sec', 0))`
- L390 (`.get`): `self._target_util_pct: float = float(self.config.get('target_util_pct', 88.0))`
- L394 (`.get`): `self._vpin_enabled: bool = bool(self.config.get('vpin_enabled', False))`
- L395 (`.get`): `self._vpin_threshold: float = float(self.config.get('vpin_threshold', 0.7))`
- L396 (`.get`): `self._vpin_bucket_size: float = float(self.config.get('vpin_bucket_size', 50.0))`
- L397 (`.get`): `self._vpin_window_buckets: int = int(self.config.get('vpin_window_buckets', 10))`
- L404 (`.get`): `self._slippage_edge_pct: float = float(self.config.get('slippage_edge_pct', 0.0))`
- L407 (`.get`): `self._as_enabled: bool = bool(self.config.get('as_enabled', False))`
- L408 (`.get`): `self._risk_aversion_gamma: float = float(self.config.get('risk_aversion_gamma', 0.1))`
- L409 (`.get`): `self._sigma_base: float = float(self.config.get('sigma_base', 0.02))`
- L410 (`.get`): `self._kappa: float = float(self.config.get('kappa', 1.5))`
- L413 (`.get`): `self._sell_enabled: bool = bool(self.config.get('sell_enabled', False))`
- L414 (`.get`): `self._sell_min_shares: int = int(self.config.get('sell_min_shares', 20))`

## `strategies/gabagool/live_trading_bridge.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L83 (`.get`): `self.symbol = config.get('symbol', 'BTC')`
- L84 (`.get`): `self.variant = config.get('variant', 'fifteen')`
- L85 (`.get`): `self.market_duration_sec = config.get('market_duration_sec', 900)`
- L86 (`.get`): `self._binance_ticker_url = config.get('binance_ticker_url', BINANCE_DEFAULT_URL)`
- L157 (`.get`): `strategy_type = self.config.get('strategy', 'legacy')`
- L166 (`.get`): `strategy_config = self.config.get('strategy', {})`
- L168 (`.get`): `strategy_config['bankroll_usd'] = self.config.get('bankroll_usd', 1000)`
- L169 (`.get`): `strategy_config['base_lot_pct'] = self.config.get('base_lot_pct', 3)`
- L170 (`.get`): `strategy_config['max_lot_pct'] = self.config.get('max_lot_pct', 5)`
- L171 (`.get`): `strategy_config['imbalance_threshold_pct'] = self.config.get('imbalance_threshold_pct', 25)`
- L172 (`.get`): `strategy_config['max_position_pct'] = self.config.get('max_position_pct', 50)`
- L173 (`.get`): `strategy_config['min_lot_shares'] = self.config.get('min_lot_shares', 1)`
- L174 (`.get`): `strategy_config['buy_interval'] = self.config.get('buy_interval', 4.0)`
- L177 (`.get`): `strategy_config['max_drawdown_pct'] = self.config.get('max_drawdown_pct', 15.0)`
- L178 (`.get`): `strategy_config['warning_drawdown_pct'] = self.config.get('warning_drawdown_pct', 10.0)`
- L179 (`.get`): `strategy_config['min_edge_pct'] = self.config.get('min_edge_pct', 2.0)`
- L182 (`.get`): `strategy_config['bid_sum_max'] = self.config.get('bid_sum_max', 0.995)`
- L183 (`.get`): `strategy_config['pair_sum_guard_threshold'] = self.config.get('pair_sum_guard_threshold', 1.005)`
- L184 (`.get`): `strategy_config['pair_sum_guard_min_pairs'] = self.config.get('pair_sum_guard_min_pairs', 3)`
- L185 (`.get`): `strategy_config['rebalancer_max_drift'] = self.config.get('rebalancer_max_drift', 0.04)`
- L186 (`.get`): `strategy_config['momentum_threshold_pct'] = self.config.get('momentum_threshold_pct', 3.0)`
- L187 (`.get`): `strategy_config['momentum_lookback_sec'] = self.config.get('momentum_lookback_sec', 10)`
- L188 (`.get`): `strategy_config['momentum_activation_sec'] = self.config.get('momentum_activation_sec', 180)`
- L191 (`.get`): `strategy_config['market_max_loss_pct'] = self.config.get('market_max_loss_pct', 8)`
- L192 (`.get`): `strategy_config['max_imbalance_hard_pct'] = self.config.get('max_imbalance_hard_pct', 40)`
- L193 (`.get`): `strategy_config['max_unpaired_shares'] = self.config.get('max_unpaired_shares', 15)`
- L196 (`.get`): `strategy_config['max_natural_spread'] = self.config.get('max_natural_spread', 1.05)`
- L197 (`.get`): `strategy_config['roc_lookback_sec'] = self.config.get('roc_lookback_sec', 10)`
- L198 (`.get`): `strategy_config['roc_max_change_pct'] = self.config.get('roc_max_change_pct', 5.0)`
- L199 (`.get`): `strategy_config['roc_cooldown_sec'] = self.config.get('roc_cooldown_sec', 5.0)`

## `strategies/gabagool/grid_strategy.py` [PLATFORM]
**Transport calls in code:**
- L1126 (`.get`): `bid_p = market_data.get(f'{side.lower()}_bid', 0.0)`
- L1178 (`.get`): `m_slug = market_data.get('slug', 'unknown')`
- L1182 (`.get`): `_is_off_strike = market_data.get('is_official_strike', False)`
- L1189 (`.get`): `f"🎯🧹 [STRIKE_SYNC_WIPE] Память оракула сброшена! Начинаем новый цикл со страйком {market_data.get('strike_price')}"`
- L1203 (`.get`): `oracle_fv = market_data.get('yes_bid', 0.5) # Это твой Initial placeholder`
- L1221 (`.get`): `yes_bid = market_data.get('yes_bid', 0.5)`
- L1222 (`.get`): `yes_ask = market_data.get('yes_ask', 0.5)`
- L1223 (`.get`): `no_bid = market_data.get('no_bid', 0.5)`
- L1224 (`.get`): `no_ask = market_data.get('no_ask', 0.5)`
- L1226 (`.get`): `api_latency = market_data.get('api_latency_ms', 0)`
- L1233 (`.get`): `raw_t_rem = float(market_data.get('time_remaining_sec', self.config.market_duration_sec))`
- L1266 (`.get`): `open_q = shadow.get('open_q', q_current)`
- L1321 (`.get`): `current_vol_ratio = market_data.get('vol_ratio', 1.0)`
- L1348 (`.get`): `if current_btc == 0: current_btc = market_data.get('btc_price', 0.0)`
- L1356 (`.get`): `if safety.get('early_exit'):`
- L1420 (`.get`): `if preflight.get('early_exit'):`
- L1462 (`.get`): `if oracle.get('early_exit'):`
- L1803 (`.get`): `if orch.get('early_exit'):`
- L1859 (`.get`): `if sync.get('early_exit'):`
- L2004 (`.get`): `if market_data.get('is_blind', False):`
- L2008 (`.get`): `c_mkt = market_data.get('market', market_data.get('market_slug', 'unknown'))`
- L2032 (`.get`): `api_latency = market_data.get('api_latency_ms', 0)`
- L2079 (`.get`): `merge_active_externally = market_data.get('merge_in_progress', False)`
- L2146 (`.get`): `cond_id                  = market_data.get('condition_id')`
- L2239 (`.get`): `'stk_v':       1 if market_data.get('strike_verified', False) else 0,`
- L2316 (`.get`): `self._is_official_strike = market_data.get('strike_verified', False)`
- L2387 (`.get`): `current_btc = market_data.get('btc_price', 0.0)`
- L2392 (`.get`): `strike = float(market_data.get('strike_price') or 0.0)`
- L2394 (`.get`): `self._is_official_strike = bool(market_data.get('strike_verified', False))`
- L2446 (`.get`): `btc_delta          = market_data.get('btc_delta', 0.0)`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/gabagool_strat.py` [PLATFORM]
**Transport calls in code:**
- L324 (`.get`): `self.paper_mode: bool = self.config.get('paper_mode', True)`
- L327 (`.get`): `self.use_v21 = self.config.get("use_v21", True)  # По умолчанию v2.1`
- L341 (`.get`): `cooldown_sec=float(self.config.get('rebalance_cooldown_sec', 5.0)),`
- L342 (`.get`): `min_imbalance_shares=int(self.config.get('min_imbalance_shares', 5)),`
- L343 (`.get`): `critical_imbalance_pct=float(self.config.get('critical_imbalance_pct', 25.0)),  # v2.8: lowered from 40%`
- L344 (`.get`): `critical_cooldown_sec=float(self.config.get('critical_rebalance_cooldown_sec', 2.0))  # v2.8: 2s min delay`
- L355 (`.get`): `linked_orders_enabled = self.config.get('linked_orders_enabled', False)`
- L360 (`.get`): `lookback_sec=int(self.config.get('roc_lookback_sec', 10)),`
- L361 (`.get`): `max_change_pct=float(self.config.get('roc_max_change_pct', 20.0)),`
- L362 (`.get`): `cooldown_sec=float(self.config.get('roc_cooldown_sec', 5.0))`
- L369 (`.get`): `self.max_natural_spread = float(self.config.get('max_natural_spread', 1.05))`
- L372 (`.get`): `self.bid_sum_max = Decimal(str(self.config.get('bid_sum_max', '0.995')))`
- L373 (`.get`): `self.pair_sum_guard_threshold = float(self.config.get('pair_sum_guard_threshold', 1.005))`
- L374 (`.get`): `self.pair_sum_guard_min_pairs = int(self.config.get('pair_sum_guard_min_pairs', 3))`
- L375 (`.get`): `self.rebalancer_max_drift = float(self.config.get('rebalancer_max_drift', 0.04))`
- L376 (`.get`): `self.momentum_threshold_pct = float(self.config.get('momentum_threshold_pct', 3.0))`
- L377 (`.get`): `self.momentum_lookback_sec = float(self.config.get('momentum_lookback_sec', 10))`
- L378 (`.get`): `self.momentum_activation_sec = float(self.config.get('momentum_activation_sec', 180))`
- L403 (`.get`): `max_drawdown_pct=float(self.config.get('max_drawdown_pct', 15.0)),`
- L404 (`.get`): `warning_drawdown_pct=float(self.config.get('warning_drawdown_pct', 10.0)),`
- L407 (`.get`): `min_edge_pct=float(self.config.get('min_edge_pct', 2.0))`
- L417 (`.get`): `custom_phase_configs = self.config.get("custom_phase_configs")`
- L440 (`.get`): `self.buy_interval = self.config.get("buy_interval", 4.0)  # секунд`
- L507 (`.get`): `slug = market_data.get('slug')`
- L515 (`.get`): `time_to_expiry = market_data.get('time_to_expiry')`
- L663 (`.get`): `safe_mode = market_data.get('safe_mode', False)`
- L665 (`.get`): `safe_mode_reason = market_data.get('safe_mode_reason', 'unknown')`
- L674 (`.get`): `self._btc_price = market_data.get('btc_price', 0) or 0`
- L675 (`.get`): `strike_from_bridge = market_data.get('strike_price')`
- L680 (`.get`): `slug = market_data.get('slug')`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/live_trading_bridge.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L83 (`.get`): `self.symbol = config.get('symbol', 'BTC')`
- L84 (`.get`): `self.variant = config.get('variant', 'fifteen')`
- L85 (`.get`): `self.market_duration_sec = config.get('market_duration_sec', 900)`
- L86 (`.get`): `self._binance_ticker_url = config.get('binance_ticker_url', BINANCE_DEFAULT_URL)`
- L139 (`.get`): `strategy_config = self.config.get('strategy', {})`
- L141 (`.get`): `strategy_config['bankroll_usd'] = self.config.get('bankroll_usd', 1000)`
- L142 (`.get`): `strategy_config['base_lot_pct'] = self.config.get('base_lot_pct', 3)`
- L143 (`.get`): `strategy_config['max_lot_pct'] = self.config.get('max_lot_pct', 5)`
- L144 (`.get`): `strategy_config['imbalance_threshold_pct'] = self.config.get('imbalance_threshold_pct', 25)`
- L145 (`.get`): `strategy_config['max_position_pct'] = self.config.get('max_position_pct', 50)`
- L146 (`.get`): `strategy_config['min_lot_shares'] = self.config.get('min_lot_shares', 1)`
- L147 (`.get`): `strategy_config['buy_interval'] = self.config.get('buy_interval', 4.0)`
- L150 (`.get`): `strategy_config['max_drawdown_pct'] = self.config.get('max_drawdown_pct', 15.0)`
- L151 (`.get`): `strategy_config['warning_drawdown_pct'] = self.config.get('warning_drawdown_pct', 10.0)`
- L152 (`.get`): `strategy_config['min_edge_pct'] = self.config.get('min_edge_pct', 2.0)`
- L155 (`.get`): `strategy_config['bid_sum_max'] = self.config.get('bid_sum_max', 0.995)`
- L156 (`.get`): `strategy_config['pair_sum_guard_threshold'] = self.config.get('pair_sum_guard_threshold', 1.005)`
- L157 (`.get`): `strategy_config['pair_sum_guard_min_pairs'] = self.config.get('pair_sum_guard_min_pairs', 3)`
- L158 (`.get`): `strategy_config['rebalancer_max_drift'] = self.config.get('rebalancer_max_drift', 0.04)`
- L159 (`.get`): `strategy_config['momentum_threshold_pct'] = self.config.get('momentum_threshold_pct', 3.0)`
- L160 (`.get`): `strategy_config['momentum_lookback_sec'] = self.config.get('momentum_lookback_sec', 10)`
- L161 (`.get`): `strategy_config['momentum_activation_sec'] = self.config.get('momentum_activation_sec', 180)`
- L164 (`.get`): `strategy_config['market_max_loss_pct'] = self.config.get('market_max_loss_pct', 8)`
- L165 (`.get`): `strategy_config['max_imbalance_hard_pct'] = self.config.get('max_imbalance_hard_pct', 40)`
- L166 (`.get`): `strategy_config['max_unpaired_shares'] = self.config.get('max_unpaired_shares', 15)`
- L169 (`.get`): `strategy_config['max_natural_spread'] = self.config.get('max_natural_spread', 1.05)`
- L170 (`.get`): `strategy_config['roc_lookback_sec'] = self.config.get('roc_lookback_sec', 10)`
- L171 (`.get`): `strategy_config['roc_max_change_pct'] = self.config.get('roc_max_change_pct', 5.0)`
- L172 (`.get`): `strategy_config['roc_cooldown_sec'] = self.config.get('roc_cooldown_sec', 5.0)`
- L175 (`.get`): `strategy_config['fillrate_logging'] = self.config.get('fillrate_logging', False)`

## `tbot_integration/grid_adapter.py` [PLATFORM]
**External imports:** aiohttp, requests, requests

**Transport calls in code:**
- L97 (`.get`): `self.paper_mode = config.get('paper_mode', True)`
- L111 (`.get`): `funder_address=config.get('funder_address', '')`
- L129 (`.get`): `queue_discount=float(config.get('queue_discount', 1.15)),`
- L130 (`.get`): `latency_penalty_ms=float(config.get('latency_penalty_ms', 60.0)),`
- L181 (`.get`): `funder_for_balance = Web3.to_checksum_address(self.config.get('proxy_address'))`
- L182 (`.get`): `sig_type_for_balance = int(self.config.get('signature_type', 2))`
- L201 (`.get`): `f_y = int(float(yes_res.get('availableBalance', 0)) / 1_000_000)`
- L202 (`.get`): `t_y = int(float(yes_res.get('balance', 0)) / 1_000_000)`
- L204 (`.get`): `f_n = int(float(no_res.get('availableBalance', 0)) / 1_000_000)`
- L205 (`.get`): `t_n = int(float(no_res.get('balance', 0)) / 1_000_000)`
- L383 (`.get`): `p_ord = self.strategy.grid_manager.pending_orders.get(oid)`
- L451 (`.get`): `spread_at_creation=max(0.0, self._ob_cache.get('yes_ask', 0.5) - self._ob_cache.get('yes_bid', 0.5)) if hasattr(self, '_`
- L506 (`.get`): `rel_nonce = n_resp.get("nonce")`
- L525 (`.post`): `r = requests.post(`
- L542 (`.get`): `tx_id = result.get('transactionID') or result.get('id')`
- L579 (`.get`): `r = requests.get(f"https://relayer-v2.polymarket.com{path}", headers=headers, timeout=15.0)`
- L583 (`.get`): `curr_state = status_res.get('state', 'UNKNOWN').upper()`
- L722 (`.get`): `self._fill_ob_state.yes_best_bid = float(orderbook.get('yes_bid', 0.50))`
- L723 (`.get`): `self._fill_ob_state.yes_best_ask = float(orderbook.get('yes_ask', 0.50))`
- L724 (`.get`): `self._fill_ob_state.no_best_bid = float(orderbook.get('no_bid', 0.50))`
- L725 (`.get`): `self._fill_ob_state.no_best_ask = float(orderbook.get('no_ask', 0.50))`
- L743 (`.get`): `ts = trade.get('timestamp')`
- L759 (`.get`): `raw_side = str(trade.get('side', 'BUY')).upper()`
- L763 (`.get`): `is_yes=trade.get('is_yes', True),`
- L764 (`.get`): `price=float(trade.get('price', 0)),`
- L765 (`.get`): `size=float(trade.get('size', 0)),`
- L772 (`.get`): `if info.get('is_taker'):`
- L775 (`.get`): `raw_side = info.get('side', '')`
- L779 (`.get`): `placed_at = info.get('timestamp', 0)`
- L786 (`.get`): `price=info.get('price', 0),`

## `archive/dead_2026-03-04/grid_adapter.py` [PLATFORM]
**Transport calls in code:**
- L53 (`.get`): `self.paper_mode = config.get('paper_mode', True)`
- L79 (`.get`): `queue_discount=float(config.get('queue_discount', 2.0)),`
- L80 (`.get`): `latency_penalty_ms=float(config.get('latency_penalty_ms', 200.0)),`
- L258 (`.get`): `self._fill_ob_state.yes_best_bid = float(orderbook.get('yes_bid', 0.50))`
- L259 (`.get`): `self._fill_ob_state.yes_best_ask = float(orderbook.get('yes_ask', 0.50))`
- L260 (`.get`): `self._fill_ob_state.no_best_bid = float(orderbook.get('no_bid', 0.50))`
- L261 (`.get`): `self._fill_ob_state.no_best_ask = float(orderbook.get('no_ask', 0.50))`
- L281 (`.get`): `ts = trade.get('timestamp')`
- L293 (`.get`): `raw_side = str(trade.get('side', 'BUY')).upper()`
- L297 (`.get`): `is_yes=trade.get('is_yes', True),`
- L298 (`.get`): `price=float(trade.get('price', 0)),`
- L299 (`.get`): `size=float(trade.get('size', 0)),`
- L306 (`.get`): `if info.get('is_taker'):`
- L308 (`.get`): `placed_at = info.get('timestamp', 0)`
- L313 (`.get`): `price=info.get('price', 0),`
- L314 (`.get`): `size=info.get('size', 0),`
- L315 (`.get`): `is_yes=(info.get('side', '') == 'YES'),`
- L318 (`.get`): `cumulative_vol=info.get('_cumvol', 0.0),`
- L319 (`.get`): `remaining_size=info.get('size', 0),`
- L337 (`.get`): `self.engine._active_orders[fill.order_id]['_cumvol'] =                     self.engine._active_orders[fill.order_id].get`
- L355 (`.get`): `if info.get('is_taker'):`
- L357 (`.get`): `side = info.get('side', '')`
- L358 (`.get`): `price = info.get('price', 0)`
- L360 (`.get`): `market_bid = float(orderbook.get('yes_bid', 0))`
- L362 (`.get`): `market_bid = float(orderbook.get('no_bid', 0))`
- L364 (`.get`): `self._handle_fill(oid, side, info.get('size', 0), price)`
- L378 (`.get`): `yes = orderbook.get('yes', {})`
- L379 (`.get`): `no = orderbook.get('no', {})`
- L382 (`.get`): `yes_bid = float(yes.get('best_bid', orderbook.get('yes_bid', 0)))`
- L383 (`.get`): `yes_ask = float(yes.get('best_ask', orderbook.get('yes_ask', 0)))`

## `dashboard/server.py` [PLATFORM]
**Transport calls in code:**
- L81 (`.get`): `config = BOT_CONFIGS.get(bot_id)`
- L84 (`.get`): `config_file = config.get('config_file')`
- L119 (`.get`): `config = BOT_CONFIGS.get(bot_id)`
- L144 (`.get`): `config = BOT_CONFIGS.get(bot_id)`
- L147 (`.get`): `state_file = config.get('live_state_file')`
- L158 (`.get`): `config = BOT_CONFIGS.get(bot_id)`
- L173 (`.get`): `bankroll = bot_yaml.get('bankroll_usd', 0) if bot_yaml else 0`
- L200 (`.get`): `bot_mode = (bot_state.get('mode') or 'paper') if bot_state else 'paper'`
- L206 (`.get`): `if bot_state and bot_state.get('bot_status', 'OFFLINE') != 'OFFLINE':`
- L207 (`.get`): `status = bot_state.get('bot_status', 'OFFLINE').lower()`
- L316 (`.get`): `won = sum(1 for r in results if r.get('pnl', 0) > 0)`
- L320 (`.get`): `pnls = [r.get('pnl', 0) for r in results]`
- L323 (`.get`): `total_cost = sum(r.get('total_cost', 0) for r in results)`
- L340 (`.get`): `total_trades = sum(r.get('trades_count', 0) for r in results)`
- L341 (`.get`): `rois = [r.get('roi_pct', 0) for r in results]`
- L378 (`.get`): `condition_id = market_result.get('condition_id') or market_result.get('market_id', '')`
- L395 (`.get`): `bot_cfg = BOT_CONFIGS.get(bot_id, {})`
- L396 (`.get`): `symbol = bot_cfg.get('symbol', 'BTC').lower()`
- L414 (`.get`): `condition_id = market_result.get('condition_id') or market_result.get('market_id', '')`
- L437 (`.get`): `'pnl': market_result.get('pnl', 0),`
- L438 (`.get`): `'winner': market_result.get('winning_side', ''),`
- L457 (`.get`): `config = BOT_CONFIGS.get(bot_id)`
- L460 (`.get`): `state_file = config.get('live_state_file')`
- L465 (`.get`): `cached = _live_state_cache.get(bot_id)`
- L506 (`.get`): `@app.get("/architecture")`
- L519 (`.get`): `@app.get("/monitor")`
- L532 (`.get`): `@app.get("/")`
- L544 (`.get`): `@app.get("/api/markets")`
- L549 (`.get`): `results = [r for r in results if r.get('mode', 'paper') == mode]`
- L552 (`.get`): `@app.get("/api/stats")`

## `archive/mag_knowledge/legacy/Well start here/poly_claim/ctf_core.py` [PLATFORM]
**External imports:** aiohttp, requests

**Transport calls in code:**
- L258 (`.get`): `resp = requests.get(url, headers=headers)`
- L264 (`.get`): `'nonce': data.get('nonce', '0'),`
- L430 (`.post`): `resp = requests.post(url, json=tx_request, headers=headers)`
- L434 (`.get`): `tx_id = result.get('transactionID')`
- L451 (`.get`): `resp = requests.get(url, headers=headers)`
- L456 (`.get`): `state = txn.get('state')`
- L459 (`.get`): `tx_hash = txn.get('transactionHash')`
- L542 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L547 (`.get`): `markets = data.get('markets', [])`
- L554 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L564 (`.get`): `accepting = market.get('acceptingOrders', False)`
- L565 (`.get`): `closed = market.get('closed', False)`
- L568 (`.get`): `'condition_id': market.get('conditionId'),`
- L572 (`.get`): `'question': market.get('question', ''),`
- L576 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`
- L615 (`.get`): `async with session.get(url, timeout=5) as resp:`
- L618 (`.get`): `markets = data.get('markets', [])`
- L621 (`.get`): `market_cond = market.get('conditionId', '').lower()`
- L623 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L630 (`.get`): `'condition_id': market.get('conditionId'),`
- L633 (`.get`): `'slug': market.get('slug') or slug,`
- L634 (`.get`): `'question': market.get('question', ''),`
- L635 (`.get`): `'closed': market.get('closed', False),`
- L636 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`
- L642 (`.get`): `async with session.get(url, timeout=30) as resp:`
- L646 (`.get`): `market_cond = market.get('conditionId', '').lower()`
- L648 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L655 (`.get`): `'condition_id': market.get('conditionId'),`
- L658 (`.get`): `'slug': market.get('slug'),`
- L659 (`.get`): `'question': market.get('question', ''),`

## `archive/hesoyam_with_fill_rate_limits/scripts/health_check.py` [TRANSPORT]
**Transport calls in code:**
- L48 (`.get`): `name = proc.get("name", "unknown")`
- L49 (`.get`): `env = proc.get("pm2_env", {})`
- L51 (`.get`): `"status": env.get("status", "unknown"),`
- L54 (`.get`): `- env.get("pm_uptime", 0)`
- L55 (`.get`): `) if env.get("pm_uptime") else None,`
- L56 (`.get`): `"restarts": env.get("restart_time", 0),`
- L57 (`.get`): `"pid": proc.get("pid", None),`
- L59 (`.get`): `proc.get("monit", {}).get("memory", 0) / (1024 * 1024), 1`
- L61 (`.get`): `"cpu_pct": proc.get("monit", {}).get("cpu", 0),`
- L84 (`.get`): `ts = data.get("timestamp")`
- L89 (`.get`): `"bot_status": data.get("bot_status"),`
- L90 (`.get`): `"mode": data.get("mode"),`
- L91 (`.get`): `"market_slug": data.get("market_slug"),`
- L92 (`.get`): `"time_left_sec": data.get("time_left_sec"),`
- L93 (`.get`): `"wallet_balance": data.get("wallet_balance"),`
- L95 (`.get`): `"position": data.get("position"),`
- L96 (`.get`): `"edge": data.get("edge"),`
- L97 (`.get`): `"risk": data.get("risk"),`
- L98 (`.get`): `"stats": data.get("stats"),`
- L99 (`.get`): `"btc_price": data.get("btc_price"),`
- L198 (`.get`): `pnl = r.get("pnl", 0)`
- L204 (`.get`): `total_edge += r.get("edge_pct", 0)`
- L205 (`.get`): `total_roi += r.get("roi_pct", 0)`
- L207 (`.get`): `avg_fill = r.get("avg_fill_interval_sec")`
- L213 (`.get`): `slippage = r.get("slippage_pct") or r.get("slippage")`
- L227 (`.get`): `"slug": r.get("slug", ""),`
- L229 (`.get`): `"roi_pct": round(r.get("roi_pct", 0), 2),`
- L230 (`.get`): `"edge_pct": round(r.get("edge_pct", 0), 2),`
- L231 (`.get`): `"winning_side": r.get("winning_side"),`
- L232 (`.get`): `"trades_count": r.get("trades_count", 0),`

## `scripts/health_check.py` [TRANSPORT]
**Transport calls in code:**
- L48 (`.get`): `name = proc.get("name", "unknown")`
- L49 (`.get`): `env = proc.get("pm2_env", {})`
- L51 (`.get`): `"status": env.get("status", "unknown"),`
- L54 (`.get`): `- env.get("pm_uptime", 0)`
- L55 (`.get`): `) if env.get("pm_uptime") else None,`
- L56 (`.get`): `"restarts": env.get("restart_time", 0),`
- L57 (`.get`): `"pid": proc.get("pid", None),`
- L59 (`.get`): `proc.get("monit", {}).get("memory", 0) / (1024 * 1024), 1`
- L61 (`.get`): `"cpu_pct": proc.get("monit", {}).get("cpu", 0),`
- L84 (`.get`): `ts = data.get("timestamp")`
- L89 (`.get`): `"bot_status": data.get("bot_status"),`
- L90 (`.get`): `"mode": data.get("mode"),`
- L91 (`.get`): `"market_slug": data.get("market_slug"),`
- L92 (`.get`): `"time_left_sec": data.get("time_left_sec"),`
- L93 (`.get`): `"wallet_balance": data.get("wallet_balance"),`
- L95 (`.get`): `"position": data.get("position"),`
- L96 (`.get`): `"edge": data.get("edge"),`
- L97 (`.get`): `"risk": data.get("risk"),`
- L98 (`.get`): `"stats": data.get("stats"),`
- L99 (`.get`): `"btc_price": data.get("btc_price"),`
- L198 (`.get`): `pnl = r.get("pnl", 0)`
- L204 (`.get`): `total_edge += r.get("edge_pct", 0)`
- L205 (`.get`): `total_roi += r.get("roi_pct", 0)`
- L207 (`.get`): `avg_fill = r.get("avg_fill_interval_sec")`
- L213 (`.get`): `slippage = r.get("slippage_pct") or r.get("slippage")`
- L227 (`.get`): `"slug": r.get("slug", ""),`
- L229 (`.get`): `"roi_pct": round(r.get("roi_pct", 0), 2),`
- L230 (`.get`): `"edge_pct": round(r.get("edge_pct", 0), 2),`
- L231 (`.get`): `"winning_side": r.get("winning_side"),`
- L232 (`.get`): `"trades_count": r.get("trades_count", 0),`

## `strategies/gabagool/execution_engine_v6.py` [PLATFORM]
**Transport calls in code:**
- L214 (`.get`): `market_params = self._token_params_cache.get(token_id, {})`
- L215 (`.get`): `server_fee = market_params.get('fee_bps', 1000)`
- L237 (`.get`): `results = resp if isinstance(resp, list) else resp.get('orderResults', [])`
- L241 (`.get`): `oid = res.get('orderID') if isinstance(res, dict) else (res if isinstance(res, str) else None)`
- L254 (`.get`): `error_msg = res.get('errorMsg') if isinstance(res, dict) else res`
- L260 (`.get`): `o_part = raw_data.get('order', raw_data)`
- L286 (`.get`): `if info.get('is_taker') or 'cancel_requested_at' in info or 'cancel_pending_at' in info:`
- L290 (`.get`): `created_at = info.get('timestamp_send', now)`
- L323 (`.get`): `side = info.get('side', 'UNK')`
- L324 (`.get`): `size = int(info.get('size', 0))`
- L325 (`.get`): `stats[side] = stats.get(side, 0) + size`
- L328 (`.get`): `reason_summary = reasons.get(oid, "PAPER_CANCEL") if reasons else "PAPER_CANCEL"`
- L333 (`.get`): `"target_price": info.get('price', 0), "side": side,`
- L357 (`.get`): `info = self._active_orders.get(oid)`
- L359 (`.get`): `side = info.get('side', 'UNK')`
- L360 (`.get`): `stats[side] = stats.get(side, 0) + int(info.get('size', 0))`
- L363 (`.get`): `life_time_ms = int((time.time() - info.get('timestamp_send', time.time())) * 1000)`
- L366 (`.get`): `"target_price": info.get('price', 0), "side": side, "reason": unique_reasons`
- L397 (`.get`): `logger.info(f"☢️ [NUCLEAR PAPER] Killed {info.get('side', '')} {info.get('size', 0)}@{info.get('price', 0)}")`
- L405 (`.get`): `logger.info(f"☢️ [NUCLEAR ITEM] Killed {info.get('side', 'UNKNOWN')} {info.get('size', 0)}@{info.get('price', 0)} | ID: `
- L408 (`.get`): `life_time_ms = int((now - info.get('timestamp_send', now)) * 1000)`
- L411 (`.get`): `"target_price": info.get('price', 0), "side": info.get('side', 'UNKNOWN'),`
- L496 (`.get`): `market_params = self._token_params_cache.get(token_id, {})`
- L497 (`.get`): `server_fee = market_params.get('fee_bps', 1000) # Берем из кэша, как в мейкерах`
- L520 (`.get`): `oid = resp.get('orderID') if isinstance(resp, dict) else None`
- L547 (`.get`): `info = self._active_orders.get(order_id)`
- L561 (`.get`): `side = info.get('side', '')`
- L562 (`.get`): `is_taker = info.get('is_taker', False)`
- L563 (`.get`): `lvl_tag = f"L{info.get('level_idx', '?')}"`
- L565 (`.get`): `target_price = info.get('price', price)`

## `scripts/claim_resolved.py` [PLATFORM]
**External imports:** requests, requests

**Transport calls in code:**
- L161 (`.get`): `if info.get('ts', 0) >= cutoff}`
- L185 (`.get`): `r = requests.get('https://gamma-api.polymarket.com/markets',`
- L189 (`.get`): `token_ids = _parse_token_ids(m.get('clobTokenIds', []))`
- L191 (`.get`): `'condition_id': m.get('conditionId', ''),`
- L193 (`.get`): `'resolved': (m.get('resolved', False) or`
- L194 (`.get`): `m.get('umaResolutionStatus') == 'resolved'),`
- L195 (`.get`): `'outcome_prices': m.get('outcomePrices', []),`
- L196 (`.get`): `'closed': m.get('closed', False),`
- L224 (`.get`): `for tid in info.get('token_ids', []):`
- L242 (`.get`): `slug = token_to_slug.get(tid)`
- L246 (`.get`): `cond = token_cache[slug].get('condition_id', '')`
- L249 (`.get`): `'token_ids': token_cache[slug].get('token_ids', []),`
- L255 (`.get`): `elif queue[slug].get('status') == 'claimed':`
- L284 (`.get`): `slug = entry.get('market_slug') or entry.get('slug', '')`
- L288 (`.get`): `cond = entry.get('condition_id', '')`
- L289 (`.get`): `token_ids = entry.get('token_ids', [])`
- L292 (`.get`): `cond = info.get('condition_id', '')`
- L293 (`.get`): `token_ids = info.get('token_ids', [])`
- L330 (`.get`): `slug = state.get('market_slug', '')`
- L331 (`.get`): `cond = state.get('condition_id', '')`
- L333 (`.get`): `yes_s = state.get('yes_shares', 0) or 0`
- L334 (`.get`): `no_s  = state.get('no_shares', 0) or 0`
- L341 (`.get`): `cond = info.get('condition_id', '')`
- L342 (`.get`): `token_ids = info.get('token_ids', [])`
- L344 (`.get`): `token_ids = token_cache.get(slug, {}).get('token_ids', [])`
- L347 (`.get`): `token_ids = info.get('token_ids', [])`
- L402 (`.get`): `token_ids = token_cache.get(slug, {}).get('token_ids', [])`
- L405 (`.get`): `token_ids = info.get('token_ids', [])`
- L440 (`.get`): `r = requests.get(`
- L455 (`.get`): `markets = markets.get('data', [])`

## `backtester/reporting/funnel_report.py` [TRANSPORT]
**Transport calls in code:**
- L40 (`.get`): `meta_s = screening_data.get('metadata', {})`
- L41 (`.get`): `meta_f = funnel_data.get('metadata', {})`
- L42 (`.get`): `symbol = meta_f.get('symbol', meta_s.get('symbol', '?')).upper()`
- L43 (`.get`): `market_type = meta_f.get('market_type', meta_s.get('market_type', '?'))`
- L44 (`.get`): `deposit = meta_f.get('deposit', meta_s.get('deposit', '?'))`
- L45 (`.get`): `n_markets = meta_f.get('n_markets', meta_s.get('n_markets', '?'))`
- L55 (`.get`): `stages = meta_f.get('stages', {})`
- L56 (`.get`): `lhs_samples = meta_s.get('samples', '?')`
- L57 (`.get`): `lines.append(f"**Pipeline:** LHS({lhs_samples}) → Multi-Start(5×{stages.get('phase2_trials_per_run', '?')}) → Block Refi`
- L58 (`.get`): `total_trials = int(lhs_samples or 0) + 5 * int(stages.get('phase2_trials_per_run', 0)) + 5 * int(stages.get('phase3_tria`
- L74 (`.get`): `sensitivity = screening_data.get('sensitivity', {})`
- L75 (`.get`): `significant = screening_data.get('significant_params', [])`
- L76 (`.get`): `frozen = screening_data.get('frozen_params', {})`
- L102 (`.get`): `lhs_results = screening_data.get('results', [])`
- L111 (`.get`): `lines.append(f"| {i+1} | {r['name']} | ${m['median_pnl']:.4f} | {m['win_rate']:.1f}% | {m['sharpe']:.3f} | ${m['worst_dd`
- L121 (`.get`): `top_configs = funnel_data.get('top_configs', [])`
- L129 (`.get`): `m = t.get('metrics', {})`
- L130 (`.get`): `lines.append(f"| #{t.get('rank', '?')} | {t.get('score', 0):.4f} | "`
- L131 (`.get`): `f"${m.get('median_pnl', 0):.4f} | "`
- L132 (`.get`): `f"{m.get('win_rate', 0):.1f}% | "`
- L133 (`.get`): `f"{m.get('sharpe', 0):.3f} | "`
- L134 (`.get`): `f"${m.get('worst_dd', 0):.2f} | "`
- L135 (`.get`): `f"{t.get('study', '?')} |")`
- L141 (`.get`): `params = best.get('params', {})`
- L147 (`.get`): `val = params.get(p, DEFAULTS.get(p, '?'))`
- L148 (`.get`): `default = DEFAULTS.get(p, '?')`
- L163 (`.get`): `v = t.get('params', {}).get(p)`
- L170 (`.get`): `header = "| Param | " + " | ".join(f"#{t.get('rank', i+1)}" for i, t in enumerate(top_configs)) + " |"`
- L175 (`.get`): `vals = [str(t.get('params', {}).get(p, '?')) for t in top_configs]`
- L191 (`.get`): `lines.append(f"| Multi-Start | 5 × {stages.get('phase2_trials_per_run', '?')} | 5 priors, TPE |")`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/bvmm_strategy.py` [PLATFORM]
**Transport calls in code:**
- L153 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L154 (`.get`): `self.fees_buffer = Decimal(str(config.get('fees_buffer', '0.005')))`
- L155 (`.get`): `self.target_profit = Decimal(str(config.get('target_profit', '0.02')))`
- L161 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', '5')))`
- L162 (`.get`): `self.target_size_total_usd = Decimal(str(config.get('target_size_total_usd', '100')))`
- L163 (`.get`): `self.per_market_budget_usd = Decimal(str(config.get('per_market_budget_usd', '100')))`
- L164 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', '20')))`
- L167 (`.get`): `self.max_imbalance_usd = Decimal(str(config.get('max_imbalance_usd', '20')))`
- L168 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.7')))`
- L169 (`.get`): `self.min_pair_ratio_hard = Decimal(str(config.get('min_pair_ratio_hard', '0.5')))`
- L172 (`.get`): `self.entry_min_time_to_close_sec = config.get('entry_min_time_to_close_sec', 300)`
- L173 (`.get`): `self.stop_before_close_sec = config.get('stop_before_close_sec', 60)`
- L176 (`.get`): `self.tick_size = Decimal(str(config.get('tick_size', '0.01')))`
- L177 (`.get`): `self.improve_ticks = config.get('improve_ticks', 1)`
- L178 (`.get`): `self.replace_cooldown_ms = config.get('replace_cooldown_ms', 2000)`
- L181 (`.get`): `self.min_bid_depth_usd = Decimal(str(config.get('min_bid_depth_usd', '50')))`
- L184 (`.get`): `self.max_worst_case_loss_usd = Decimal(str(config.get('max_worst_case_loss_usd', '10')))`
- L246 (`.get`): `time_to_expiry = market_data.get('time_to_expiry', 0)`
- L286 (`.get`): `is_yes = market_data.get('is_yes')`
- L287 (`.get`): `bids = market_data.get('bids', [])`
- L288 (`.get`): `asks = market_data.get('asks', [])`
- L308 (`.get`): `bids = book.get('bids', [])`
- L312 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L314 (`.get`): `Decimal(str(best.get('price', 0))),`
- L315 (`.get`): `Decimal(str(best.get('size', 0)))`
- L325 (`.get`): `asks = book.get('asks', [])`
- L329 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L331 (`.get`): `Decimal(str(best.get('price', 0))),`
- L332 (`.get`): `Decimal(str(best.get('size', 0)))`
- L337 (`.get`): `bids = book.get('bids', [])`

## `tbot_integration/bvmm_strategy.py` [PLATFORM]
**Transport calls in code:**
- L153 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L154 (`.get`): `self.fees_buffer = Decimal(str(config.get('fees_buffer', '0.005')))`
- L155 (`.get`): `self.target_profit = Decimal(str(config.get('target_profit', '0.02')))`
- L161 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', '5')))`
- L162 (`.get`): `self.target_size_total_usd = Decimal(str(config.get('target_size_total_usd', '100')))`
- L163 (`.get`): `self.per_market_budget_usd = Decimal(str(config.get('per_market_budget_usd', '100')))`
- L164 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', '20')))`
- L167 (`.get`): `self.max_imbalance_usd = Decimal(str(config.get('max_imbalance_usd', '20')))`
- L168 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.7')))`
- L169 (`.get`): `self.min_pair_ratio_hard = Decimal(str(config.get('min_pair_ratio_hard', '0.5')))`
- L172 (`.get`): `self.entry_min_time_to_close_sec = config.get('entry_min_time_to_close_sec', 300)`
- L173 (`.get`): `self.stop_before_close_sec = config.get('stop_before_close_sec', 60)`
- L176 (`.get`): `self.tick_size = Decimal(str(config.get('tick_size', '0.01')))`
- L177 (`.get`): `self.improve_ticks = config.get('improve_ticks', 1)`
- L178 (`.get`): `self.replace_cooldown_ms = config.get('replace_cooldown_ms', 2000)`
- L181 (`.get`): `self.min_bid_depth_usd = Decimal(str(config.get('min_bid_depth_usd', '50')))`
- L184 (`.get`): `self.max_worst_case_loss_usd = Decimal(str(config.get('max_worst_case_loss_usd', '10')))`
- L246 (`.get`): `time_to_expiry = market_data.get('time_to_expiry', 0)`
- L286 (`.get`): `is_yes = market_data.get('is_yes')`
- L287 (`.get`): `bids = market_data.get('bids', [])`
- L288 (`.get`): `asks = market_data.get('asks', [])`
- L308 (`.get`): `bids = book.get('bids', [])`
- L312 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L314 (`.get`): `Decimal(str(best.get('price', 0))),`
- L315 (`.get`): `Decimal(str(best.get('size', 0)))`
- L325 (`.get`): `asks = book.get('asks', [])`
- L329 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L331 (`.get`): `Decimal(str(best.get('price', 0))),`
- L332 (`.get`): `Decimal(str(best.get('size', 0)))`
- L337 (`.get`): `bids = book.get('bids', [])`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/ws_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L26 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')`
- L49 (`.get`): `yes_token = market_data.get('yes_token')`
- L50 (`.get`): `no_token = market_data.get('no_token')`
- L69 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L108 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L110 (`.get`): `yes_token = market_data.get('yes_token')`
- L111 (`.get`): `no_token = market_data.get('no_token')`
- L120 (`.get`): `asset_id = message.get('asset_id')`
- L121 (`.get`): `market = message.get('market')  # This is condition_id`
- L127 (`.get`): `yes_token = market_data.get('yes_token')`
- L128 (`.get`): `no_token = market_data.get('no_token')`
- L140 (`.get`): `for level in message.get('bids', []):`
- L146 (`.get`): `for level in message.get('asks', []):`
- L164 (`.get`): `yes_book = self.orderbooks[market].get(yes_token, {})`
- L165 (`.get`): `no_book = self.orderbooks[market].get(no_token, {})`
- L167 (`.get`): `if yes_book.get('bids') and yes_book.get('asks') and no_book.get('bids') and no_book.get('asks'):`
- L168 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L172 (`.get`): `market = message.get('market')`
- L173 (`.get`): `asset_id = message.get('asset_id')`
- L174 (`.get`): `side = message.get('side')`
- L175 (`.get`): `price = message.get('price')`
- L176 (`.get`): `size = message.get('size')`
- L207 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L212 (`.get`): `f"Trade: {message.get('side')} {message.get('size')}@{message.get('price')} "`
- L213 (`.get`): `f"fee_rate: {message.get('fee_rate_bps')}bps"`
- L218 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L222 (`.get`): `market_books = self.orderbooks.get(condition_id, {})`
- L223 (`.get`): `yes_token = market_data.get('yes_token')`
- L224 (`.get`): `no_token = market_data.get('no_token')`
- L226 (`.get`): `yes_book = market_books.get(yes_token, {})`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/api/ws_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L26 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')`
- L49 (`.get`): `yes_token = market_data.get('yes_token')`
- L50 (`.get`): `no_token = market_data.get('no_token')`
- L69 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L108 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L110 (`.get`): `yes_token = market_data.get('yes_token')`
- L111 (`.get`): `no_token = market_data.get('no_token')`
- L120 (`.get`): `asset_id = message.get('asset_id')`
- L121 (`.get`): `market = message.get('market')  # This is condition_id`
- L127 (`.get`): `yes_token = market_data.get('yes_token')`
- L128 (`.get`): `no_token = market_data.get('no_token')`
- L140 (`.get`): `for level in message.get('bids', []):`
- L146 (`.get`): `for level in message.get('asks', []):`
- L164 (`.get`): `yes_book = self.orderbooks[market].get(yes_token, {})`
- L165 (`.get`): `no_book = self.orderbooks[market].get(no_token, {})`
- L167 (`.get`): `if yes_book.get('bids') and yes_book.get('asks') and no_book.get('bids') and no_book.get('asks'):`
- L168 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L172 (`.get`): `market = message.get('market')`
- L173 (`.get`): `asset_id = message.get('asset_id')`
- L174 (`.get`): `side = message.get('side')`
- L175 (`.get`): `price = message.get('price')`
- L176 (`.get`): `size = message.get('size')`
- L207 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L212 (`.get`): `f"Trade: {message.get('side')} {message.get('size')}@{message.get('price')} "`
- L213 (`.get`): `f"fee_rate: {message.get('fee_rate_bps')}bps"`
- L218 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L222 (`.get`): `market_books = self.orderbooks.get(condition_id, {})`
- L223 (`.get`): `yes_token = market_data.get('yes_token')`
- L224 (`.get`): `no_token = market_data.get('no_token')`
- L226 (`.get`): `yes_book = market_books.get(yes_token, {})`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/ws_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L26 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')`
- L49 (`.get`): `yes_token = market_data.get('yes_token')`
- L50 (`.get`): `no_token = market_data.get('no_token')`
- L69 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L108 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L110 (`.get`): `yes_token = market_data.get('yes_token')`
- L111 (`.get`): `no_token = market_data.get('no_token')`
- L120 (`.get`): `asset_id = message.get('asset_id')`
- L121 (`.get`): `market = message.get('market')  # This is condition_id`
- L127 (`.get`): `yes_token = market_data.get('yes_token')`
- L128 (`.get`): `no_token = market_data.get('no_token')`
- L140 (`.get`): `for level in message.get('bids', []):`
- L146 (`.get`): `for level in message.get('asks', []):`
- L164 (`.get`): `yes_book = self.orderbooks[market].get(yes_token, {})`
- L165 (`.get`): `no_book = self.orderbooks[market].get(no_token, {})`
- L167 (`.get`): `if yes_book.get('bids') and yes_book.get('asks') and no_book.get('bids') and no_book.get('asks'):`
- L168 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L172 (`.get`): `market = message.get('market')`
- L173 (`.get`): `asset_id = message.get('asset_id')`
- L174 (`.get`): `side = message.get('side')`
- L175 (`.get`): `price = message.get('price')`
- L176 (`.get`): `size = message.get('size')`
- L207 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L212 (`.get`): `f"Trade: {message.get('side')} {message.get('size')}@{message.get('price')} "`
- L213 (`.get`): `f"fee_rate: {message.get('fee_rate_bps')}bps"`
- L218 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L222 (`.get`): `market_books = self.orderbooks.get(condition_id, {})`
- L223 (`.get`): `yes_token = market_data.get('yes_token')`
- L224 (`.get`): `no_token = market_data.get('no_token')`
- L226 (`.get`): `yes_book = market_books.get(yes_token, {})`

## `backtester/optimizer/param_space.py` [TRANSPORT]
**Transport calls in code:**
- L486 (`.get`): `lambda p: p.get('imbalance_stop_pct', 25) > p.get('imbalance_rebalance_pct', 15),`
- L488 (`.get`): `lambda p: p.get('lot_size', 12) >= 5,`
- L490 (`.get`): `lambda p: p.get('depth_thin_threshold', 50) < p.get('depth_thick_threshold', 200),`
- L492 (`.get`): `lambda p: p.get('bid_sum_threshold_build', 0.955) <= p.get('bid_sum_threshold', 0.97),`
- L494 (`.get`): `lambda p: p.get('imbalance_rebalance_pct_build', 25) >= p.get('imbalance_rebalance_pct', 15),`
- L523 (`.get`): `cap = LOT_CAPS.get(bankroll, 60)`
- L573 (`.get`): `lot_cap = LOT_CAPS.get(bankroll, 60)`
- L577 (`.get`): `ladder = full.get('ladder_levels', 1)`
- L591 (`.get`): `ims = full.get('imbalance_min_shares')`
- L622 (`.get`): `recovery_max_ask_price=float(full.get('recovery_max_ask_price', 0.70)),`
- L647 (`.get`): `slippage_edge_pct=float(full.get('slippage_edge_pct', 0.4)),`
- L652 (`.get`): `vpin_threshold=float(full.get('vpin_threshold', 0.7)),`
- L653 (`.get`): `vpin_bucket_size=float(full.get('vpin_bucket_size', 50.0)),`
- L654 (`.get`): `vpin_window_buckets=int(full.get('vpin_window_buckets', 10)),`
- L656 (`.get`): `as_enabled=bool(full.get('as_enabled', False)),`
- L657 (`.get`): `risk_aversion_gamma=float(full.get('risk_aversion_gamma', 0.1)),`
- L658 (`.get`): `sigma_base=float(full.get('sigma_base', 0.02)),`
- L659 (`.get`): `kappa=float(full.get('kappa', 1.5)),`
- L661 (`.get`): `sell_enabled=bool(full.get('sell_enabled', False)),`
- L662 (`.get`): `sell_min_shares=int(full.get('sell_min_shares', 20)),`
- L663 (`.get`): `sell_imb_threshold=float(full.get('sell_imb_threshold', 25.0)),`
- L664 (`.get`): `sell_util_threshold=float(full.get('sell_util_threshold', 0.7)),`
- L665 (`.get`): `sell_min_time_pct=float(full.get('sell_min_time_pct', 0.3)),`
- L666 (`.get`): `sell_target_imbalance=float(full.get('sell_target_imbalance', 10.0)),`
- L668 (`.get`): `target_util_pct=float(full.get('target_util_pct', 88.0)),`
- L669 (`.get`): `bid_sum_threshold_build=float(full.get(`
- L671 (`.get`): `imbalance_rebalance_pct_build=float(full.get(`
- L673 (`.get`): `lot_multiplier_max=float(full.get('lot_multiplier_max', 1.5)),`
- L702 (`.get`): `if spec.get('ordinal', False) and len(values) > 2:`
- L717 (`.get`): `spec = PARAM_SPACE.get(real_name)`

## `tbot_core/api/ws_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L26 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')`
- L49 (`.get`): `yes_token = market_data.get('yes_token')`
- L50 (`.get`): `no_token = market_data.get('no_token')`
- L69 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L108 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L110 (`.get`): `yes_token = market_data.get('yes_token')`
- L111 (`.get`): `no_token = market_data.get('no_token')`
- L120 (`.get`): `asset_id = message.get('asset_id')`
- L121 (`.get`): `market = message.get('market')  # This is condition_id`
- L127 (`.get`): `yes_token = market_data.get('yes_token')`
- L128 (`.get`): `no_token = market_data.get('no_token')`
- L140 (`.get`): `for level in message.get('bids', []):`
- L146 (`.get`): `for level in message.get('asks', []):`
- L164 (`.get`): `yes_book = self.orderbooks[market].get(yes_token, {})`
- L165 (`.get`): `no_book = self.orderbooks[market].get(no_token, {})`
- L167 (`.get`): `if yes_book.get('bids') and yes_book.get('asks') and no_book.get('bids') and no_book.get('asks'):`
- L168 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L172 (`.get`): `market = message.get('market')`
- L173 (`.get`): `asset_id = message.get('asset_id')`
- L174 (`.get`): `side = message.get('side')`
- L175 (`.get`): `price = message.get('price')`
- L176 (`.get`): `size = message.get('size')`
- L207 (`.get`): `await self._dispatch_update(market, message.get('timestamp', str(int(time.time() * 1000))))`
- L212 (`.get`): `f"Trade: {message.get('side')} {message.get('size')}@{message.get('price')} "`
- L213 (`.get`): `f"fee_rate: {message.get('fee_rate_bps')}bps"`
- L218 (`.get`): `market_data = self.subscribed_markets.get(condition_id)`
- L222 (`.get`): `market_books = self.orderbooks.get(condition_id, {})`
- L223 (`.get`): `yes_token = market_data.get('yes_token')`
- L224 (`.get`): `no_token = market_data.get('no_token')`
- L226 (`.get`): `yes_book = market_books.get(yes_token, {})`

## `tbot_logger/orderbook_logger.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L58 (`.get`): `self._tag_id = MARKET_TAG_IDS.get(variant, '102467')`
- L182 (`.get`): `is_yes = message.get('is_yes')`
- L183 (`.get`): `asset_id = message.get('yes_token_id') if is_yes else message.get('no_token_id')`
- L186 (`.get`): `bids = message.get('bids', [])`
- L187 (`.get`): `asks = message.get('asks', [])`
- L189 (`.get`): `timestamp = str(int(message.get('timestamp', time.time()) * 1000))`
- L219 (`.get`): `if isinstance(lev, dict): return float(lev.get('price' if i==0 else 'size'))`
- L267 (`.get`): `is_yes = message.get('is_yes', False)`
- L268 (`.get`): `price = message.get('price', 0)`
- L269 (`.get`): `size = message.get('size', 0)`
- L270 (`.get`): `side = message.get('side', 'unknown')`
- L549 (`.get`): `async with session.get(yes_url, params=yes_params) as resp:`
- L556 (`.get`): `'bids': yes_data.get('bids', []),`
- L557 (`.get`): `'asks': yes_data.get('asks', []),`
- L565 (`.get`): `'bids': yes_data.get('bids', []),`
- L566 (`.get`): `'asks': yes_data.get('asks', []),`
- L579 (`.get`): `async with session.get(no_url, params=no_params) as resp:`
- L586 (`.get`): `'bids': no_data.get('bids', []),`
- L587 (`.get`): `'asks': no_data.get('asks', []),`
- L643 (`.get`): `async with session.get(url, params={'slug': slug}, timeout=aiohttp.ClientTimeout(total=5)) as resp:`
- L648 (`.get`): `markets = event.get('markets', [])`
- L650 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L651 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L660 (`.get`): `'condition_id': market.get('conditionId'),`
- L663 (`.get`): `'slug': market.get('slug'),`
- L682 (`.get`): `async with session.get(url, params=params) as response:`
- L698 (`.get`): `event_slug = event.get('slug', '')`
- L703 (`.get`): `markets = event.get('markets', [])`
- L705 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L706 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`

## `archive/dead_2026-03-04/ws_implementation_code.py` [PLATFORM]
**External imports:** aiohttp, aiohttp

**Transport calls in code:**
- L234 (`.get`): `event_type = data.get('event_type')`
- L238 (`.get`): `asset_id = data.get('asset_id')`
- L246 (`.get`): `'market':    data.get('market'),`
- L249 (`.get`): `'bids':      data.get('bids', []),`
- L250 (`.get`): `'asks':      data.get('asks', []),`
- L251 (`.get`): `'timestamp': data.get('timestamp'),`
- L256 (`.get`): `asset_id = data.get('asset_id')`
- L264 (`.get`): `'market':    data.get('market'),`
- L267 (`.get`): `'price':     float(data.get('price', 0)),`
- L268 (`.get`): `'size':      float(data.get('size', 0)),`
- L269 (`.get`): `'side':      data.get('side', 'unknown'),`
- L270 (`.get`): `'timestamp': data.get('timestamp'),`
- L527 (`.get`): `self._tag_id = MARKET_TAG_IDS.get(variant, '102467')`
- L599 (`.get`): `asset_id  = message.get('asset_id')`
- L600 (`.get`): `is_yes    = message.get('is_yes')`
- L601 (`.get`): `bids      = message.get('bids', [])`
- L602 (`.get`): `asks      = message.get('asks', [])`
- L603 (`.get`): `timestamp = message.get('timestamp', str(int(time.time() * 1000)))`
- L604 (`.get`): `source    = message.get('source', 'ws')   # 'ws' or 'rest'`
- L829 (`.get`): `async with session.get(f"{clob_base}/book", params={'token_id': token_id}) as resp:`
- L835 (`.get`): `'bids':      book.get('bids', []),`
- L836 (`.get`): `'asks':      book.get('asks', []),`
- L865 (`.get`): `async with session.get(url, params=params) as resp:`
- L875 (`.get`): `slug = event.get('slug', '')`
- L878 (`.get`): `for market in event.get('markets', []):`
- L879 (`.get`): `if not market.get('acceptingOrders') or market.get('closed'):`
- L881 (`.get`): `token_ids = json.loads(market.get('clobTokenIds', '[]'))`
- L931 (`.get`): `async with session.get(url, params={'slug': slug},`
- L938 (`.get`): `for market in events[0].get('markets', []):`
- L939 (`.get`): `if not market.get('acceptingOrders') or market.get('closed'):`

## `archive/hesoyam_with_fill_rate_limits/tbot_logger/orderbook_logger.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L52 (`.get`): `self._tag_id = MARKET_TAG_IDS.get(variant, '102467')`
- L149 (`.get`): `asset_id = message.get('asset_id')`
- L150 (`.get`): `is_yes = message.get('is_yes')`
- L151 (`.get`): `bids = message.get('bids', [])`
- L152 (`.get`): `asks = message.get('asks', [])`
- L153 (`.get`): `timestamp = message.get('timestamp', str(int(time.time() * 1000)))`
- L163 (`.get`): `best_bid = max([float(b.get('price', 0)) for b in bids]) if bids else 0`
- L164 (`.get`): `best_ask = min([float(a.get('price', 1)) for a in asks]) if asks else 1`
- L241 (`.get`): `is_yes = message.get('is_yes', False)`
- L242 (`.get`): `price = message.get('price', 0)`
- L243 (`.get`): `size = message.get('size', 0)`
- L244 (`.get`): `side = message.get('side', 'unknown')`
- L536 (`.get`): `async with session.get(yes_url, params=yes_params) as resp:`
- L544 (`.get`): `'bids': yes_data.get('bids', []),`
- L545 (`.get`): `'asks': yes_data.get('asks', []),`
- L556 (`.get`): `async with session.get(no_url, params=no_params) as resp:`
- L563 (`.get`): `'bids': no_data.get('bids', []),`
- L564 (`.get`): `'asks': no_data.get('asks', []),`
- L618 (`.get`): `async with session.get(url, params={'slug': slug}, timeout=aiohttp.ClientTimeout(total=5)) as resp:`
- L623 (`.get`): `markets = event.get('markets', [])`
- L625 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L626 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L635 (`.get`): `'condition_id': market.get('conditionId'),`
- L638 (`.get`): `'slug': market.get('slug'),`
- L657 (`.get`): `async with session.get(url, params=params) as response:`
- L673 (`.get`): `event_slug = event.get('slug', '')`
- L678 (`.get`): `markets = event.get('markets', [])`
- L680 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L681 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L701 (`.get`): `'condition_id': market.get('conditionId'),`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/ws_user_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L32 (`.get`): `trade_id=data.get('id', ''),`
- L33 (`.get`): `taker_order_id=data.get('taker_order_id', ''),`
- L34 (`.get`): `asset_id=data.get('asset_id', ''),`
- L35 (`.get`): `market=data.get('market', ''),`
- L36 (`.get`): `side=data.get('side', ''),`
- L37 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L38 (`.get`): `size=Decimal(str(data.get('size', '0'))),`
- L39 (`.get`): `outcome=data.get('outcome', ''),`
- L40 (`.get`): `status=data.get('status', ''),`
- L42 (`.get`): `int(data.get('matchtime', '0')),`
- L45 (`.get`): `maker_orders=data.get('maker_orders', [])`
- L73 (`.get`): `order_id=data.get('id', ''),`
- L74 (`.get`): `asset_id=data.get('asset_id', ''),`
- L75 (`.get`): `market=data.get('market', ''),`
- L76 (`.get`): `side=data.get('side', ''),`
- L77 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L78 (`.get`): `original_size=Decimal(str(data.get('original_size', '0'))),`
- L79 (`.get`): `size_matched=Decimal(str(data.get('size_matched', '0'))),`
- L80 (`.get`): `outcome=data.get('outcome', ''),`
- L81 (`.get`): `event_type=data.get('type', ''),`
- L83 (`.get`): `int(data.get('timestamp', '0')),`
- L103 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/user')`
- L104 (`.get`): `self.api_key = config.get('api_key')`
- L105 (`.get`): `self.api_secret = config.get('api_secret')`
- L106 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L169 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L174 (`.get`): `event_type = data.get('event_type')`
- L224 (`ws\.recv`): `message = await self.ws.recv()`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/api/ws_user_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L32 (`.get`): `trade_id=data.get('id', ''),`
- L33 (`.get`): `taker_order_id=data.get('taker_order_id', ''),`
- L34 (`.get`): `asset_id=data.get('asset_id', ''),`
- L35 (`.get`): `market=data.get('market', ''),`
- L36 (`.get`): `side=data.get('side', ''),`
- L37 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L38 (`.get`): `size=Decimal(str(data.get('size', '0'))),`
- L39 (`.get`): `outcome=data.get('outcome', ''),`
- L40 (`.get`): `status=data.get('status', ''),`
- L42 (`.get`): `int(data.get('matchtime', '0')),`
- L45 (`.get`): `maker_orders=data.get('maker_orders', [])`
- L73 (`.get`): `order_id=data.get('id', ''),`
- L74 (`.get`): `asset_id=data.get('asset_id', ''),`
- L75 (`.get`): `market=data.get('market', ''),`
- L76 (`.get`): `side=data.get('side', ''),`
- L77 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L78 (`.get`): `original_size=Decimal(str(data.get('original_size', '0'))),`
- L79 (`.get`): `size_matched=Decimal(str(data.get('size_matched', '0'))),`
- L80 (`.get`): `outcome=data.get('outcome', ''),`
- L81 (`.get`): `event_type=data.get('type', ''),`
- L83 (`.get`): `int(data.get('timestamp', '0')),`
- L103 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/user')`
- L104 (`.get`): `self.api_key = config.get('api_key')`
- L105 (`.get`): `self.api_secret = config.get('api_secret')`
- L106 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L169 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L174 (`.get`): `event_type = data.get('event_type')`
- L224 (`ws\.recv`): `message = await self.ws.recv()`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/ws_user_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L32 (`.get`): `trade_id=data.get('id', ''),`
- L33 (`.get`): `taker_order_id=data.get('taker_order_id', ''),`
- L34 (`.get`): `asset_id=data.get('asset_id', ''),`
- L35 (`.get`): `market=data.get('market', ''),`
- L36 (`.get`): `side=data.get('side', ''),`
- L37 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L38 (`.get`): `size=Decimal(str(data.get('size', '0'))),`
- L39 (`.get`): `outcome=data.get('outcome', ''),`
- L40 (`.get`): `status=data.get('status', ''),`
- L42 (`.get`): `int(data.get('matchtime', '0')),`
- L45 (`.get`): `maker_orders=data.get('maker_orders', [])`
- L73 (`.get`): `order_id=data.get('id', ''),`
- L74 (`.get`): `asset_id=data.get('asset_id', ''),`
- L75 (`.get`): `market=data.get('market', ''),`
- L76 (`.get`): `side=data.get('side', ''),`
- L77 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L78 (`.get`): `original_size=Decimal(str(data.get('original_size', '0'))),`
- L79 (`.get`): `size_matched=Decimal(str(data.get('size_matched', '0'))),`
- L80 (`.get`): `outcome=data.get('outcome', ''),`
- L81 (`.get`): `event_type=data.get('type', ''),`
- L83 (`.get`): `int(data.get('timestamp', '0')),`
- L103 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/user')`
- L104 (`.get`): `self.api_key = config.get('api_key')`
- L105 (`.get`): `self.api_secret = config.get('api_secret')`
- L106 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L169 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L174 (`.get`): `event_type = data.get('event_type')`
- L224 (`ws\.recv`): `message = await self.ws.recv()`

## `tbot_core/api/ws_user_client.py` [PLATFORM]
**External imports:** websockets

**Transport calls in code:**
- L32 (`.get`): `trade_id=data.get('id', ''),`
- L33 (`.get`): `taker_order_id=data.get('taker_order_id', ''),`
- L34 (`.get`): `asset_id=data.get('asset_id', ''),`
- L35 (`.get`): `market=data.get('market', ''),`
- L36 (`.get`): `side=data.get('side', ''),`
- L37 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L38 (`.get`): `size=Decimal(str(data.get('size', '0'))),`
- L39 (`.get`): `outcome=data.get('outcome', ''),`
- L40 (`.get`): `status=data.get('status', ''),`
- L42 (`.get`): `int(data.get('matchtime', '0')),`
- L45 (`.get`): `maker_orders=data.get('maker_orders', [])`
- L73 (`.get`): `order_id=data.get('id', ''),`
- L74 (`.get`): `asset_id=data.get('asset_id', ''),`
- L75 (`.get`): `market=data.get('market', ''),`
- L76 (`.get`): `side=data.get('side', ''),`
- L77 (`.get`): `price=Decimal(str(data.get('price', '0'))),`
- L78 (`.get`): `original_size=Decimal(str(data.get('original_size', '0'))),`
- L79 (`.get`): `size_matched=Decimal(str(data.get('size_matched', '0'))),`
- L80 (`.get`): `outcome=data.get('outcome', ''),`
- L81 (`.get`): `event_type=data.get('type', ''),`
- L83 (`.get`): `int(data.get('timestamp', '0')),`
- L103 (`.get`): `self.ws_url = config.get('ws_url', 'wss://ws-subscriptions-clob.polymarket.com/ws/user')`
- L104 (`.get`): `self.api_key = config.get('api_key')`
- L105 (`.get`): `self.api_secret = config.get('api_secret')`
- L106 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L169 (`ws\.send`): `await self.ws.send(json.dumps(message))`
- L174 (`.get`): `event_type = data.get('event_type')`
- L224 (`ws\.recv`): `message = await self.ws.recv()`

## `main.py` [PLATFORM]
**External imports:** aiohttp, zmq

**Transport calls in code:**
- L18 (`zmq`): `import zmq`
- L53 (`.post`): `async with session.post(url, json={`
- L93 (`.get`): `client = PolymarketClient(config.get('polymarket', {}))`
- L97 (`.get`): `market_tag = config.get('market_tag', 'btc-15m')`
- L105 (`.get`): `market_slug = market.get('slug')`
- L114 (`.get`): `time_to_expiry = config.get('market_duration_sec', 900)`
- L179 (`.get`): `yaml_id = config.get('bot_id', 'btc_hybrid')`
- L212 (`.get`): `f"[TBOT] Config: bankroll=${config.get('bankroll_usd', 0):.0f} | "`
- L213 (`.get`): `f"strategy={config.get('strategy', 'legacy')}"`
- L217 (`.get`): `data_source = config.get('data_source', '')`
- L225 (`zmq`): `if data_source.startswith('zmq://'):`
- L312 (`.get`): `wallet = config.get('funder_address') or '0xA1dC7f65e6adC537604B99607cA356A23b35bB61'`
- L313 (`.get`): `bankroll = float(config.get('bankroll_usd', 0))`
- L321 (`.get`): `f"wallet={str(config.get('funder_address', 'UNKNOWN'))[:10]}... | "`
- L334 (`zmq`): `ctx = zmq.Context()`
- L335 (`zmq`): `sock = ctx.socket(zmq.SUB)`
- L335 (`SUB`): `sock = ctx.socket(zmq.SUB)`
- L337 (`zmq`): `sock.setsockopt_string(zmq.SUBSCRIBE, "")`
- L342 (`.get`): `if msg.get("type") == "btc_update":`
- L343 (`.get`): `data = msg.get("data", {})`
- L344 (`.get`): `p_val.value = data.get("btc_price", 0.0)`
- L345 (`.get`): `ts_val.value = data.get("btc_ts", 0.0)`
- L346 (`.get`): `vr_val.value = data.get("vol_ratio", 1.0)`
- L347 (`.get`): `bd_val.value = data.get("btc_delta", 0.0)`
- L370 (`.get`): `logger.info(f"⚡ [CORE] Deploying strategy: {config.get('strategy').upper()} in LIVE mode")`
- L447 (`.get`): `msg = context.get("exception", context["message"])`
- L448 (`.get`): `logging.getLogger('main').critical(f"‼️ [CORE FATAL] AsyncIO Unhandled Exception: {msg}", exc_info=context.get('exceptio`

## `unified_analysis.py` [TRANSPORT]
**Transport calls in code:**
- L308 (`.get`): `vals = [counts_by_bot[b].get(tag, 0) for b in BOTS]`
- L325 (`.get`): `vals = [healer_by_bot[b].get(reason, 0) for b in BOTS]`
- L332 (`.get`): `vals = [cancel_by_bot[b].get(reason, 0) for b in BOTS]`
- L385 (`.get`): `epochs = all_epochs_by_bot.get(bot_id, [])`
- L410 (`.get`): `epochs = all_epochs_by_bot.get(bot_id, [])`
- L446 (`.get`): `all_toxic = toxic_by_bot.get('bot-control', [])`
- L521 (`.get`): `fills_ctrl = fills_by_bot.get('bot-control', [])`
- L588 (`.get`): `fills = fills_by_bot.get(bot_id, [])`
- L595 (`.get`): `epochs = all_epochs_by_bot.get(bot_id, [])`
- L604 (`.get`): `lambda b: str(len(fills_by_bot.get(b, [])))),`
- L606 (`.get`): `lambda b: str(sum(1 for f in fills_by_bot.get(b,[]) if f['intent']=='NORMAL'))),`
- L608 (`.get`): `lambda b: str(sum(1 for f in fills_by_bot.get(b,[]) if f['intent']=='HUNTER'))),`
- L610 (`.get`): `lambda b: str(sum(1 for f in fills_by_bot.get(b,[]) if f['intent']=='HEALER_AVG'))),`
- L613 (`.get`): `lambda b: f"{sum(f['edge'] for f in fills_by_bot.get(b,[]) if f['intent']=='NORMAL')/max(1,sum(1 for f in fills_by_bot.g`
- L615 (`.get`): `lambda b: f"{sum(f['edge'] for f in fills_by_bot.get(b,[]) if f['intent']=='HUNTER')/max(1,sum(1 for f in fills_by_bot.g`
- L618 (`.get`): `lambda b: str(len(all_epochs_by_bot.get(b, [])))),`
- L623 (`.get`): `sum(1 for e in all_epochs_by_bot.get(b,[]) if e['realized_ps']>1.00),`
- L624 (`.get`): `len(all_epochs_by_bot.get(b,[]))`
- L627 (`.get`): `lambda b: f"{sum(e['duration_sec'] for e in all_epochs_by_bot.get(b,[]))/max(1,len(all_epochs_by_bot.get(b,[]))):.0f}"),`
- L630 (`.get`): `lambda b: str(len([r for r in toxic_by_bot.get(b,[]) if r['tag']=='TOXIC_ORIGIN']))),`
- L632 (`.get`): `lambda b: str(len([r for r in toxic_by_bot.get(b,[]) if r['tag']=='TOXIC_HEAL']))),`
- L635 (`.get`): `lambda b: str(counts_by_bot[b].get('GRID_MGR_KILL', 0))),`
- L637 (`.get`): `lambda b: str(counts_by_bot[b].get('PROJ_CUT', 0))),`
- L639 (`.get`): `lambda b: str(counts_by_bot[b].get('PINGPONG_GUARD', 0))),`
- L641 (`.get`): `lambda b: str(counts_by_bot[b].get('HEALER_FAIL', 0))),`
- L643 (`.get`): `lambda b: str(healer_by_bot[b].get('CAUSE_B_HUNTER_ZONE', 0))),`
- L645 (`.get`): `lambda b: str(healer_by_bot[b].get('PRICE_NOT_CHEAP_ENOUGH', 0))),`

## `backtester/optimizer/optuna_optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L130 (`.get`): `cfg.deposit = params.get('deposit', deposit)`
- L147 (`.get`): `if spec.get('ordinal', True) and spec['type'] in ('int', 'float'):`
- L163 (`.get`): `if spec.get('optimize', True):`
- L224 (`.get`): `if spec.get('ordinal', True) and spec['type'] in ('int', 'float'):`
- L407 (`.get`): `imbalances = [r.metrics.get('imbalance_pct', 0) for r in results]`
- L408 (`.get`): `pair_sums = [r.metrics.get('pair_sum', 1.0) for r in results`
- L409 (`.get`): `if r.metrics.get('pair_sum', 0) > 0]`
- L410 (`.get`): `cap_utils = [r.metrics.get('capital_utilization', 0) for r in results]`
- L651 (`.get`): `f"median_pnl=${bt.user_attrs.get('median_pnl', 0):.4f}, "`
- L652 (`.get`): `f"WR={bt.user_attrs.get('win_rate', 0):.1f}%")`
- L763 (`.get`): `val = best_params_from_multistart.get(p)`
- L766 (`.get`): `val = DEFAULTS.get(p)`
- L805 (`.get`): `f"median_pnl=${bt.user_attrs.get('median_pnl', 0):.4f}")`
- L854 (`.get`): `best_val = DEFAULTS.get(p)`
- L908 (`.get`): `f"median_pnl=${bt.user_attrs.get('median_pnl', 0):.4f}, "`
- L909 (`.get`): `f"WR={bt.user_attrs.get('win_rate', 0):.1f}%")`
- L947 (`.get`): `all_trials.sort(key=lambda x: (x.get('score') or x['metrics'].get('median_pnl', -999)),`
- L1026 (`.get`): `spec = PARAM_SPACE.get(k)`
- L1034 (`.get`): `lhs_results = screening.get('results', [])`
- L1164 (`.get`): `f"median_pnl=${m.get('median_pnl', 0):.4f} | "`
- L1165 (`.get`): `f"WR={m.get('win_rate', 0):.1f}% | "`
- L1166 (`.get`): `f"sharpe={m.get('sharpe', 0):.3f} | "`
- L1167 (`.get`): `f"worst=${m.get('worst_dd', 0):.2f}")`
- L1281 (`.get`): `if spec.get('optimize', True) and len(spec['values']) > 1:`
- L1287 (`.get`): `n_opt = sum(1 for s in modified_space.values() if len(s.get('values', [])) > 1)`
- L1307 (`.get`): `n_opt = sum(1 for s in modified_space.values() if len(s.get('values', [])) > 1)`

## `archive/dead_2026-03-04/polymarket/client.py` [PLATFORM]
**Transport calls in code:**
- L317 (`.get`): `order_id = response.get('orderID') or response.get('id')`
- L359 (`.get`): `status=response.get('status', 'UNKNOWN'),`
- L360 (`.get`): `filled_size=float(response.get('size_matched', 0)),`
- L361 (`.get`): `remaining_size=float(response.get('original_size', 0)) - float(response.get('size_matched', 0)),`
- L362 (`.get`): `avg_price=float(response.get('price', 0)) if response.get('price') else None,`
- L363 (`.get`): `created_at=response.get('created_at')`
- L389 (`.get`): `success = response.get('canceled') or response.get('success', False)`
- L417 (`.get`): `cancelled = len(response.get('canceled', []))`
- L444 (`.get`): `asset_id=pos.get('asset'),`
- L445 (`.get`): `condition_id=pos.get('condition_id', ''),`
- L446 (`.get`): `size=float(pos.get('size', 0)),`
- L447 (`.get`): `avg_price=float(pos.get('avg_price', 0)),`
- L448 (`.get`): `side=pos.get('outcome', 'UNKNOWN')  # YES or NO`
- L473 (`.get`): `balance = float(response.get('balance', 0))`
- L504 (`.get`): `tokens = response.get('tokens', [])`
- L505 (`.get`): `yes_token = next((t for t in tokens if t.get('outcome') == 'Yes'), {})`
- L506 (`.get`): `no_token = next((t for t in tokens if t.get('outcome') == 'No'), {})`
- L510 (`.get`): `question=response.get('question', ''),`
- L511 (`.get`): `yes_token_id=yes_token.get('token_id', ''),`
- L512 (`.get`): `no_token_id=no_token.get('token_id', ''),`
- L513 (`.get`): `active=response.get('active', False),`
- L514 (`.get`): `closed=response.get('closed', False),`
- L515 (`.get`): `resolved=response.get('resolved', False),`
- L516 (`.get`): `outcome=response.get('outcome')`
- L539 (`.get`): `open_orders = [o for o in response if o.get('status') == 'LIVE']`

## `archive/hesoyam_with_fill_rate_limits/polymarket/client.py` [PLATFORM]
**Transport calls in code:**
- L317 (`.get`): `order_id = response.get('orderID') or response.get('id')`
- L359 (`.get`): `status=response.get('status', 'UNKNOWN'),`
- L360 (`.get`): `filled_size=float(response.get('size_matched', 0)),`
- L361 (`.get`): `remaining_size=float(response.get('original_size', 0)) - float(response.get('size_matched', 0)),`
- L362 (`.get`): `avg_price=float(response.get('price', 0)) if response.get('price') else None,`
- L363 (`.get`): `created_at=response.get('created_at')`
- L389 (`.get`): `success = response.get('canceled') or response.get('success', False)`
- L417 (`.get`): `cancelled = len(response.get('canceled', []))`
- L444 (`.get`): `asset_id=pos.get('asset'),`
- L445 (`.get`): `condition_id=pos.get('condition_id', ''),`
- L446 (`.get`): `size=float(pos.get('size', 0)),`
- L447 (`.get`): `avg_price=float(pos.get('avg_price', 0)),`
- L448 (`.get`): `side=pos.get('outcome', 'UNKNOWN')  # YES or NO`
- L473 (`.get`): `balance = float(response.get('balance', 0))`
- L504 (`.get`): `tokens = response.get('tokens', [])`
- L505 (`.get`): `yes_token = next((t for t in tokens if t.get('outcome') == 'Yes'), {})`
- L506 (`.get`): `no_token = next((t for t in tokens if t.get('outcome') == 'No'), {})`
- L510 (`.get`): `question=response.get('question', ''),`
- L511 (`.get`): `yes_token_id=yes_token.get('token_id', ''),`
- L512 (`.get`): `no_token_id=no_token.get('token_id', ''),`
- L513 (`.get`): `active=response.get('active', False),`
- L514 (`.get`): `closed=response.get('closed', False),`
- L515 (`.get`): `resolved=response.get('resolved', False),`
- L516 (`.get`): `outcome=response.get('outcome')`
- L539 (`.get`): `open_orders = [o for o in response if o.get('status') == 'LIVE']`

## `backtester/results_db.py` [PLATFORM]
**Transport calls in code:**
- L113 (`.get`): `fill_rate = m.get('fill_rate', 0)`
- L114 (`.get`): `pairs = m.get('pairs_completed', 0)`
- L115 (`.get`): `pair_sum = m.get('avg_pair_sum', 0)`
- L116 (`.get`): `imb = m.get('imbalance_pct', 0)`
- L117 (`.get`): `toxic = m.get('toxic_fill_pct', 0)`
- L118 (`.get`): `worst = m.get('worst_case_pnl', 0)`
- L119 (`.get`): `recovery = m.get('recovery_triggers', 0)`
- L120 (`.get`): `drawdown = m.get('drawdown_triggers', 0)`
- L121 (`.get`): `imb_stops = m.get('imbalance_stops', 0)`
- L122 (`.get`): `momentum = m.get('momentum_skips', 0)`
- L123 (`.get`): `spread = m.get('spread_skips', 0)`
- L124 (`.get`): `mkt_pnl = m.get('market_pnl_stops', 0)`
- L125 (`.get`): `edge_rec = m.get('edge_recovery_triggers', 0)`
- L126 (`.get`): `bid_sum = m.get('bid_sum_skips', 0)`
- L127 (`.get`): `taker = m.get('taker_fees', 0)`
- L128 (`.get`): `cap_util = m.get('capital_utilization', 0)`
- L339 (`.get`): `winner=r.get('winner', ''),`
- L341 (`.get`): `fills=r.get('fills', 0),`
- L342 (`.get`): `orders=r.get('orders', 0),`
- L343 (`.get`): `yes_shares=r.get('yes', 0),`
- L344 (`.get`): `no_shares=r.get('no', 0),`
- L345 (`.get`): `cost=r.get('cost', 0),`
- L346 (`.get`): `metrics=r.get('metrics', {}),`
- L347 (`.get`): `processed_at=r.get('processed_at', ''),`
- L392 (`.get`): `print(f"   Capital Util: {s.get('avg_capital_util', 0):.1f}%")`

## `archive/hesoyam_with_fill_rate_limits/backtester/results_db.py` [PLATFORM]
**Transport calls in code:**
- L111 (`.get`): `fill_rate = m.get('fill_rate', 0)`
- L112 (`.get`): `pairs = m.get('pairs_completed', 0)`
- L113 (`.get`): `pair_sum = m.get('avg_pair_sum', 0)`
- L114 (`.get`): `imb = m.get('imbalance_pct', 0)`
- L115 (`.get`): `toxic = m.get('toxic_fill_pct', 0)`
- L116 (`.get`): `worst = m.get('worst_case_pnl', 0)`
- L117 (`.get`): `recovery = m.get('recovery_triggers', 0)`
- L118 (`.get`): `drawdown = m.get('drawdown_triggers', 0)`
- L119 (`.get`): `imb_stops = m.get('imbalance_stops', 0)`
- L120 (`.get`): `momentum = m.get('momentum_skips', 0)`
- L121 (`.get`): `spread = m.get('spread_skips', 0)`
- L122 (`.get`): `mkt_pnl = m.get('market_pnl_stops', 0)`
- L123 (`.get`): `edge_rec = m.get('edge_recovery_triggers', 0)`
- L124 (`.get`): `bid_sum = m.get('bid_sum_skips', 0)`
- L125 (`.get`): `taker = m.get('taker_fees', 0)`
- L333 (`.get`): `winner=r.get('winner', ''),`
- L335 (`.get`): `fills=r.get('fills', 0),`
- L336 (`.get`): `orders=r.get('orders', 0),`
- L337 (`.get`): `yes_shares=r.get('yes', 0),`
- L338 (`.get`): `no_shares=r.get('no', 0),`
- L339 (`.get`): `cost=r.get('cost', 0),`
- L340 (`.get`): `metrics=r.get('metrics', {}),`
- L341 (`.get`): `processed_at=r.get('processed_at', ''),`

## `archive/optimizer/angel_optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L291 (`.get`): `scaling = DEPOSIT_SCALING.get(bankroll, DEPOSIT_SCALING[200])`
- L330 (`.get`): `if params.get('imbalance_stop_pct', 25) <= params.get('imbalance_rebalance_pct', 15):`
- L351 (`.get`): `if params.get('imbalance_stop_pct', 25) <= params.get('imbalance_rebalance_pct', 15):`
- L366 (`.get`): `grace = params.get('imbalance_min_shares', 18)`
- L371 (`.get`): `lot = params.get('lot_size', 12)`
- L372 (`.get`): `interval = params.get('buy_interval', 2)`
- L373 (`.get`): `pricing = params.get('pricing_mode', 'at-bid')`
- L374 (`.get`): `bid_sum = params.get('bid_sum_threshold', 0.985)`
- L375 (`.get`): `rebal = params.get('imbalance_rebalance_pct', 15)`
- L376 (`.get`): `stop = params.get('imbalance_stop_pct', 25)`
- L383 (`.get`): `buy_interval=params.get('buy_interval', 2),`
- L389 (`.get`): `critical_cooldown_sec=params.get('critical_cooldown_sec', 2),`
- L390 (`.get`): `momentum_threshold=params.get('momentum_threshold', 3.0),`
- L391 (`.get`): `momentum_window_sec=params.get('momentum_window_sec', 10.0),`
- L392 (`.get`): `market_pnl_stop_roi=params.get('market_pnl_stop_roi', -8.0),`
- L393 (`.get`): `market_pnl_grace_sec=params.get('market_pnl_grace_sec', 60.0),`
- L395 (`.get`): `drawdown_pct=params.get('drawdown_pct', 10.0),`
- L397 (`.get`): `recovery_max_loss_pct=params.get('recovery_max_loss_pct', 2.0),`
- L398 (`.get`): `recovery_max_budget_pct=params.get('recovery_max_budget_pct', 30.0),`
- L399 (`.get`): `recovery_min_time_left=params.get('recovery_min_time_left', 60.0),`
- L400 (`.get`): `recovery_min_imbalance_pct=params.get('recovery_min_imbalance_pct', 25.0),`
- L402 (`.get`): `start_delay_sec=params.get('start_delay_sec', 10.0) if duration == 900 else 3.0,`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/orderbook_logger.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L111 (`.get`): `asset_id = message.get('asset_id')`
- L112 (`.get`): `is_yes = message.get('is_yes')`
- L113 (`.get`): `bids = message.get('bids', [])`
- L114 (`.get`): `asks = message.get('asks', [])`
- L115 (`.get`): `timestamp = message.get('timestamp', str(int(time.time() * 1000)))`
- L125 (`.get`): `best_bid = max([float(b.get('price', 0)) for b in bids]) if bids else 0`
- L126 (`.get`): `best_ask = min([float(a.get('price', 1)) for a in asks]) if asks else 1`
- L384 (`.get`): `async with session.get(url, params=params) as response:`
- L400 (`.get`): `event_slug = event.get('slug', '')`
- L405 (`.get`): `markets = event.get('markets', [])`
- L407 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L408 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L426 (`.get`): `'condition_id': market.get('conditionId'),`
- L429 (`.get`): `'slug': market.get('slug'),`
- L460 (`.get`): `async with session.get(url, params=params) as response:`
- L472 (`.get`): `event_slug = event.get('slug', '')`
- L477 (`.get`): `markets = event.get('markets', [])`
- L479 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L480 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L496 (`.get`): `'condition_id': market.get('conditionId'),`
- L499 (`.get`): `'slug': market.get('slug'),`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/orderbook_logger.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L111 (`.get`): `asset_id = message.get('asset_id')`
- L112 (`.get`): `is_yes = message.get('is_yes')`
- L113 (`.get`): `bids = message.get('bids', [])`
- L114 (`.get`): `asks = message.get('asks', [])`
- L115 (`.get`): `timestamp = message.get('timestamp', str(int(time.time() * 1000)))`
- L125 (`.get`): `best_bid = max([float(b.get('price', 0)) for b in bids]) if bids else 0`
- L126 (`.get`): `best_ask = min([float(a.get('price', 1)) for a in asks]) if asks else 1`
- L384 (`.get`): `async with session.get(url, params=params) as response:`
- L400 (`.get`): `event_slug = event.get('slug', '')`
- L405 (`.get`): `markets = event.get('markets', [])`
- L407 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L408 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L426 (`.get`): `'condition_id': market.get('conditionId'),`
- L429 (`.get`): `'slug': market.get('slug'),`
- L460 (`.get`): `async with session.get(url, params=params) as response:`
- L472 (`.get`): `event_slug = event.get('slug', '')`
- L477 (`.get`): `markets = event.get('markets', [])`
- L479 (`.get`): `if market.get('acceptingOrders') and not market.get('closed'):`
- L480 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L496 (`.get`): `'condition_id': market.get('conditionId'),`
- L499 (`.get`): `'slug': market.get('slug'),`

## `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/rfq/rfq_client.py` [PLATFORM]
**Transport calls in code:**
- L490 (`.get`): `if not resp.get("data") or len(resp["data"]) == 0:`
- L495 (`.get`): `price = order_creation_payload.get("price")`
- L537 (`.get`): `accept_payload.get("requestId"),`
- L538 (`.get`): `accept_payload.get("quoteId"),`
- L539 (`.get`): `accept_payload.get("tokenId"),`
- L540 (`.get`): `accept_payload.get("side"),`
- L572 (`.get`): `if not rfq_quotes.get("data") or len(rfq_quotes["data"]) == 0:`
- L579 (`.get`): `side = rfq_quote.get("side", BUY)`
- L583 (`.get`): `size = rfq_quote.get("sizeIn")`
- L585 (`.get`): `size = rfq_quote.get("sizeOut")`
- L587 (`.get`): `token_id = rfq_quote.get("token")`
- L588 (`.get`): `price = rfq_quote.get("price")`
- L653 (`.get`): `raw_match_type = quote.get("matchType", MatchType.COMPLEMENTARY)`
- L660 (`.get`): `side = quote.get("side", BUY)`
- L665 (`.get`): `token = quote.get("token")`
- L669 (`.get`): `size = quote.get("sizeOut") if side == BUY else quote.get("sizeIn")`
- L672 (`.get`): `price = quote.get("price")`
- L685 (`.get`): `token = quote.get("complement")`
- L688 (`.get`): `size = quote.get("sizeIn") if side == BUY else quote.get("sizeOut")`
- L691 (`.get`): `price = quote.get("price")`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_risk/guards.py` [PLATFORM]
**Transport calls in code:**
- L41 (`.get`): `self.entry_min_time_to_close = int(config.get('entry_min_time_to_close_sec', 300))`
- L42 (`.get`): `self.stop_before_close = int(config.get('stop_before_close_sec', 60))`
- L45 (`.get`): `self.max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss_usd', 15)))`
- L46 (`.get`): `self.panic_exit_loss = Decimal(str(config.get('panic_exit_loss_usd', 50)))`
- L49 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L50 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L51 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', '0.5')))`
- L54 (`.get`): `self.max_imbalance = Decimal(str(config.get('max_imbalance_usd', 50)))`
- L55 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.5')))`
- L56 (`.get`): `self.max_unpaired_time = int(config.get('unpaired_timeout_sec', 120))`
- L123 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L124 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L125 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L165 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L169 (`.get`): `order_cost = Decimal(str(pending_order.get('size', 0))) * Decimal(str(pending_order.get('price', 0)))`
- L211 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L212 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L240 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L241 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_risk/guards.py` [PLATFORM]
**Transport calls in code:**
- L41 (`.get`): `self.entry_min_time_to_close = int(config.get('entry_min_time_to_close_sec', 300))`
- L42 (`.get`): `self.stop_before_close = int(config.get('stop_before_close_sec', 60))`
- L45 (`.get`): `self.max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss_usd', 15)))`
- L46 (`.get`): `self.panic_exit_loss = Decimal(str(config.get('panic_exit_loss_usd', 50)))`
- L49 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L50 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L51 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', '0.5')))`
- L54 (`.get`): `self.max_imbalance = Decimal(str(config.get('max_imbalance_usd', 50)))`
- L55 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.5')))`
- L56 (`.get`): `self.max_unpaired_time = int(config.get('unpaired_timeout_sec', 120))`
- L123 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L124 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L125 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L165 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L169 (`.get`): `order_cost = Decimal(str(pending_order.get('size', 0))) * Decimal(str(pending_order.get('price', 0)))`
- L211 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L212 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L240 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L241 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_risk/guards.py` [PLATFORM]
**Transport calls in code:**
- L41 (`.get`): `self.entry_min_time_to_close = int(config.get('entry_min_time_to_close_sec', 300))`
- L42 (`.get`): `self.stop_before_close = int(config.get('stop_before_close_sec', 60))`
- L45 (`.get`): `self.max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss_usd', 15)))`
- L46 (`.get`): `self.panic_exit_loss = Decimal(str(config.get('panic_exit_loss_usd', 50)))`
- L49 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L50 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L51 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', '0.5')))`
- L54 (`.get`): `self.max_imbalance = Decimal(str(config.get('max_imbalance_usd', 50)))`
- L55 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.5')))`
- L56 (`.get`): `self.max_unpaired_time = int(config.get('unpaired_timeout_sec', 120))`
- L123 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L124 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L125 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L165 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L169 (`.get`): `order_cost = Decimal(str(pending_order.get('size', 0))) * Decimal(str(pending_order.get('price', 0)))`
- L211 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L212 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L240 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L241 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`

## `tbot_risk/guards.py` [PLATFORM]
**Transport calls in code:**
- L41 (`.get`): `self.entry_min_time_to_close = int(config.get('entry_min_time_to_close_sec', 300))`
- L42 (`.get`): `self.stop_before_close = int(config.get('stop_before_close_sec', 60))`
- L45 (`.get`): `self.max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss_usd', 15)))`
- L46 (`.get`): `self.panic_exit_loss = Decimal(str(config.get('panic_exit_loss_usd', 50)))`
- L49 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L50 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L51 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', '0.5')))`
- L54 (`.get`): `self.max_imbalance = Decimal(str(config.get('max_imbalance_usd', 50)))`
- L55 (`.get`): `self.min_pair_ratio = Decimal(str(config.get('min_pair_ratio', '0.5')))`
- L56 (`.get`): `self.max_unpaired_time = int(config.get('unpaired_timeout_sec', 120))`
- L123 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L124 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L125 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L165 (`.get`): `total_cost = Decimal(str(position.get('total_cost', 0)))`
- L169 (`.get`): `order_cost = Decimal(str(pending_order.get('size', 0))) * Decimal(str(pending_order.get('price', 0)))`
- L211 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L212 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`
- L240 (`.get`): `yes_shares = Decimal(str(position.get('yes_shares', 0)))`
- L241 (`.get`): `no_shares = Decimal(str(position.get('no_shares', 0)))`

## `archive/hesoyam_with_fill_rate_limits/scripts/safety_watchdog.py` [PLATFORM]
**Transport calls in code:**
- L47 (`.get`): `if p.get('name') == PM2_PROCESS:`
- L49 (`.get`): `'status': p.get('pm2_env', {}).get('status', '?'),`
- L50 (`.get`): `'restarts': p.get('pm2_env', {}).get('restart_time', 0),`
- L51 (`.get`): `'pid': p.get('pid', 0),`
- L52 (`.get`): `'uptime': p.get('pm2_env', {}).get('pm_uptime', 0),`
- L99 (`.get`): `state_age = time.time() - state.get('timestamp', 0)`
- L104 (`.get`): `wallet = state.get('wallet_balance', 999)`
- L109 (`.get`): `pos = state.get('position', {})`
- L110 (`.get`): `yes = pos.get('yes_shares', 0)`
- L111 (`.get`): `no = pos.get('no_shares', 0)`
- L113 (`.get`): `cost = pos.get('total_cost', 0)`
- L124 (`.get`): `risk = state.get('risk', {})`
- L125 (`.get`): `pnl = risk.get('realized_pnl', 0)`
- L150 (`.get`): `pos = state.get('position', {}) if state else {}`
- L151 (`.get`): `wallet = state.get('wallet_balance', '?') if state else '?'`
- L152 (`.get`): `slug = state.get('market_slug', '—') if state else '—'`
- L153 (`.get`): `time_left = state.get('time_left_sec', 0) if state else 0`
- L157 (`.get`): `status += f'YES={pos.get("yes_shares",0)} NO={pos.get("no_shares",0)} ${pos.get("total_cost",0):.2f} | '`

## `monitor.py` [TRANSPORT]
**External imports:** zmq

**Transport calls in code:**
- L1 (`zmq`): `import zmq`
- L48 (`.get`): `tag = data.get('recovery_tag', 'NORMAL')`
- L49 (`.get`): `intent = data.get('intent', 'IDLE')`
- L50 (`.get`): `t_rem = data.get('t_rem', 0)`
- L57 (`.get`): `f"[{header_color}]ID: {data.get('bot_id', '???')} | INTENT: {intent} | STATUS: {tag} | T-REM: {t_rem}s[/]",`
- L68 (`.get`): `q = data.get('q', 0)`
- L69 (`.get`): `hc = data.get('hc_limit', 35)`
- L73 (`.get`): `stress = data.get('stress', 0.0)`
- L77 (`.get`): `cvd = data.get('cvd', 0.0)`
- L81 (`.get`): `stuck = data.get('stuck_sec', 0)`
- L85 (`.get`): `pnl = data.get('pnl', 0.0)`
- L86 (`.get`): `oxy = data.get('oxy', 0)`
- L89 (`.get`): `footer_text = f"[{pnl_color}]PnL: {pnl:+.2f}$[/] | [cyan]Margin Oxygen: {oxy}%[/] | [white]BTC: ${data.get('btc', 0):,.0`
- L95 (`zmq`): `context = zmq.Context()`
- L96 (`zmq`): `socket = context.socket(zmq.SUB)`
- L96 (`SUB`): `socket = context.socket(zmq.SUB)`
- L97 (`socket\.connect`): `socket.connect("tcp://127.0.0.1:28888")`
- L98 (`zmq`): `socket.setsockopt_string(zmq.SUBSCRIBE, "")`

## `scripts/safety_watchdog.py` [PLATFORM]
**Transport calls in code:**
- L47 (`.get`): `if p.get('name') == PM2_PROCESS:`
- L49 (`.get`): `'status': p.get('pm2_env', {}).get('status', '?'),`
- L50 (`.get`): `'restarts': p.get('pm2_env', {}).get('restart_time', 0),`
- L51 (`.get`): `'pid': p.get('pid', 0),`
- L52 (`.get`): `'uptime': p.get('pm2_env', {}).get('pm_uptime', 0),`
- L99 (`.get`): `state_age = time.time() - state.get('timestamp', 0)`
- L104 (`.get`): `wallet = state.get('wallet_balance', 999)`
- L109 (`.get`): `pos = state.get('position', {})`
- L110 (`.get`): `yes = pos.get('yes_shares', 0)`
- L111 (`.get`): `no = pos.get('no_shares', 0)`
- L113 (`.get`): `cost = pos.get('total_cost', 0)`
- L124 (`.get`): `risk = state.get('risk', {})`
- L125 (`.get`): `pnl = risk.get('realized_pnl', 0)`
- L150 (`.get`): `pos = state.get('position', {}) if state else {}`
- L151 (`.get`): `wallet = state.get('wallet_balance', '?') if state else '?'`
- L152 (`.get`): `slug = state.get('market_slug', '—') if state else '—'`
- L153 (`.get`): `time_left = state.get('time_left_sec', 0) if state else 0`
- L157 (`.get`): `status += f'YES={pos.get("yes_shares",0)} NO={pos.get("no_shares",0)} ${pos.get("total_cost",0):.2f} | '`

## `analysis/views/leaderboard.py` [TRANSPORT]
**Transport calls in code:**
- L38 (`.get`): `a_markets = max(1, anchor_data.counts.get('FINAL MARKET REPORT', 0))`
- L39 (`.get`): `v_markets = max(1, variant_data.counts.get('FINAL MARKET REPORT', 0))`
- L40 (`.get`): `a_healer = anchor_data.counts.get('FILL_CTX', 0)  # placeholder, см. note ниже`
- L41 (`.get`): `v_healer = variant_data.counts.get('FILL_CTX', 0)`
- L79 (`.get`): `anchor_id = HYPOTHESIS_ANCHORS.get(hyp_name)`
- L80 (`.get`): `anchor_data = bots_data.get(anchor_id)`
- L81 (`.get`): `anchor_summary = epochs_summary.get(anchor_id) if anchor_id else None`
- L88 (`.get`): `anchor_data = bots_data.get(a_bot)`
- L89 (`.get`): `anchor_summary = epochs_summary.get(a_bot)`
- L101 (`.get`): `markets = max(1, anchor_data.counts.get('FINAL MARKET REPORT', 0))`
- L104 (`.get`): `proj = anchor_data.counts.get('PROJ_CUT', 0)`
- L105 (`.get`): `fc = max(1, anchor_data.counts.get('FILL_CTX', 0))`
- L113 (`.get`): `data = bots_data.get(bot_id)`
- L114 (`.get`): `summary = epochs_summary.get(bot_id)`
- L124 (`.get`): `markets = max(1, data.counts.get('FINAL MARKET REPORT', 0))`
- L127 (`.get`): `proj = data.counts.get('PROJ_CUT', 0)`
- L128 (`.get`): `fc = max(1, data.counts.get('FILL_CTX', 0))`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/engine.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- L62 (`.get`): `self.ws_client = PolymarketWSClient(self.config.get('polymarket', {}))`
- L63 (`.get`): `self.user_ws_client = UserChannelClient(self.config.get('polymarket', {}))`
- L64 (`.get`): `self.market_analyzer = MarketAnalyzer(self.config.get('strategy', {}))`
- L65 (`.get`): `self.strategy = StrategyCore(self.config.get('strategy', {}))`
- L66 (`.get`): `self.order_manager = OrderManager(self.config.get('polymarket', {}))`
- L68 (`.get`): `self.fills_handler = FillsHandler(self.config.get('simulation', {}))`
- L69 (`.get`): `self.risk_guards = RiskGuards(self.config.get('risk', {}))`
- L70 (`.get`): `self.risk_limits = RiskLimits(self.config.get('capital', {}))`
- L71 (`.get`): `self.claim_manager = ClaimManager(self.config.get('blockchain', {}))`
- L74 (`.get`): `self.claim_check_interval = self.config.get('operations', {}).get('claim_check_interval_sec', 300)`
- L92 (`.get`): `log_config = self.config.get('logging', {})`
- L93 (`.get`): `level = getattr(logging, log_config.get('level', 'INFO'))`
- L101 (`.get`): `if log_config.get('file', True):`
- L102 (`.get`): `log_dir = Path(log_config.get('log_dir', 'tbot_logs'))`
- L383 (`.get`): `wallet_address = self.config.get('blockchain', {}).get('wallet_address')`
- L397 (`.get`): `f"Winner: {claim['position'].get('winning_outcome', 'unknown')}"`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/engine.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- L62 (`.get`): `self.ws_client = PolymarketWSClient(self.config.get('polymarket', {}))`
- L63 (`.get`): `self.user_ws_client = UserChannelClient(self.config.get('polymarket', {}))`
- L64 (`.get`): `self.market_analyzer = MarketAnalyzer(self.config.get('strategy', {}))`
- L65 (`.get`): `self.strategy = StrategyCore(self.config.get('strategy', {}))`
- L66 (`.get`): `self.order_manager = OrderManager(self.config.get('polymarket', {}))`
- L68 (`.get`): `self.fills_handler = FillsHandler(self.config.get('simulation', {}))`
- L69 (`.get`): `self.risk_guards = RiskGuards(self.config.get('risk', {}))`
- L70 (`.get`): `self.risk_limits = RiskLimits(self.config.get('capital', {}))`
- L71 (`.get`): `self.claim_manager = ClaimManager(self.config.get('blockchain', {}))`
- L74 (`.get`): `self.claim_check_interval = self.config.get('operations', {}).get('claim_check_interval_sec', 300)`
- L92 (`.get`): `log_config = self.config.get('logging', {})`
- L93 (`.get`): `level = getattr(logging, log_config.get('level', 'INFO'))`
- L101 (`.get`): `if log_config.get('file', True):`
- L102 (`.get`): `log_dir = Path(log_config.get('log_dir', 'tbot_logs'))`
- L383 (`.get`): `wallet_address = self.config.get('blockchain', {}).get('wallet_address')`
- L397 (`.get`): `f"Winner: {claim['position'].get('winning_outcome', 'unknown')}"`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/engine.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- L62 (`.get`): `self.ws_client = PolymarketWSClient(self.config.get('polymarket', {}))`
- L63 (`.get`): `self.user_ws_client = UserChannelClient(self.config.get('polymarket', {}))`
- L64 (`.get`): `self.market_analyzer = MarketAnalyzer(self.config.get('strategy', {}))`
- L65 (`.get`): `self.strategy = StrategyCore(self.config.get('strategy', {}))`
- L66 (`.get`): `self.order_manager = OrderManager(self.config.get('polymarket', {}))`
- L68 (`.get`): `self.fills_handler = FillsHandler(self.config.get('simulation', {}))`
- L69 (`.get`): `self.risk_guards = RiskGuards(self.config.get('risk', {}))`
- L70 (`.get`): `self.risk_limits = RiskLimits(self.config.get('capital', {}))`
- L71 (`.get`): `self.claim_manager = ClaimManager(self.config.get('blockchain', {}))`
- L74 (`.get`): `self.claim_check_interval = self.config.get('operations', {}).get('claim_check_interval_sec', 300)`
- L92 (`.get`): `log_config = self.config.get('logging', {})`
- L93 (`.get`): `level = getattr(logging, log_config.get('level', 'INFO'))`
- L101 (`.get`): `if log_config.get('file', True):`
- L102 (`.get`): `log_dir = Path(log_config.get('log_dir', 'tbot_logs'))`
- L383 (`.get`): `wallet_address = self.config.get('blockchain', {}).get('wallet_address')`
- L397 (`.get`): `f"Winner: {claim['position'].get('winning_outcome', 'unknown')}"`

## `tbot_core/engine.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- L62 (`.get`): `self.ws_client = PolymarketWSClient(self.config.get('polymarket', {}))`
- L63 (`.get`): `self.user_ws_client = UserChannelClient(self.config.get('polymarket', {}))`
- L64 (`.get`): `self.market_analyzer = MarketAnalyzer(self.config.get('strategy', {}))`
- L65 (`.get`): `self.strategy = StrategyCore(self.config.get('strategy', {}))`
- L66 (`.get`): `self.order_manager = OrderManager(self.config.get('polymarket', {}))`
- L68 (`.get`): `self.fills_handler = FillsHandler(self.config.get('simulation', {}))`
- L69 (`.get`): `self.risk_guards = RiskGuards(self.config.get('risk', {}))`
- L70 (`.get`): `self.risk_limits = RiskLimits(self.config.get('capital', {}))`
- L71 (`.get`): `self.claim_manager = ClaimManager(self.config.get('blockchain', {}))`
- L74 (`.get`): `self.claim_check_interval = self.config.get('operations', {}).get('claim_check_interval_sec', 300)`
- L92 (`.get`): `log_config = self.config.get('logging', {})`
- L93 (`.get`): `level = getattr(logging, log_config.get('level', 'INFO'))`
- L101 (`.get`): `if log_config.get('file', True):`
- L102 (`.get`): `log_dir = Path(log_config.get('log_dir', 'tbot_logs'))`
- L383 (`.get`): `wallet_address = self.config.get('blockchain', {}).get('wallet_address')`
- L397 (`.get`): `f"Winner: {claim['position'].get('winning_outcome', 'unknown')}"`

## `archive/hesoyam_with_fill_rate_limits/dashboard/server.py` [PLATFORM]
**Transport calls in code:**
- L125 (`.get`): `won = sum(1 for r in results if r.get('pnl', 0) > 0)`
- L129 (`.get`): `pnls = [r.get('pnl', 0) for r in results]`
- L132 (`.get`): `total_cost = sum(r.get('total_cost', 0) for r in results)`
- L149 (`.get`): `total_trades = sum(r.get('trades_count', 0) for r in results)`
- L150 (`.get`): `rois = [r.get('roi_pct', 0) for r in results]`
- L204 (`.get`): `@app.get("/")`
- L216 (`.get`): `@app.get("/api/markets")`
- L221 (`.get`): `results = [r for r in results if r.get('mode', 'paper') == mode]`
- L224 (`.get`): `@app.get("/api/stats")`
- L229 (`.get`): `results = [r for r in results if r.get('mode', 'paper') == mode]`
- L233 (`.get`): `@app.get("/api/pending_claims")`
- L245 (`.get`): `if not r.get('resolved', False):`
- L247 (`.get`): `ts_str = r.get('timestamp', '')`
- L248 (`.get`): `slug = r.get('slug', '')`
- L270 (`.get`): `@app.get("/api/health")`
- L283 (`.get`): `@app.get("/api/live")`

## `archive/hesoyam_with_fill_rate_limits/tbot_logger/ws_client.py` [PLATFORM]
**External imports:** aiohttp, aiohttp

**Transport calls in code:**
- L221 (`.get`): `event_type = data.get('event_type')`
- L224 (`.get`): `asset_id = data.get('asset_id')`
- L225 (`.get`): `bids = data.get('bids', [])`
- L226 (`.get`): `asks = data.get('asks', [])`
- L235 (`.get`): `'market': data.get('market'),`
- L240 (`.get`): `'timestamp': data.get('timestamp')`
- L245 (`.get`): `f"[WS] Best prices update for {data.get('market')}: "`
- L246 (`.get`): `f"bid={data.get('best_bid')} ask={data.get('best_ask')} "`
- L247 (`.get`): `f"spread={data.get('spread')}"`
- L251 (`.get`): `logger.debug(f"[WS] Price change for {data.get('market')}")`
- L255 (`.get`): `asset_id = data.get('asset_id')`
- L258 (`.get`): `price = data.get('price')`
- L259 (`.get`): `size = data.get('size', 0)`
- L260 (`.get`): `side = data.get('side', 'unknown')  # 'buy' or 'sell'`
- L267 (`.get`): `'market': data.get('market'),`
- L273 (`.get`): `'timestamp': data.get('timestamp')`

## `dashboard/microstructure/tape_renderer.py` [PLATFORM]
**Transport calls in code:**
- L33 (`.get`): `events = tape.get('events', [])`
- L34 (`.get`): `config = tape.get('config', {})`
- L64 (`.get`): `yes_bid = np.array([t.get('yes_bid', 0) for t in ticks])`
- L65 (`.get`): `no_bid = np.array([t.get('no_bid', 0) for t in ticks])`
- L66 (`.get`): `yes_ask = np.array([t.get('yes_ask', 0) for t in ticks])`
- L67 (`.get`): `no_ask = np.array([t.get('no_ask', 0) for t in ticks])`
- L92 (`.get`): `vpins = np.array([t.get('vpin', 0) for t in ticks])`
- L93 (`.get`): `vpin_thr = config.get('vpin_threshold', 0.7)`
- L118 (`.get`): `n_fills_yes = sum(1 for f in fills if f.get('side') == 'YES')`
- L119 (`.get`): `n_fills_no = sum(1 for f in fills if f.get('side') == 'NO')`
- L127 (`.get`): `q_arr = np.array([t.get('q', 0) for t in ticks])`
- L128 (`.get`): `pairs_arr = np.array([t.get('pairs', 0) for t in ticks])`
- L160 (`.get`): `cid = tape.get('condition_id', '?')[:20]`
- L161 (`.get`): `bot_id = tape.get('bot_id', '?')`
- L164 (`.get`): `pnl = market_meta.get('pnl', 0)`
- L166 (`.get`): `winner = market_meta.get('winner', '')`

## `data_gateway.py` [TRANSPORT]
**External imports:** zmq, zmq.asyncio

**Transport calls in code:**
- L3 (`PUB`): `Data Gateway — ZMQ PUB server for A/B/C testing.`
- L10 (`PUB`): `Publishes all data to ZMQ PUB socket on tcp://*:5555.`
- L11 (`SUB`): `Bot instances subscribe as ZMQ SUB clients and receive identical data streams.`
- L36 (`zmq`): `import zmq`
- L37 (`zmq`): `import zmq.asyncio`
- L54 (`zmq`): `self._ctx = zmq.asyncio.Context()`
- L55 (`zmq`): `self._sock = self._ctx.socket(zmq.PUB)`
- L55 (`PUB`): `self._sock = self._ctx.socket(zmq.PUB)`
- L56 (`zmq`): `self._sock.setsockopt(zmq.SNDHWM, 5000)`
- L57 (`zmq`): `self._sock.setsockopt(zmq.LINGER, 0)`
- L114 (`.get`): `logger.info(f"📤 [GATEWAY] Trade #{count} broadcasted: price={message.get('price')}")`
- L145 (`.get`): `"slug": mkt.get("slug"), "condition_id": mkt.get("condition_id"),`
- L146 (`.get`): `"yes_token_id": mkt.get("yes_token_id"), "no_token_id": mkt.get("no_token_id"),`
- L147 (`.get`): `"window_timestamp": mkt.get("window_timestamp"), "window_end": mkt.get("window_end"),`
- L148 (`.get`): `"time_remaining_sec": mkt.get("window_end", 0) - int(time.time()),`
- L175 (`.get`): `logger.info(f"📤 [GATEWAY] Trade #{count} broadcasted: price={message.get('price')}")`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L28 (`.get`): `self.base_url = config.get('clob_base_url', 'https://clob.polymarket.com')`
- L29 (`.get`): `self.chain_id = config.get('chain_id', 137)`
- L32 (`.get`): `self.api_key = config.get('api_key')`
- L33 (`.get`): `self.api_secret = config.get('api_secret')`
- L34 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L37 (`.get`): `self.private_key = config.get('private_key')`
- L38 (`.get`): `self.signature_type = config.get('signature_type', 0)  # 0=EOA, 1=PROXY, 2=SAFE`
- L39 (`.get`): `self.funder = config.get('funder_address')`
- L55 (`.get`): `self.max_retries = config.get('max_retries', 3)`
- L56 (`.get`): `self.retry_delay = config.get('retry_delay', 1.0)`
- L57 (`.get`): `self.retry_backoff = config.get('retry_backoff', 2.0)`
- L119 (`.get`): `retry_after = int(response.headers.get('Retry-After', delay))`
- L278 (`.get`): `async with self.session.get(`
- L293 (`.post`): `async with self.session.post(`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/models.py` [PLATFORM]
**Transport calls in code:**
- L69 (`.get`): `book_data = message.get(side_key, {})`
- L72 (`.get`): `bids=[OrderBookLevel.from_raw(x) for x in book_data.get('bids', [])],`
- L73 (`.get`): `asks=[OrderBookLevel.from_raw(x) for x in book_data.get('asks', [])],`
- L75 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L92 (`.get`): `if message.get('endDate'):`
- L97 (`.get`): `elif message.get('expiry_timestamp'):`
- L104 (`.get`): `market_slug=message.get('market', ''),`
- L108 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L174 (`.get`): `filled_size=Decimal(str(data.get('filledAmount', '0'))),`
- L175 (`.get`): `remaining_size=Decimal(str(data.get('remainingAmount', '0'))),`
- L178 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L211 (`.get`): `aggressor=data.get('aggressor', False),`
- L212 (`.get`): `fee=Decimal(str(data.get('fee', '0'))),`
- L213 (`.get`): `fee_rate=Decimal(str(data.get('feeRate', '0')))`

## `archive/hesoyam_with_fill_rate_limits/scripts/claim_resolved.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L71 (`.get`): `slug = order.get('market_slug', '')`
- L72 (`.get`): `if slug and slug not in known_slugs and order.get('mode') == 'live':`
- L75 (`.get`): `r = requests.get('https://gamma-api.polymarket.com/markets',`
- L80 (`.get`): `'condition_id': m.get('conditionId', ''),`
- L98 (`.get`): `slug = r.get('slug', '')`
- L99 (`.get`): `if slug and slug not in known_slugs and r.get('mode') == 'live':`
- L100 (`.get`): `cond = r.get('condition_id', '')`
- L123 (`.get`): `pending = {k: v for k, v in queue.items() if v.get('status') == 'pending'}`
- L132 (`.get`): `cond_id = info.get('condition_id', '')`
- L138 (`.get`): `r = requests.get('https://gamma-api.polymarket.com/markets',`
- L144 (`.get`): `resolved = m.get('resolved', False) or m.get('umaResolutionStatus') == 'resolved'`
- L148 (`.get`): `age_hours = (time.time() - info.get('added_at', 0)) / 3600`
- L209 (`.post`): `requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage',`
- L229 (`.get`): `pending = sum(1 for v in queue.values() if v.get('status') == 'pending')`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/api/client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L29 (`.get`): `self.base_url = config.get('clob_base_url', 'https://clob.polymarket.com')`
- L30 (`.get`): `self.chain_id = config.get('chain_id', 137)`
- L33 (`.get`): `self.api_key = config.get('api_key')`
- L34 (`.get`): `self.api_secret = config.get('api_secret')`
- L35 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L38 (`.get`): `self.private_key = config.get('private_key')`
- L39 (`.get`): `self.signature_type = config.get('signature_type', 0)  # 0=EOA, 1=PROXY, 2=SAFE`
- L40 (`.get`): `self.funder = config.get('funder_address')`
- L56 (`.get`): `self.max_retries = config.get('max_retries', 3)`
- L57 (`.get`): `self.retry_delay = config.get('retry_delay', 1.0)`
- L58 (`.get`): `self.retry_backoff = config.get('retry_backoff', 2.0)`
- L120 (`.get`): `retry_after = int(response.headers.get('Retry-After', delay))`
- L279 (`.get`): `async with self.session.get(`
- L294 (`.post`): `async with self.session.post(`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/api/models.py` [PLATFORM]
**Transport calls in code:**
- L69 (`.get`): `book_data = message.get(side_key, {})`
- L72 (`.get`): `bids=[OrderBookLevel.from_raw(x) for x in book_data.get('bids', [])],`
- L73 (`.get`): `asks=[OrderBookLevel.from_raw(x) for x in book_data.get('asks', [])],`
- L75 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L92 (`.get`): `if message.get('endDate'):`
- L97 (`.get`): `elif message.get('expiry_timestamp'):`
- L104 (`.get`): `market_slug=message.get('market', ''),`
- L108 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L174 (`.get`): `filled_size=Decimal(str(data.get('filledAmount', '0'))),`
- L175 (`.get`): `remaining_size=Decimal(str(data.get('remainingAmount', '0'))),`
- L178 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L211 (`.get`): `aggressor=data.get('aggressor', False),`
- L212 (`.get`): `fee=Decimal(str(data.get('fee', '0'))),`
- L213 (`.get`): `fee_rate=Decimal(str(data.get('feeRate', '0')))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L28 (`.get`): `self.base_url = config.get('clob_base_url', 'https://clob.polymarket.com')`
- L29 (`.get`): `self.chain_id = config.get('chain_id', 137)`
- L32 (`.get`): `self.api_key = config.get('api_key')`
- L33 (`.get`): `self.api_secret = config.get('api_secret')`
- L34 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L37 (`.get`): `self.private_key = config.get('private_key')`
- L38 (`.get`): `self.signature_type = config.get('signature_type', 0)  # 0=EOA, 1=PROXY, 2=SAFE`
- L39 (`.get`): `self.funder = config.get('funder_address')`
- L55 (`.get`): `self.max_retries = config.get('max_retries', 3)`
- L56 (`.get`): `self.retry_delay = config.get('retry_delay', 1.0)`
- L57 (`.get`): `self.retry_backoff = config.get('retry_backoff', 2.0)`
- L119 (`.get`): `retry_after = int(response.headers.get('Retry-After', delay))`
- L278 (`.get`): `async with self.session.get(`
- L293 (`.post`): `async with self.session.post(`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/models.py` [PLATFORM]
**Transport calls in code:**
- L69 (`.get`): `book_data = message.get(side_key, {})`
- L72 (`.get`): `bids=[OrderBookLevel.from_raw(x) for x in book_data.get('bids', [])],`
- L73 (`.get`): `asks=[OrderBookLevel.from_raw(x) for x in book_data.get('asks', [])],`
- L75 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L92 (`.get`): `if message.get('endDate'):`
- L97 (`.get`): `elif message.get('expiry_timestamp'):`
- L104 (`.get`): `market_slug=message.get('market', ''),`
- L108 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L174 (`.get`): `filled_size=Decimal(str(data.get('filledAmount', '0'))),`
- L175 (`.get`): `remaining_size=Decimal(str(data.get('remainingAmount', '0'))),`
- L178 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L211 (`.get`): `aggressor=data.get('aggressor', False),`
- L212 (`.get`): `fee=Decimal(str(data.get('fee', '0'))),`
- L213 (`.get`): `fee_rate=Decimal(str(data.get('feeRate', '0')))`

## `tbot_core/api/client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L29 (`.get`): `self.base_url = config.get('clob_base_url', 'https://clob.polymarket.com')`
- L30 (`.get`): `self.chain_id = config.get('chain_id', 137)`
- L33 (`.get`): `self.api_key = config.get('api_key')`
- L34 (`.get`): `self.api_secret = config.get('api_secret')`
- L35 (`.get`): `self.api_passphrase = config.get('api_passphrase')`
- L38 (`.get`): `self.private_key = config.get('private_key')`
- L39 (`.get`): `self.signature_type = config.get('signature_type', 0)  # 0=EOA, 1=PROXY, 2=SAFE`
- L40 (`.get`): `self.funder = config.get('funder_address')`
- L56 (`.get`): `self.max_retries = config.get('max_retries', 3)`
- L57 (`.get`): `self.retry_delay = config.get('retry_delay', 1.0)`
- L58 (`.get`): `self.retry_backoff = config.get('retry_backoff', 2.0)`
- L120 (`.get`): `retry_after = int(response.headers.get('Retry-After', delay))`
- L279 (`.get`): `async with self.session.get(`
- L294 (`.post`): `async with self.session.post(`

## `tbot_core/api/models.py` [PLATFORM]
**Transport calls in code:**
- L69 (`.get`): `book_data = message.get(side_key, {})`
- L72 (`.get`): `bids=[OrderBookLevel.from_raw(x) for x in book_data.get('bids', [])],`
- L73 (`.get`): `asks=[OrderBookLevel.from_raw(x) for x in book_data.get('asks', [])],`
- L75 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L92 (`.get`): `if message.get('endDate'):`
- L97 (`.get`): `elif message.get('expiry_timestamp'):`
- L104 (`.get`): `market_slug=message.get('market', ''),`
- L108 (`.get`): `int(message.get('timestamp', 0)) / 1000`
- L174 (`.get`): `filled_size=Decimal(str(data.get('filledAmount', '0'))),`
- L175 (`.get`): `remaining_size=Decimal(str(data.get('remainingAmount', '0'))),`
- L178 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L211 (`.get`): `aggressor=data.get('aggressor', False),`
- L212 (`.get`): `fee=Decimal(str(data.get('fee', '0'))),`
- L213 (`.get`): `fee_rate=Decimal(str(data.get('feeRate', '0')))`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/market/analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L22 (`.get`): `self.min_bid_depth = Decimal(str(config.get('min_bid_depth_usd', 50)))`
- L23 (`.get`): `self.min_ask_depth = Decimal(str(config.get('min_ask_depth_usd', 50)))`
- L26 (`.get`): `self.max_spread = Decimal(str(config.get('max_spread', '0.10')))`
- L29 (`.get`): `self.min_edge = Decimal(str(config.get('min_edge', '0.01')))`
- L30 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L33 (`.get`): `self.depth_band = Decimal(str(config.get('depth_band', '0.05')))`
- L101 (`.get`): `max_age = self.config.get('max_stale_ms', 5000)`
- L149 (`.get`): `edge = metrics.get('edge', Decimal('0'))`
- L150 (`.get`): `total_cost = metrics.get('total_cost', Decimal('1'))`
- L160 (`.get`): `tick_size = Decimal(str(self.config.get('tick_size', '0.001')))`
- L161 (`.get`): `improve_ticks = int(self.config.get('improve_ticks', 1))`
- L189 (`.get`): `max_depth_ratio = Decimal(str(self.config.get('max_depth_ratio', '0.3')))`
- L194 (`.get`): `per_market_budget = Decimal(str(self.config.get('per_market_budget_usd', 100)))`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_risk/limits.py` [TRANSPORT]
**Transport calls in code:**
- L25 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L26 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', 0.5)))`
- L27 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L28 (`.get`): `self.max_simultaneous_markets = int(config.get('max_simultaneous_markets', 1))`
- L31 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', 5)))`
- L32 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', 50)))`
- L33 (`.get`): `self.target_size_usd = Decimal(str(config.get('target_size_total_usd', 100)))`
- L36 (`.get`): `self.pilot_clip_usd = Decimal(str(config.get('pilot_clip_usd', 5)))`
- L37 (`.get`): `self.pilot_min_filled = Decimal(str(config.get('pilot_min_filled_usd', 3)))`
- L38 (`.get`): `self.scale_in_multiplier = Decimal(str(config.get('scale_in_multiplier', 1.5)))`
- L53 (`.get`): `Decimal(str(m.get('total_cost', 0)))`
- L61 (`.get`): `used = Decimal(str(self.active_markets[market_slug].get('total_cost', 0)))`
- L149 (`.get`): `Decimal(str(m.get('total_cost', 0)))`

## `archive/dead_2026-03-04/tbot_core_market/analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L22 (`.get`): `self.min_bid_depth = Decimal(str(config.get('min_bid_depth_usd', 50)))`
- L23 (`.get`): `self.min_ask_depth = Decimal(str(config.get('min_ask_depth_usd', 50)))`
- L26 (`.get`): `self.max_spread = Decimal(str(config.get('max_spread', '0.10')))`
- L29 (`.get`): `self.min_edge = Decimal(str(config.get('min_edge', '0.01')))`
- L30 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L33 (`.get`): `self.depth_band = Decimal(str(config.get('depth_band', '0.05')))`
- L101 (`.get`): `max_age = self.config.get('max_stale_ms', 5000)`
- L149 (`.get`): `edge = metrics.get('edge', Decimal('0'))`
- L150 (`.get`): `total_cost = metrics.get('total_cost', Decimal('1'))`
- L160 (`.get`): `tick_size = Decimal(str(self.config.get('tick_size', '0.001')))`
- L161 (`.get`): `improve_ticks = int(self.config.get('improve_ticks', 1))`
- L189 (`.get`): `max_depth_ratio = Decimal(str(self.config.get('max_depth_ratio', '0.3')))`
- L194 (`.get`): `per_market_budget = Decimal(str(self.config.get('per_market_budget_usd', 100)))`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/opportunity_evaluator.py` [PLATFORM]
**Transport calls in code:**
- L422 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L423 (`.get`): `bids = book.get('bids', [])`
- L430 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L431 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L439 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L440 (`.get`): `asks = book.get('asks', [])`
- L447 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L448 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L456 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L457 (`.get`): `bids = book.get('bids', [])`
- L458 (`.get`): `asks = book.get('asks', [])`
- L465 (`.get`): `best_bid = max(Decimal(str(b.get('price', 0))) for b in bids)`
- L466 (`.get`): `best_ask = min(Decimal(str(a.get('price', 1))) for a in asks)`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/market/analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L22 (`.get`): `self.min_bid_depth = Decimal(str(config.get('min_bid_depth_usd', 50)))`
- L23 (`.get`): `self.min_ask_depth = Decimal(str(config.get('min_ask_depth_usd', 50)))`
- L26 (`.get`): `self.max_spread = Decimal(str(config.get('max_spread', '0.10')))`
- L29 (`.get`): `self.min_edge = Decimal(str(config.get('min_edge', '0.01')))`
- L30 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L33 (`.get`): `self.depth_band = Decimal(str(config.get('depth_band', '0.05')))`
- L101 (`.get`): `max_age = self.config.get('max_stale_ms', 5000)`
- L149 (`.get`): `edge = metrics.get('edge', Decimal('0'))`
- L150 (`.get`): `total_cost = metrics.get('total_cost', Decimal('1'))`
- L160 (`.get`): `tick_size = Decimal(str(self.config.get('tick_size', '0.001')))`
- L161 (`.get`): `improve_ticks = int(self.config.get('improve_ticks', 1))`
- L189 (`.get`): `max_depth_ratio = Decimal(str(self.config.get('max_depth_ratio', '0.3')))`
- L194 (`.get`): `per_market_budget = Decimal(str(self.config.get('per_market_budget_usd', 100)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/market/analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L22 (`.get`): `self.min_bid_depth = Decimal(str(config.get('min_bid_depth_usd', 50)))`
- L23 (`.get`): `self.min_ask_depth = Decimal(str(config.get('min_ask_depth_usd', 50)))`
- L26 (`.get`): `self.max_spread = Decimal(str(config.get('max_spread', '0.10')))`
- L29 (`.get`): `self.min_edge = Decimal(str(config.get('min_edge', '0.01')))`
- L30 (`.get`): `self.entry_threshold = Decimal(str(config.get('entry_threshold', '0.98')))`
- L33 (`.get`): `self.depth_band = Decimal(str(config.get('depth_band', '0.05')))`
- L101 (`.get`): `max_age = self.config.get('max_stale_ms', 5000)`
- L149 (`.get`): `edge = metrics.get('edge', Decimal('0'))`
- L150 (`.get`): `total_cost = metrics.get('total_cost', Decimal('1'))`
- L160 (`.get`): `tick_size = Decimal(str(self.config.get('tick_size', '0.001')))`
- L161 (`.get`): `improve_ticks = int(self.config.get('improve_ticks', 1))`
- L189 (`.get`): `max_depth_ratio = Decimal(str(self.config.get('max_depth_ratio', '0.3')))`
- L194 (`.get`): `per_market_budget = Decimal(str(self.config.get('per_market_budget_usd', 100)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_risk/limits.py` [TRANSPORT]
**Transport calls in code:**
- L25 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L26 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', 0.5)))`
- L27 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L28 (`.get`): `self.max_simultaneous_markets = int(config.get('max_simultaneous_markets', 1))`
- L31 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', 5)))`
- L32 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', 50)))`
- L33 (`.get`): `self.target_size_usd = Decimal(str(config.get('target_size_total_usd', 100)))`
- L36 (`.get`): `self.pilot_clip_usd = Decimal(str(config.get('pilot_clip_usd', 5)))`
- L37 (`.get`): `self.pilot_min_filled = Decimal(str(config.get('pilot_min_filled_usd', 3)))`
- L38 (`.get`): `self.scale_in_multiplier = Decimal(str(config.get('scale_in_multiplier', 1.5)))`
- L53 (`.get`): `Decimal(str(m.get('total_cost', 0)))`
- L61 (`.get`): `used = Decimal(str(self.active_markets[market_slug].get('total_cost', 0)))`
- L149 (`.get`): `Decimal(str(m.get('total_cost', 0)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_risk/limits.py` [TRANSPORT]
**Transport calls in code:**
- L25 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L26 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', 0.5)))`
- L27 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L28 (`.get`): `self.max_simultaneous_markets = int(config.get('max_simultaneous_markets', 1))`
- L31 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', 5)))`
- L32 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', 50)))`
- L33 (`.get`): `self.target_size_usd = Decimal(str(config.get('target_size_total_usd', 100)))`
- L36 (`.get`): `self.pilot_clip_usd = Decimal(str(config.get('pilot_clip_usd', 5)))`
- L37 (`.get`): `self.pilot_min_filled = Decimal(str(config.get('pilot_min_filled_usd', 3)))`
- L38 (`.get`): `self.scale_in_multiplier = Decimal(str(config.get('scale_in_multiplier', 1.5)))`
- L53 (`.get`): `Decimal(str(m.get('total_cost', 0)))`
- L61 (`.get`): `used = Decimal(str(self.active_markets[market_slug].get('total_cost', 0)))`
- L149 (`.get`): `Decimal(str(m.get('total_cost', 0)))`

## `strategies/gabagool/opportunity_evaluator.py` [PLATFORM]
**Transport calls in code:**
- L422 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L423 (`.get`): `bids = book.get('bids', [])`
- L430 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L431 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L439 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L440 (`.get`): `asks = book.get('asks', [])`
- L447 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L448 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L456 (`.get`): `book = orderbook.get(f'{token}_book', orderbook.get(token, {}))`
- L457 (`.get`): `bids = book.get('bids', [])`
- L458 (`.get`): `asks = book.get('asks', [])`
- L465 (`.get`): `best_bid = max(Decimal(str(b.get('price', 0))) for b in bids)`
- L466 (`.get`): `best_ask = min(Decimal(str(a.get('price', 1))) for a in asks)`

## `tbot_risk/limits.py` [TRANSPORT]
**Transport calls in code:**
- L25 (`.get`): `self.total_equity = Decimal(str(config.get('total_equity_usd', 1000)))`
- L26 (`.get`): `self.deployable_ratio = Decimal(str(config.get('deployable_capital_ratio', 0.5)))`
- L27 (`.get`): `self.per_market_budget = Decimal(str(config.get('per_market_budget_usd', 100)))`
- L28 (`.get`): `self.max_simultaneous_markets = int(config.get('max_simultaneous_markets', 1))`
- L31 (`.get`): `self.base_clip_usd = Decimal(str(config.get('base_clip_usd', 5)))`
- L32 (`.get`): `self.max_clip_usd = Decimal(str(config.get('max_clip_usd', 50)))`
- L33 (`.get`): `self.target_size_usd = Decimal(str(config.get('target_size_total_usd', 100)))`
- L36 (`.get`): `self.pilot_clip_usd = Decimal(str(config.get('pilot_clip_usd', 5)))`
- L37 (`.get`): `self.pilot_min_filled = Decimal(str(config.get('pilot_min_filled_usd', 3)))`
- L38 (`.get`): `self.scale_in_multiplier = Decimal(str(config.get('scale_in_multiplier', 1.5)))`
- L53 (`.get`): `Decimal(str(m.get('total_cost', 0)))`
- L61 (`.get`): `used = Decimal(str(self.active_markets[market_slug].get('total_cost', 0)))`
- L149 (`.get`): `Decimal(str(m.get('total_cost', 0)))`

## `archive/dead_2026-03-04/tbot_core_blockchain/ctf_client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L69 (`.get`): `self.w3 = Web3(Web3.HTTPProvider(config.get('polygon_rpc', POLYGON_RPC)))`
- L72 (`.get`): `self.private_key = config.get('private_key')`
- L83 (`.get`): `self.builder_api_key = config.get('builder_api_key')`
- L84 (`.get`): `self.builder_secret = config.get('builder_secret')`
- L85 (`.get`): `self.builder_passphrase = config.get('builder_passphrase')`
- L245 (`.get`): `async with session.get(url) as resp:`
- L250 (`.get`): `nonce = payload.get('nonce', '0')`
- L267 (`.post`): `async with session.post(`
- L276 (`.get`): `tx_id = result.get('transactionID')`
- L292 (`.get`): `async with session.get(url) as resp:`
- L297 (`.get`): `state = txn.get('state')`
- L300 (`.get`): `self.logger.info(f"TX confirmed: {txn.get('transactionHash')}")`

## `archive/dead_2026-03-04/test_live_order_ws.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L45 (`.get`): `events = requests.get(url, params=params).json()`
- L53 (`.get`): `if 'btc' not in event.get('title', '').lower():`
- L56 (`.get`): `markets = event.get('markets', [])`
- L58 (`.get`): `end_iso = m.get('endDateIso')`
- L59 (`.get`): `if not end_iso or m.get('closed'):`
- L64 (`.get`): `slug = m.get('slug', '')`
- L77 (`.get`): `token_ids = btc_market.get('clobTokenIds', '').strip('[]"').split('","')`
- L99 (`.get`): `asset_id = message.get('asset_id', '')`
- L102 (`.get`): `bids = message.get('bids', [])`
- L104 (`.get`): `first_bid = float(bids[0].get('price', 0.50))`
- L149 (`.get`): `print(f'   Status через 2s: {order.get("status", "?")}')`
- L157 (`.get`): `print(f'✅ ОТМЕНЁН! Final: {order_final.get("status", "?")}')`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/blockchain/ctf_client.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L69 (`.get`): `self.w3 = Web3(Web3.HTTPProvider(config.get('polygon_rpc', POLYGON_RPC)))`
- L72 (`.get`): `self.private_key = config.get('private_key')`
- L83 (`.get`): `self.builder_api_key = config.get('builder_api_key')`
- L84 (`.get`): `self.builder_secret = config.get('builder_secret')`
- L85 (`.get`): `self.builder_passphrase = config.get('builder_passphrase')`
- L245 (`.get`): `async with session.get(url) as resp:`
- L250 (`.get`): `nonce = payload.get('nonce', '0')`
- L267 (`.post`): `async with session.post(`
- L276 (`.get`): `tx_id = result.get('transactionID')`
- L292 (`.get`): `async with session.get(url) as resp:`
- L297 (`.get`): `state = txn.get('state')`
- L300 (`.get`): `self.logger.info(f"TX confirmed: {txn.get('transactionHash')}")`

## `tbot_logger/poly_orderbook_swarm.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L70 (`.get`): `p = float(level.get('price', 0))`
- L71 (`.get`): `s = float(level.get('size', 0))`
- L85 (`.get`): `if side_map.get(p) != s:`
- L284 (`.get`): `pm_id = os.environ.get('pm_id')`
- L309 (`.get`): `asset_id = msg.get('asset_id')`
- L315 (`.get`): `mirror = self.mirrors.get(aid_str)`
- L319 (`.get`): `etype = msg.get('event_type')`
- L327 (`.get`): `has_changes = mirror.apply_delta(msg.get('bids', []), msg.get('asks', []))`
- L376 (`.get`): `'price': float(msg.get('price', 0)),`
- L377 (`.get`): `'size': float(msg.get('size', 0)),`
- L378 (`.get`): `'side': msg.get('side', 'unknown'),`
- L379 (`.get`): `'timestamp': msg.get('timestamp')`

## `archive/dead_2026-03-04/backtester_scripts/methodology_report.py` [TRANSPORT]
**Transport calls in code:**
- L131 (`.get`): `c.get('avg_capital_util', 0),  # higher utilization is better`
- L204 (`.get`): `for mid, _ in all_pnls.get(c, []):`
- L220 (`.get`): `pnls = all_pnls.get(c, [])`
- L316 (`.get`): `cap_utils = [c.get('avg_capital_util', 0) for c in configs]`
- L340 (`.get`): `stab = stability.get(c['config'], 0.5)`
- L360 (`.get`): `stab = stability.get(cfg, 0.5)`
- L361 (`.get`): `ci_low, ci_high = bootstrap_results.get(cfg, (0.0, 0.0))`
- L363 (`.get`): `cap_util = c.get('avg_capital_util', 0)`
- L418 (`.get`): `pnl_values = [pnl for _, pnl in all_pnls.get(cfg, [])]`
- L453 (`.get`): `n_ci_significant = sum(1 for cfg in config_names if bootstrap_results.get(cfg, (0,))[0] > 0)`
- L454 (`.get`): `avg_stability = sum(stability.get(c, 0.5) for c in config_names) / len(config_names) if config_names else 0`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/ws_client.py` [PLATFORM]
**External imports:** aiohttp, aiohttp

**Transport calls in code:**
- L125 (`.get`): `event_type = data.get('event_type')`
- L128 (`.get`): `asset_id = data.get('asset_id')`
- L129 (`.get`): `bids = data.get('bids', [])`
- L130 (`.get`): `asks = data.get('asks', [])`
- L139 (`.get`): `'market': data.get('market'),`
- L144 (`.get`): `'timestamp': data.get('timestamp')`
- L149 (`.get`): `f"Best prices update for {data.get('market')}: "`
- L150 (`.get`): `f"bid={data.get('best_bid')} ask={data.get('best_ask')} "`
- L151 (`.get`): `f"spread={data.get('spread')}"`
- L155 (`.get`): `logger.debug(f"Price change for {data.get('market')}")`
- L158 (`.get`): `logger.debug(f"Last trade: {data.get('price')} for {data.get('asset_id')}")`

## `archive/dead_2026-03-04/risk_manager.py` [TRANSPORT]
**Transport calls in code:**
- L253 (`.get`): `saved_bankroll = data.get('initial_bankroll', 0)`
- L261 (`.get`): `saved_at = data.get('saved_at', 0)`
- L268 (`.get`): `self.status.realized_pnl = Decimal(str(data.get('realized_pnl', 0)))`
- L269 (`.get`): `self.status.realized_pnl_pct = data.get('realized_pnl_pct', 0.0)`
- L271 (`.get`): `self.status.markets_resolved = data.get('markets_resolved', 0)`
- L272 (`.get`): `self.status.markets_won = data.get('markets_won', 0)`
- L273 (`.get`): `self.status.markets_lost = data.get('markets_lost', 0)`
- L274 (`.get`): `self.status.stop_triggered = data.get('stop_triggered', False)`
- L275 (`.get`): `self.status.stop_reason = data.get('stop_reason', '')`
- L277 (`.get`): `state_str = data.get('state', 'NORMAL')`
- L496 (`.get`): `emoji = state_emoji.get(self.status.state, "❓")`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/risk_manager.py` [TRANSPORT]
**Transport calls in code:**
- L253 (`.get`): `saved_bankroll = data.get('initial_bankroll', 0)`
- L261 (`.get`): `saved_at = data.get('saved_at', 0)`
- L268 (`.get`): `self.status.realized_pnl = Decimal(str(data.get('realized_pnl', 0)))`
- L269 (`.get`): `self.status.realized_pnl_pct = data.get('realized_pnl_pct', 0.0)`
- L271 (`.get`): `self.status.markets_resolved = data.get('markets_resolved', 0)`
- L272 (`.get`): `self.status.markets_won = data.get('markets_won', 0)`
- L273 (`.get`): `self.status.markets_lost = data.get('markets_lost', 0)`
- L274 (`.get`): `self.status.stop_triggered = data.get('stop_triggered', False)`
- L275 (`.get`): `self.status.stop_reason = data.get('stop_reason', '')`
- L277 (`.get`): `state_str = data.get('state', 'NORMAL')`
- L496 (`.get`): `emoji = state_emoji.get(self.status.state, "❓")`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/ws_client.py` [PLATFORM]
**External imports:** aiohttp, aiohttp

**Transport calls in code:**
- L125 (`.get`): `event_type = data.get('event_type')`
- L128 (`.get`): `asset_id = data.get('asset_id')`
- L129 (`.get`): `bids = data.get('bids', [])`
- L130 (`.get`): `asks = data.get('asks', [])`
- L139 (`.get`): `'market': data.get('market'),`
- L144 (`.get`): `'timestamp': data.get('timestamp')`
- L149 (`.get`): `f"Best prices update for {data.get('market')}: "`
- L150 (`.get`): `f"bid={data.get('best_bid')} ask={data.get('best_ask')} "`
- L151 (`.get`): `f"spread={data.get('spread')}"`
- L155 (`.get`): `logger.debug(f"Price change for {data.get('market')}")`
- L158 (`.get`): `logger.debug(f"Last trade: {data.get('price')} for {data.get('asset_id')}")`

## `archive/mag_quarantine/lorine93s-analysis/src/main.py` [PLATFORM]
**Transport calls in code:**
- L56 (`.get`): `if market.get("id") == self.settings.market_id:`
- L57 (`.get`): `logger.info("market_discovered", market_id=market.get("id"), question=market.get("question"))`
- L77 (`.get`): `if data.get("market") == self.settings.market_id:`
- L78 (`.get`): `self.current_orderbook = data.get("book", self.current_orderbook)`
- L94 (`.get`): `best_bid = float(orderbook.get("best_bid", 0))`
- L95 (`.get`): `best_ask = float(orderbook.get("best_ask", 1))`
- L101 (`.get`): `yes_token_id = market_info.get("yes_token_id", "")`
- L102 (`.get`): `no_token_id = market_info.get("no_token_id", "")`
- L126 (`.get`): `order_time = order.get("timestamp", 0)`
- L130 (`.get`): `order_ids_to_cancel.append(order.get("id"))`
- L160 (`.get`): `order_id=result.get("id"),`

## `backtester/optimizer/tier_inheritance.py` [TRANSPORT]
**Transport calls in code:**
- L85 (`.get`): `if len(spec.get('values', [])) > 1}`
- L91 (`.get`): `params = cfg.get('params', cfg)`
- L197 (`.get`): `for param, value in inheritance.get('freeze_overrides', {}).items():`
- L201 (`.get`): `for param, values in inheritance.get('optimize_overrides', {}).items():`
- L215 (`.get`): `freeze_ov = inheritance.get('freeze_overrides', {})`
- L216 (`.get`): `opt_ov = inheritance.get('optimize_overrides', {})`
- L320 (`.get`): `top_configs = data.get('top_configs', [])`
- L348 (`.get`): `opt_before = sum(1 for s in ps_before.values() if len(s.get('values', [])) > 1)`
- L349 (`.get`): `opt_after = sum(1 for s in ps_after.values() if len(s.get('values', [])) > 1)`
- L353 (`.get`): `if len(s.get('values', [])) > 1:`
- L356 (`.get`): `if len(s.get('values', [])) > 1:`

## `scripts/analyze_fanova.py` [TRANSPORT]
**Transport calls in code:**
- L59 (`.get`): `'n_samples': data.get('n_samples', len(results)),`
- L60 (`.get`): `'timestamp': data.get('timestamp', ''),`
- L61 (`.get`): `'frozen_params': data.get('frozen_params', {}),`
- L62 (`.get`): `'metadata': data.get('metadata', {}),`
- L176 (`.get`): `gb_top = top_stats.get(GEARBOX_PARAM, {})`
- L177 (`.get`): `gb_top_mean = gb_top.get('mean', 0)`
- L178 (`.get`): `gb_top_std = gb_top.get('std', 0)`
- L181 (`.get`): `cd_top = top_stats.get(COOLDOWN_PARAM, {})`
- L182 (`.get`): `cd_top_mean = cd_top.get('mean', 0)`
- L290 (`.get`): `ts = analysis['top_samples_stats'].get(name, {})`
- L302 (`.get`): `emoji = trigger_emoji.get(diagnosis['trigger'], '❓')`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L61 (`.get`): `entry_threshold = float(constraints.get('entry_threshold', 0.98))`
- L62 (`.get`): `max_imbalance = float(constraints.get('max_imbalance', 100))`
- L63 (`.get`): `min_size = float(constraints.get('base_clip_usd', 5))`
- L64 (`.get`): `max_size = float(constraints.get('max_clip_usd', 50))`
- L65 (`.get`): `tick_size = float(constraints.get('tick_size', 0.001))`
- L66 (`.get`): `improve_ticks = int(constraints.get('improve_ticks', 1))`
- L69 (`.get`): `current_yes = float(current_position.get('yes_shares', 0))`
- L70 (`.get`): `current_no = float(current_position.get('no_shares', 0))`
- L141 (`.get`): `return float(bids[0].get('price', 0))`
- L156 (`.get`): `return float(asks[0].get('price', 0))`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/results_tracker.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L314 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L326 (`.get`): `resolved = market.get('resolved', False)`
- L329 (`.get`): `uma_status = market.get('umaResolutionStatus', '')`
- L335 (`.get`): `outcome_prices = market.get('outcomePrices', [])`
- L344 (`.get`): `winning_outcome = market.get('winningOutcome')`
- L419 (`.get`): `if r.get('timestamp', '').startswith(date):`
- L434 (`.get`): `total_pnl = sum(r.get('pnl', 0) for r in results)`
- L435 (`.get`): `total_cost = sum(r.get('total_cost', 0) for r in results)`
- L436 (`.get`): `wins = sum(1 for r in results if r.get('pnl', 0) > 0)`
- L517 (`.get`): `result = tracker.pending_markets.get("test-market-123")`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L61 (`.get`): `entry_threshold = float(constraints.get('entry_threshold', 0.98))`
- L62 (`.get`): `max_imbalance = float(constraints.get('max_imbalance', 100))`
- L63 (`.get`): `min_size = float(constraints.get('base_clip_usd', 5))`
- L64 (`.get`): `max_size = float(constraints.get('max_clip_usd', 50))`
- L65 (`.get`): `tick_size = float(constraints.get('tick_size', 0.001))`
- L66 (`.get`): `improve_ticks = int(constraints.get('improve_ticks', 1))`
- L69 (`.get`): `current_yes = float(current_position.get('yes_shares', 0))`
- L70 (`.get`): `current_no = float(current_position.get('no_shares', 0))`
- L141 (`.get`): `return float(bids[0].get('price', 0))`
- L156 (`.get`): `return float(asks[0].get('price', 0))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L61 (`.get`): `entry_threshold = float(constraints.get('entry_threshold', 0.98))`
- L62 (`.get`): `max_imbalance = float(constraints.get('max_imbalance', 100))`
- L63 (`.get`): `min_size = float(constraints.get('base_clip_usd', 5))`
- L64 (`.get`): `max_size = float(constraints.get('max_clip_usd', 50))`
- L65 (`.get`): `tick_size = float(constraints.get('tick_size', 0.001))`
- L66 (`.get`): `improve_ticks = int(constraints.get('improve_ticks', 1))`
- L69 (`.get`): `current_yes = float(current_position.get('yes_shares', 0))`
- L70 (`.get`): `current_no = float(current_position.get('no_shares', 0))`
- L141 (`.get`): `return float(bids[0].get('price', 0))`
- L156 (`.get`): `return float(asks[0].get('price', 0))`

## `backtester/optimizer/lhs_screening.py` [TRANSPORT]
**Transport calls in code:**
- L65 (`.get`): `cfg.deposit = params.get('deposit', deposit)`
- L310 (`.get`): `val = r['params'].get(param)`
- L344 (`.get`): `val = r['params'].get(name)`
- L386 (`.get`): `rf_val = rf_impacts.get(name, 0)`
- L387 (`.get`): `vom_val = vom_impacts.get(name, 0)`
- L427 (`.get`): `imp = impacts.get(param, 0.0)`
- L555 (`.get`): `n_opt = sum(1 for s in modified_space.values() if len(s.get('values', [])) > 1)`
- L556 (`.get`): `n_frz = sum(1 for s in modified_space.values() if len(s.get('values', [])) == 1)`
- L580 (`.get`): `n_opt = sum(1 for s in modified_space.values() if len(s.get('values', [])) > 1)`
- L581 (`.get`): `n_frz = sum(1 for s in modified_space.values() if len(s.get('values', [])) == 1)`

## `backtester/scripts/hard_mode_autopsy.py` [TRANSPORT]
**Transport calls in code:**
- L119 (`.get`): `orders = m.get('orders_placed', 1)`
- L121 (`.get`): `cu = m.get('capital_utilization', 0.0)`
- L122 (`.get`): `tf = m.get('toxic_fills', 0)`
- L123 (`.get`): `tc = m.get('toxic_fill_cost', 0.0)`
- L124 (`.get`): `ps = m.get('avg_pair_sum', 0.0)`
- L125 (`.get`): `ticks = m.get('ticks_processed', 1)`
- L126 (`.get`): `l0b = m.get('l0_blocked_ticks', 0)`
- L128 (`.get`): `rf = m.get('regime_flat_ticks', 0)`
- L129 (`.get`): `rt = m.get('regime_trend_ticks', 0)`
- L130 (`.get`): `rx = m.get('regime_toxic_ticks', 0)`

## `strategies/gabagool/recovery_module.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.enabled = config.get('recovery_enabled', True)`
- L62 (`.get`): `self.max_loss_pct = float(config.get('recovery_max_loss_pct', 2.0)) / 100.0  # 2% → 0.02`
- L63 (`.get`): `self.min_shares = int(config.get('recovery_min_shares', 10))`
- L64 (`.get`): `self.max_budget_pct = float(config.get('recovery_max_budget_pct', 30.0)) / 100.0  # 30% → 0.30`
- L65 (`.get`): `self.min_time_left = float(config.get('recovery_min_time_left', 60))`
- L66 (`.get`): `self.min_imbalance_pct = float(config.get('recovery_min_imbalance_pct', 20.0))`
- L69 (`.get`): `self.max_ask_price = float(config.get('recovery_max_ask_price', 0.70))`
- L338 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L339 (`.get`): `asks = book.get('asks', [])`
- L343 (`.get`): `return min(float(a.get('price', 1)) for a in asks)`

## `strategies/gabagool/results_tracker.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L344 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L356 (`.get`): `resolved = market.get('resolved', False)`
- L359 (`.get`): `uma_status = market.get('umaResolutionStatus', '')`
- L365 (`.get`): `outcome_prices = market.get('outcomePrices', [])`
- L374 (`.get`): `winning_outcome = market.get('winningOutcome')`
- L463 (`.get`): `if r.get('timestamp', '').startswith(date):`
- L478 (`.get`): `total_pnl = sum(r.get('pnl', 0) for r in results)`
- L479 (`.get`): `total_cost = sum(r.get('total_cost', 0) for r in results)`
- L480 (`.get`): `wins = sum(1 for r in results if r.get('pnl', 0) > 0)`
- L561 (`.get`): `result = tracker.pending_markets.get("test-market-123")`

## `tbot_core/strategy/optimizer.py` [TRANSPORT]
**Transport calls in code:**
- L61 (`.get`): `entry_threshold = float(constraints.get('entry_threshold', 0.98))`
- L62 (`.get`): `max_imbalance = float(constraints.get('max_imbalance', 100))`
- L63 (`.get`): `min_size = float(constraints.get('base_clip_usd', 5))`
- L64 (`.get`): `max_size = float(constraints.get('max_clip_usd', 50))`
- L65 (`.get`): `tick_size = float(constraints.get('tick_size', 0.001))`
- L66 (`.get`): `improve_ticks = int(constraints.get('improve_ticks', 1))`
- L69 (`.get`): `current_yes = float(current_position.get('yes_shares', 0))`
- L70 (`.get`): `current_no = float(current_position.get('no_shares', 0))`
- L141 (`.get`): `return float(bids[0].get('price', 0))`
- L156 (`.get`): `return float(asks[0].get('price', 0))`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/claim_manager.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L45 (`.get`): `async with session.get(url) as response:`
- L50 (`.get`): `markets = data.get('markets', [])`
- L56 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved',`
- L57 (`.get`): `'condition_id': market.get('conditionId'),`
- L58 (`.get`): `'winning_outcome': market.get('winningOutcome'),`
- L59 (`.get`): `'resolution_time': market.get('resolutionTime')`
- L109 (`.get`): `async with session.get(url) as response:`
- L117 (`.get`): `market_slug = pos.get('marketSlug')`
- L122 (`.get`): `if resolution.get('resolved'):`

## `archive/dead_2026-03-04/tbot_core_execution/claim_manager.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L45 (`.get`): `async with session.get(url) as response:`
- L50 (`.get`): `markets = data.get('markets', [])`
- L56 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved',`
- L57 (`.get`): `'condition_id': market.get('conditionId'),`
- L58 (`.get`): `'winning_outcome': market.get('winningOutcome'),`
- L59 (`.get`): `'resolution_time': market.get('resolutionTime')`
- L109 (`.get`): `async with session.get(url) as response:`
- L117 (`.get`): `market_slug = pos.get('marketSlug')`
- L122 (`.get`): `if resolution.get('resolved'):`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/order_logger.py` [PLATFORM]
**Transport calls in code:**
- L206 (`.get`): `logger.debug(f"[ORDER] Updated | {local_id} | {updates.get('status', '?')}")`
- L344 (`.get`): `local_id = record.get('local_id')`
- L349 (`.get`): `if record.get('market_slug') == market_slug:`
- L369 (`.get`): `status = record.get('status', '')`
- L375 (`.get`): `intent_ms = record.get('intent_time_ms')`
- L376 (`.get`): `fill_ms = record.get('fill_time_ms')`
- L377 (`.get`): `sent_ms = record.get('sent_time_ms')`
- L427 (`.get`): `local_id = record.get('local_id')`
- L429 (`.get`): `orders[local_id] = record.get('status', 'INTENT')`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/recovery_module.py` [PLATFORM]
**Transport calls in code:**
- L61 (`.get`): `self.enabled = config.get('recovery_enabled', True)`
- L62 (`.get`): `self.max_loss_pct = float(config.get('recovery_max_loss_pct', 2.0)) / 100.0  # 2% → 0.02`
- L63 (`.get`): `self.min_shares = int(config.get('recovery_min_shares', 10))`
- L64 (`.get`): `self.max_budget_pct = float(config.get('recovery_max_budget_pct', 30.0)) / 100.0  # 30% → 0.30`
- L65 (`.get`): `self.min_time_left = float(config.get('recovery_min_time_left', 60))`
- L66 (`.get`): `self.min_imbalance_pct = float(config.get('recovery_min_imbalance_pct', 20.0))`
- L321 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L322 (`.get`): `asks = book.get('asks', [])`
- L326 (`.get`): `return min(float(a.get('price', 1)) for a in asks)`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/claim_manager.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L45 (`.get`): `async with session.get(url) as response:`
- L50 (`.get`): `markets = data.get('markets', [])`
- L56 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved',`
- L57 (`.get`): `'condition_id': market.get('conditionId'),`
- L58 (`.get`): `'winning_outcome': market.get('winningOutcome'),`
- L59 (`.get`): `'resolution_time': market.get('resolutionTime')`
- L109 (`.get`): `async with session.get(url) as response:`
- L117 (`.get`): `market_slug = pos.get('marketSlug')`
- L122 (`.get`): `if resolution.get('resolved'):`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/claim_manager.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L45 (`.get`): `async with session.get(url) as response:`
- L50 (`.get`): `markets = data.get('markets', [])`
- L56 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved',`
- L57 (`.get`): `'condition_id': market.get('conditionId'),`
- L58 (`.get`): `'winning_outcome': market.get('winningOutcome'),`
- L59 (`.get`): `'resolution_time': market.get('resolutionTime')`
- L109 (`.get`): `async with session.get(url) as response:`
- L117 (`.get`): `market_slug = pos.get('marketSlug')`
- L122 (`.get`): `if resolution.get('resolved'):`

## `strategies/gabagool/order_logger.py` [PLATFORM]
**Transport calls in code:**
- L206 (`.get`): `logger.debug(f"[ORDER] Updated | {local_id} | {updates.get('status', '?')}")`
- L344 (`.get`): `local_id = record.get('local_id')`
- L349 (`.get`): `if record.get('market_slug') == market_slug:`
- L369 (`.get`): `status = record.get('status', '')`
- L375 (`.get`): `intent_ms = record.get('intent_time_ms')`
- L376 (`.get`): `fill_ms = record.get('fill_time_ms')`
- L377 (`.get`): `sent_ms = record.get('sent_time_ms')`
- L427 (`.get`): `local_id = record.get('local_id')`
- L429 (`.get`): `orders[local_id] = record.get('status', 'INTENT')`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/market_api.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L43 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L48 (`.get`): `markets = data.get('markets', [])`
- L54 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L64 (`.get`): `'condition_id': market.get('conditionId'),`
- L68 (`.get`): `'question': market.get('question', ''),`
- L69 (`.get`): `'accepting_orders': market.get('acceptingOrders', False),`
- L70 (`.get`): `'closed': market.get('closed', True),`
- L73 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/market_api.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L26 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L31 (`.get`): `markets = data.get('markets', [])`
- L36 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L46 (`.get`): `condition_id=market.get('conditionId'),`
- L50 (`.get`): `question=market.get('question', ''),`
- L51 (`.get`): `accepting_orders=market.get('acceptingOrders', False),`
- L52 (`.get`): `closed=market.get('closed', True),`
- L55 (`.get`): `resolved=market.get('umaResolutionStatus') == 'resolved'`

## `archive/dead_2026-03-04/market_api.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L26 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L31 (`.get`): `markets = data.get('markets', [])`
- L36 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L46 (`.get`): `condition_id=market.get('conditionId'),`
- L50 (`.get`): `question=market.get('question', ''),`
- L51 (`.get`): `accepting_orders=market.get('acceptingOrders', False),`
- L52 (`.get`): `closed=market.get('closed', True),`
- L55 (`.get`): `resolved=market.get('umaResolutionStatus') == 'resolved'`

## `archive/dead_2026-03-04/test_live_order_direct.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L44 (`.get`): `slug = state.get('market_slug')`
- L45 (`.get`): `condition_id = state.get('condition_id')`
- L56 (`.get`): `market = requests.get(f'https://gamma-api.polymarket.com/markets/slug/{slug}').json()`
- L57 (`.get`): `token_ids = market.get('clobTokenIds', '').strip('[]"').split('","')`
- L72 (`.get`): `if msg.get('asset_id') == yes_token:`
- L73 (`.get`): `bids = msg.get('bids', [])`
- L75 (`.get`): `best_bid_price = float(bids[0].get('price', 0.50))`
- L110 (`.get`): `print(f'   Status: {order.get("status", "?")}')`

## `archive/hesoyam_with_fill_rate_limits/backtester/scripts/methodology_report.py` [TRANSPORT]
**Transport calls in code:**
- L200 (`.get`): `for mid, _ in all_pnls.get(c, []):`
- L216 (`.get`): `pnls = all_pnls.get(c, [])`
- L333 (`.get`): `stab = stability.get(c['config'], 0.5)`
- L353 (`.get`): `stab = stability.get(cfg, 0.5)`
- L354 (`.get`): `ci_low, ci_high = bootstrap_results.get(cfg, (0.0, 0.0))`
- L409 (`.get`): `pnl_values = [pnl for _, pnl in all_pnls.get(cfg, [])]`
- L443 (`.get`): `n_ci_significant = sum(1 for cfg in config_names if bootstrap_results.get(cfg, (0,))[0] > 0)`
- L444 (`.get`): `avg_stability = sum(stability.get(c, 0.5) for c in config_names) / len(config_names) if config_names else 0`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/order_pricer.py` [TRANSPORT]
**Transport calls in code:**
- L149 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L150 (`.get`): `bids = book.get('bids', [])`
- L157 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L158 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L167 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L168 (`.get`): `asks = book.get('asks', [])`
- L175 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L176 (`.get`): `return Decimal(str(best.get('price', 1)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/api/market_api.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L43 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L48 (`.get`): `markets = data.get('markets', [])`
- L54 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L64 (`.get`): `'condition_id': market.get('conditionId'),`
- L68 (`.get`): `'question': market.get('question', ''),`
- L69 (`.get`): `'accepting_orders': market.get('acceptingOrders', False),`
- L70 (`.get`): `'closed': market.get('closed', True),`
- L73 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/market_api.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L26 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L31 (`.get`): `markets = data.get('markets', [])`
- L36 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L46 (`.get`): `condition_id=market.get('conditionId'),`
- L50 (`.get`): `question=market.get('question', ''),`
- L51 (`.get`): `accepting_orders=market.get('acceptingOrders', False),`
- L52 (`.get`): `closed=market.get('closed', True),`
- L55 (`.get`): `resolved=market.get('umaResolutionStatus') == 'resolved'`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/market_api.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L43 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L48 (`.get`): `markets = data.get('markets', [])`
- L54 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L64 (`.get`): `'condition_id': market.get('conditionId'),`
- L68 (`.get`): `'question': market.get('question', ''),`
- L69 (`.get`): `'accepting_orders': market.get('acceptingOrders', False),`
- L70 (`.get`): `'closed': market.get('closed', True),`
- L73 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/market_api.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L26 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L31 (`.get`): `markets = data.get('markets', [])`
- L36 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L46 (`.get`): `condition_id=market.get('conditionId'),`
- L50 (`.get`): `question=market.get('question', ''),`
- L51 (`.get`): `accepting_orders=market.get('acceptingOrders', False),`
- L52 (`.get`): `closed=market.get('closed', True),`
- L55 (`.get`): `resolved=market.get('umaResolutionStatus') == 'resolved'`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/strike_fetcher.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L81 (`.get`): `async with session.get(`
- L94 (`.get`): `if data.get("error"):`
- L99 (`.get`): `close_price = data.get("closePrice")`
- L103 (`.get`): `open_price = data.get("openPrice")`
- L122 (`.get`): `if slug in self._cache and self._cache[slug].get('verified'):`
- L133 (`.get`): `prev = self._cache.get(slug, {}).get('strike')`
- L200 (`.get`): `cached = self._cache.get(slug)`
- L235 (`.get`): `cached = self._cache.get(slug)`

## `archive/hesoyam_with_fill_rate_limits/tbot_logger/enhanced_logger.py` [TRANSPORT]
**Transport calls in code:**
- L221 (`.get`): `price = float(level.get('price', 0))`
- L222 (`.get`): `size = float(level.get('size', 0))`
- L240 (`.get`): `prev_book_dict = self.prev_books[side].get('bids' if is_yes else 'asks', {})`
- L252 (`.get`): `old_size = prev_book_dict.get(price, 0)`
- L253 (`.get`): `new_size = new_book_dict.get(price, 0)`
- L324 (`.get`): `prev_book_dict = self.prev_books[token_side].get(book_side, {})`
- L332 (`.get`): `old_size = prev_book_dict.get(price, 0)`
- L333 (`.get`): `new_size = new_book_dict.get(price, 0)`

## `backtester/optimizer/dsr_validator.py` [TRANSPORT]
**Transport calls in code:**
- L118 (`.get`): `exclude_set = set(data.get('market_ids', []))`
- L159 (`.get`): `deposit = config.get('deposit', 300)`
- L160 (`.get`): `market_duration = config.get('market_duration_sec', 300.0)`
- L180 (`.get`): `pnl = result.pnl if hasattr(result, 'pnl') else result.get('pnl', 0)`
- L182 (`.get`): `costs.append(result.total_cost if hasattr(result, 'total_cost') else result.get('total_cost', 0))`
- L183 (`.get`): `fills_list.append(result.fills_count if hasattr(result, 'fills_count') else result.get('trades_count', 0))`
- L247 (`.get`): `for r in lhs_data.get('results', []):`
- L248 (`.get`): `sr = r.get('metrics', {}).get('sharpe', None)`

## `strategies/gabagool/order_pricer.py` [TRANSPORT]
**Transport calls in code:**
- L149 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L150 (`.get`): `bids = book.get('bids', [])`
- L157 (`.get`): `best = max(bids, key=lambda x: float(x.get('price', 0)))`
- L158 (`.get`): `return Decimal(str(best.get('price', 0)))`
- L167 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L168 (`.get`): `asks = book.get('asks', [])`
- L175 (`.get`): `best = min(asks, key=lambda x: float(x.get('price', 1)))`
- L176 (`.get`): `return Decimal(str(best.get('price', 1)))`

## `tbot_core/api/market_api.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L43 (`.get`): `async with session.get(url, timeout=10) as resp:`
- L48 (`.get`): `markets = data.get('markets', [])`
- L54 (`.get`): `token_ids_str = market.get('clobTokenIds', '[]')`
- L64 (`.get`): `'condition_id': market.get('conditionId'),`
- L68 (`.get`): `'question': market.get('question', ''),`
- L69 (`.get`): `'accepting_orders': market.get('acceptingOrders', False),`
- L70 (`.get`): `'closed': market.get('closed', True),`
- L73 (`.get`): `'resolved': market.get('umaResolutionStatus') == 'resolved'`

## `tbot_logger/enhanced_logger.py` [TRANSPORT]
**Transport calls in code:**
- L228 (`.get`): `p, s = float(level.get('price', 0)), float(level.get('size', 0))`
- L249 (`.get`): `prev_book_dict = self.prev_books[side].get('bids' if is_yes else 'asks', {})`
- L261 (`.get`): `old_size = prev_book_dict.get(price, 0)`
- L262 (`.get`): `new_size = new_book_dict.get(price, 0)`
- L333 (`.get`): `prev_book_dict = self.prev_books[token_side].get(book_side, {})`
- L341 (`.get`): `old_size = prev_book_dict.get(price, 0)`
- L342 (`.get`): `new_size = new_book_dict.get(price, 0)`
- L371 (`.get`): `if isinstance(lev, dict): return float(lev.get('price' if i==0 else 'size', 0))`

## `analysis/signals/alpha_signals.py` [PLATFORM]
**Transport calls in code:**
- L47 (`.get`): `}.get(self.severity, '⚪')`
- L161 (`.get`): `neutral = summary.by_regime.get('NEUTRAL')`
- L173 (`.get`): `ts = ctx.toxics_summary.get(bot_id)`
- L207 (`.get`): `torpedo = summary.by_regime.get('TORPEDO')`
- L461 (`.get`): `action = actions.get(sample_reason, f"Изучить причину {sample_reason} в _compute_healer.")`
- L549 (`.get`): `signals.sort(key=lambda s: severity_order.get(s.severity, 99))`
- L577 (`.get`): `counts[s.severity] = counts.get(s.severity, 0) + 1`

## `archive/dead_2026-03-04/tbot_simulator/engine.py` [PLATFORM]
**Transport calls in code:**
- L73 (`.get`): `host=config.get('db_host', 'localhost'),`
- L74 (`.get`): `port=config.get('db_port', 5432)`
- L198 (`.get`): `'is_maker': order.get('is_maker', True),`
- L215 (`.get`): `market_price = snapshot.get(f'{side}_best_ask')`
- L217 (`.get`): `market_price = snapshot.get(f'{side}_best_bid')`
- L295 (`.get`): `yes_price = snapshot.get('yes_best_bid', Decimal('0.5'))`
- L296 (`.get`): `no_price = snapshot.get('no_best_bid', Decimal('0.5'))`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/phase_manager.py` [PLATFORM]
**Transport calls in code:**
- L206 (`.get`): `yes_book = orderbook.get('yes_book', orderbook.get('yes', {}))`
- L207 (`.get`): `no_book = orderbook.get('no_book', orderbook.get('no', {}))`
- L220 (`.get`): `bids = book.get('bids', [])`
- L221 (`.get`): `asks = book.get('asks', [])`
- L231 (`.get`): `best_bid = max(Decimal(str(b.get('price', 0))) for b in bids)`
- L232 (`.get`): `best_ask = min(Decimal(str(a.get('price', 1))) for a in asks)`
- L245 (`.get`): `yes_book = orderbook.get('yes_book', orderbook.get('yes', {}))`

## `archive/hesoyam_with_fill_rate_limits/tbot_simulator/engine.py` [PLATFORM]
**Transport calls in code:**
- L73 (`.get`): `host=config.get('db_host', 'localhost'),`
- L74 (`.get`): `port=config.get('db_port', 5432)`
- L198 (`.get`): `'is_maker': order.get('is_maker', True),`
- L215 (`.get`): `market_price = snapshot.get(f'{side}_best_ask')`
- L217 (`.get`): `market_price = snapshot.get(f'{side}_best_bid')`
- L295 (`.get`): `yes_price = snapshot.get('yes_best_bid', Decimal('0.5'))`
- L296 (`.get`): `no_price = snapshot.get('no_best_bid', Decimal('0.5'))`

## `scripts/Сканнеры SDK/check_market_precision.py` [TRANSPORT]
**External imports:** requests

**Transport calls in code:**
- L11 (`.get`): `resp = requests.get(url)`
- L24 (`.get`): `print(f"  - Title: {market.get('question')}")`
- L25 (`.get`): `print(f"  - Tick Size: {market.get('tick_size')}") # <--- ВОТ ТВОЙ ОТВЕТ`
- L26 (`.get`): `print(f"  - Min Order: {market.get('minimum_order_size')}")`
- L27 (`.get`): `print(f"  - Neg Risk: {market.get('neg_risk')}")`
- L28 (`.get`): `print(f"  - Active: {market.get('active')}")`
- L31 (`.get`): `tokens = market.get('clobTokenIds', [])`

## `scripts/Сканнеры SDK/get_truth.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L17 (`.get`): `m_data = requests.get(gamma_url).json()`
- L23 (`.get`): `token_id = m_data[0].get('clobTokenIds', [])[0]`
- L28 (`.get`): `resp = requests.get(clob_url)`
- L33 (`.get`): `print(f"    - ТЕКУЩИЙ TICK SIZE: {clob_data.get('tick_size')}") # <--- ВОТ ТВОЯ ЦИФРА`
- L34 (`.get`): `print(f"    - МИН. ОБЪЕМ: {clob_data.get('minimum_order_size')}")`
- L39 (`.get`): `book = requests.get(book_url).json()`
- L41 (`.get`): `actual_tick = book.get('tick_size', 'Не указан')`

## `strategies/gabagool/phase_manager.py` [PLATFORM]
**Transport calls in code:**
- L206 (`.get`): `yes_book = orderbook.get('yes_book', orderbook.get('yes', {}))`
- L207 (`.get`): `no_book = orderbook.get('no_book', orderbook.get('no', {}))`
- L220 (`.get`): `bids = book.get('bids', [])`
- L221 (`.get`): `asks = book.get('asks', [])`
- L231 (`.get`): `best_bid = max(Decimal(str(b.get('price', 0))) for b in bids)`
- L232 (`.get`): `best_ask = min(Decimal(str(a.get('price', 1))) for a in asks)`
- L245 (`.get`): `yes_book = orderbook.get('yes_book', orderbook.get('yes', {}))`

## `tbot_integration/strike_fetcher.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L35 (`.get`): `async with session.get(url, timeout=3) as resp:`
- L64 (`.get`): `async with session.get(STRIKE_API_URL, params=params, timeout=5) as resp:`
- L68 (`.get`): `if data.get("completed") and data.get("closePrice"):`
- L69 (`.get`): `return round(float(data.get("closePrice")), 2)`
- L88 (`.get`): `cached = self._cache.get(slug)`
- L93 (`.get`): `if cached.get('verified'):`
- L106 (`.get`): `return self._cache.get(slug, {}).get('strike')`

## `analysis/views/toxic_view.py` [TRANSPORT]
**Transport calls in code:**
- L35 (`.get`): `ts = toxics_summary.get(bot_id)`
- L50 (`.get`): `ts = toxics_summary.get(bot_id)`
- L66 (`.get`): `ts = toxics_summary.get(bot_id)`
- L89 (`.get`): `ts = toxics_summary.get(bot_id)`
- L102 (`.get`): `ages = cell_ages.get((intent, regime), [])`
- L103 (`.get`): `drifts = cell_drifts.get((intent, regime), [])`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/manager.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L40 (`.get`): `self.api_key = config.get('api_key')`
- L81 (`.post`): `async with self.session.post('/orders', json=payload) as resp:`
- L91 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L175 (`.get`): `async with self.session.get(f'/orders/{order_id}') as resp:`
- L185 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L237 (`.get`): `client_order_id=data.get('clientOrderId'),`

## `archive/dead_2026-03-04/tbot_core_execution/manager.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L40 (`.get`): `self.api_key = config.get('api_key')`
- L81 (`.post`): `async with self.session.post('/orders', json=payload) as resp:`
- L91 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L175 (`.get`): `async with self.session.get(f'/orders/{order_id}') as resp:`
- L185 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L237 (`.get`): `client_order_id=data.get('clientOrderId'),`

## `archive/dead_2026-03-04/tbot_visualizer/server.py` [TRANSPORT]
**Transport calls in code:**
- L21 (`.get`): `@app.get("/", response_class=HTMLResponse)`
- L25 (`.get`): `@app.get("/api/simulations")`
- L36 (`.get`): `"market": sim_data.get("market"),`
- L37 (`.get`): `"timestamp": sim_data.get("timestamp"),`
- L38 (`.get`): `"final_pnl": sim_data.get("metrics", {}).get("final_pnl")`
- L44 (`.get`): `@app.get("/api/simulation/{sim_id}")`

## `archive/dead_2026-03-04/test_api_methods.py` [PLATFORM]
**Transport calls in code:**
- L29 (`.get`): `btc_markets = [m for m in markets if 'btc' in m.get('question', '').lower()]`
- L33 (`.get`): `print(f"   Example: {btc_markets[0].get('question', 'N/A')[:60]}")`
- L36 (`.get`): `if btc_markets and btc_markets[0].get('tokens'):`
- L55 (`.get`): `print(f"   Allowance: ${float(usdc.get('allowance', 0)):.2f}")`
- L67 (`.get`): `print(f"   Order {order_id[:16]}... — {order.get('status', 'N/A')}")`
- L86 (`.get`): `if btc_markets and btc_markets[0].get('tokens'):`

## `archive/dead_2026-03-04/test_live_order_v2.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L23 (`.get`): `markets = requests.get(url, params=params).json()`
- L28 (`.get`): `btc_markets = [m for m in markets if 'btc' in m.get('question', '').lower()]`
- L39 (`.get`): `print(f'Закрытие: {market.get("endDateIso", "N/A")}\n')`
- L42 (`.get`): `tokens = market.get('clobTokenIds', '').split(',') if market.get('clobTokenIds') else []`
- L75 (`.get`): `print(f'   Status: {order.get("status", "unknown")}')`
- L83 (`.get`): `print(f'✅ ОТМЕНЁН! Final: {order_final.get("status", "unknown")}')`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/execution_engine.py` [TRANSPORT]
**Transport calls in code:**
- L622 (`.get`): `book = orderbook.get(leg_key, {})`
- L623 (`.get`): `bids = book.get('bids', [])`
- L630 (`.get`): `prices = [float(b.get('price', 0)) for b in bids]`
- L642 (`.get`): `return self.PHASE_TIMEOUTS.get(phase, 15.0)`
- L682 (`.get`): `'smart_holds': smart.get('holds', 0),`
- L683 (`.get`): `'smart_replaces': smart.get('replaces', 0),`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/rebalancer.py` [PLATFORM]
**Transport calls in code:**
- L233 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L234 (`.get`): `asks = book.get('asks', [])`
- L241 (`.get`): `prices = [float(a.get('price', 1)) for a in asks]`
- L250 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L251 (`.get`): `bids = book.get('bids', [])`
- L258 (`.get`): `prices = [float(b.get('price', 0)) for b in bids]`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/manager.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L40 (`.get`): `self.api_key = config.get('api_key')`
- L81 (`.post`): `async with self.session.post('/orders', json=payload) as resp:`
- L91 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L175 (`.get`): `async with self.session.get(f'/orders/{order_id}') as resp:`
- L185 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L237 (`.get`): `client_order_id=data.get('clientOrderId'),`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/manager.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L40 (`.get`): `self.api_key = config.get('api_key')`
- L81 (`.post`): `async with self.session.post('/orders', json=payload) as resp:`
- L91 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L175 (`.get`): `async with self.session.get(f'/orders/{order_id}') as resp:`
- L185 (`.get`): `client_order_id=data.get('clientOrderId'),`
- L237 (`.get`): `client_order_id=data.get('clientOrderId'),`

## `archive/hesoyam_with_fill_rate_limits/tbot_visualizer/server.py` [TRANSPORT]
**Transport calls in code:**
- L21 (`.get`): `@app.get("/", response_class=HTMLResponse)`
- L25 (`.get`): `@app.get("/api/simulations")`
- L36 (`.get`): `"market": sim_data.get("market"),`
- L37 (`.get`): `"timestamp": sim_data.get("timestamp"),`
- L38 (`.get`): `"final_pnl": sim_data.get("metrics", {}).get("final_pnl")`
- L44 (`.get`): `@app.get("/api/simulation/{sim_id}")`

## `archive/mag_quarantine/lorine93s-analysis/src/polymarket/order_signer.py` [TRANSPORT]
**Transport calls in code:**
- L30 (`.get`): `str(order.get("market", "")),`
- L31 (`.get`): `str(order.get("side", "")),`
- L32 (`.get`): `str(order.get("size", "")),`
- L33 (`.get`): `str(order.get("price", "")),`
- L34 (`.get`): `str(order.get("time", "")),`
- L35 (`.get`): `str(order.get("salt", "")),`

## `backtester/optimizer/deposit_scaler.py` [TRANSPORT]
**Transport calls in code:**
- L60 (`.get`): `original_lot = base_config.get('lot_size', 12)`
- L65 (`.get`): `lot_cap = LOT_CAPS.get(to_bankroll, 60)`
- L121 (`.get`): `if not data.get('top_configs'):`
- L128 (`.get`): `base_deposit = data.get('metadata', {}).get('deposit', 100)`
- L137 (`.get`): `lot = all_tiers[br].get('lot_size', '?')`
- L138 (`.get`): `pricing = all_tiers[br].get('pricing_mode', '?')`

## `scripts/math_playground.py` [TRANSPORT]
**Transport calls in code:**
- L16 (`.get`): `deposit = float(cfg.get('deposit', 150.0))`
- L17 (`.get`): `base_lot = int(cfg.get('grid_lot_size', 5))`
- L18 (`.get`): `edge = float(cfg.get('target_edge', 0.015))`
- L20 (`.get`): `max_skew = float(cfg.get('max_penalty_dev', 0.25))`
- L22 (`.get`): `usd_limit = deposit * float(cfg.get('side_usd_limit_pct', 0.60))`
- L23 (`.get`): `asym_mult = float(cfg.get('spacing_asym_multiplier', 2.5))`

## `strategies/gabagool/execution_engine.py` [TRANSPORT]
**Transport calls in code:**
- L622 (`.get`): `book = orderbook.get(leg_key, {})`
- L623 (`.get`): `bids = book.get('bids', [])`
- L630 (`.get`): `prices = [float(b.get('price', 0)) for b in bids]`
- L642 (`.get`): `return self.PHASE_TIMEOUTS.get(phase, 15.0)`
- L682 (`.get`): `'smart_holds': smart.get('holds', 0),`
- L683 (`.get`): `'smart_replaces': smart.get('replaces', 0),`

## `strategies/gabagool/rebalancer.py` [PLATFORM]
**Transport calls in code:**
- L233 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L234 (`.get`): `asks = book.get('asks', [])`
- L241 (`.get`): `prices = [float(a.get('price', 1)) for a in asks]`
- L250 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L251 (`.get`): `bids = book.get('bids', [])`
- L258 (`.get`): `prices = [float(b.get('price', 0)) for b in bids]`

## `analysis/views/pair_state_view.py` [TRANSPORT]
**Transport calls in code:**
- L38 (`.get`): `ps = pair_state_summary.get(bot_id)`
- L41 (`.get`): `bal_pct = ps.state_distribution.get('BALANCED', 0) * 100`
- L42 (`.get`): `fresh_pct = ps.state_distribution.get('FRESH', 0) * 100`
- L43 (`.get`): `stuck_pct = ps.state_distribution.get('STUCK', 0) * 100`
- L61 (`.get`): `ps = pair_state_summary.get(bot_id)`

## `archive/hesoyam_with_fill_rate_limits/main.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L46 (`.post`): `async with session.post(url, json={`
- L86 (`.get`): `client = PolymarketClient(config.get('polymarket', {}))`
- L90 (`.get`): `market_tag = config.get('market_tag', 'btc-15m')`
- L98 (`.get`): `market_slug = market.get('slug')`
- L107 (`.get`): `time_to_expiry = config.get('market_duration_sec', 900)`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/fillrate_logger.py` [PLATFORM]
**Transport calls in code:**
- L104 (`.get`): `book = orderbook.get(leg_lower, orderbook.get(f'{leg_lower}_book', {}))`
- L105 (`.get`): `bids = book.get('bids', [])`
- L106 (`.get`): `asks = book.get('asks', [])`
- L116 (`.get`): `bid_prices = [(float(b['price']), float(b.get('size', 0))) for b in bids]`
- L124 (`.get`): `ask_prices = [(float(a['price']), float(a.get('size', 0))) for a in asks]`

## `archive/mag_knowledge/legacy/Well start here/poly_claim/bulk_redeem.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L32 (`.get`): `async with session.get(url) as resp:`
- L96 (`.get`): `cond_id = pos.get('conditionId')`
- L97 (`.get`): `title = pos.get('title', 'Unknown Market')`
- L123 (`.get`): `elif isinstance(result, dict) and result.get('transactionHash'):`
- L124 (`.get`): `print(f"   УСПЕХ! TX Hash: https://polygonscan.com/tx/{result.get('transactionHash')}")`

## `archive/mag_quarantine/lorine93s-analysis/src/polymarket/rest_client.py` [TRANSPORT]
**Transport calls in code:**
- L22 (`.get`): `response = await self.client.get(f"{self.base_url}/markets", params=params)`
- L31 (`.get`): `response = await self.client.get(f"{self.base_url}/book", params={"market": market_id})`
- L40 (`.get`): `response = await self.client.get(f"{self.base_url}/markets/{market_id}")`
- L49 (`.get`): `response = await self.client.get(f"{self.base_url}/balances", params={"user": address})`
- L61 (`.get`): `response = await self.client.get(f"{self.base_url}/open-orders", params=params)`

## `backtester/optimizer/param_space_v6.py` [TRANSPORT]
**Transport calls in code:**
- L289 (`.get`): `return {k: v for k, v in PARAM_SPACE_V6.items() if v.get('optimize', True)}`
- L294 (`.get`): `return {k: v['values'][0] for k, v in PARAM_SPACE_V6.items() if not v.get('optimize', True)}`
- L301 (`.get`): `if v.get('optimize', True):`
- L343 (`.get`): `opt = sum(1 for v in PARAM_SPACE_V6.values() if v.get('optimize', True))`
- L344 (`.get`): `frozen = sum(1 for v in PARAM_SPACE_V6.values() if not v.get('optimize', True))`

## `backtester/optimizer/profiles.py` [PLATFORM]
**Transport calls in code:**
- L420 (`.get`): `return sum(1 for spec in applied.values() if len(spec.get('values', [])) > 1)`
- L425 (`.get`): `return sum(1 for spec in applied.values() if len(spec.get('values', [])) == 1)`
- L432 (`.get`): `vals = spec.get('values', [])`
- L467 (`.get`): `opt_names = [k for k, v in applied.items() if len(v.get('values', [])) > 1]`
- L472 (`.get`): `if len(v.get('values', [])) == 1}`

## `dashboard/microstructure/kde_renderer.py` [TRANSPORT]
**Transport calls in code:**
- L92 (`.get`): `market_id_short = meta.get('market_id', 'unknown')`
- L95 (`.get`): `timestamp = meta.get('timestamp', '')`
- L108 (`.get`): `ax.set_title(METRIC_TITLES.get(metric_name, metric_name),`
- L117 (`.get`): `metric_data = metrics.get(metric_name, {})`
- L121 (`.get`): `data = metric_data.get(window_name)`

## `generate_fleet.py` [TRANSPORT]
**Transport calls in code:**
- L150 (`.get`): `anchor_bot     = hyp.get("anchor_bot")`
- L151 (`.get`): `anchor_variant = hyp.get("anchor_variant", "a")`
- L158 (`.get`): `anchor_bot     = hyp.get("anchor_bot")`
- L159 (`.get`): `anchor_variant = hyp.get("anchor_variant", "a")`
- L251 (`.get`): `print(f"   Основных ботов:   {len([h for h in hypotheses if h.get('anchor_bot')])}")`

## `oracle_daemon.py` [TRANSPORT]
**External imports:** zmq.asyncio

**Transport calls in code:**
- L3 (`zmq`): `import zmq.asyncio`
- L14 (`zmq`): `ctx = zmq.asyncio.Context()`
- L15 (`zmq`): `pub = ctx.socket(zmq.PUB)`
- L15 (`PUB`): `pub = ctx.socket(zmq.PUB)`
- L46 (`PUB`): `logger.error(f"PUB Error: {e}")`

## `scripts/Сканнеры SDK/check_token.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L13 (`.get`): `resp = requests.get(url)`
- L20 (`.get`): `bids = data.get('bids', [])`
- L21 (`.get`): `asks = data.get('asks', [])`
- L29 (`.get`): `price = level.get('price')`
- L37 (`.get`): `price = level.get('price')`

## `strategies/gabagool/fillrate_logger.py` [PLATFORM]
**Transport calls in code:**
- L104 (`.get`): `book = orderbook.get(leg_lower, orderbook.get(f'{leg_lower}_book', {}))`
- L105 (`.get`): `bids = book.get('bids', [])`
- L106 (`.get`): `asks = book.get('asks', [])`
- L116 (`.get`): `bid_prices = [(float(b['price']), float(b.get('size', 0))) for b in bids]`
- L124 (`.get`): `ask_prices = [(float(a['price']), float(a.get('size', 0))) for a in asks]`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/position_tracker.py` [PLATFORM]
**Transport calls in code:**
- L140 (`.get`): `max_exposure = Decimal(str(config.get('max_total_exposure', '10000')))`
- L146 (`.get`): `max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss', '1000')))`
- L152 (`.get`): `max_position_size = Decimal(str(config.get('max_position_size', '1000')))`
- L159 (`.get`): `max_imbalance = Decimal(str(config.get('max_imbalance', '100')))`

## `archive/dead_2026-03-04/tbot_core_execution/position_tracker.py` [PLATFORM]
**Transport calls in code:**
- L140 (`.get`): `max_exposure = Decimal(str(config.get('max_total_exposure', '10000')))`
- L146 (`.get`): `max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss', '1000')))`
- L152 (`.get`): `max_position_size = Decimal(str(config.get('max_position_size', '1000')))`
- L159 (`.get`): `max_imbalance = Decimal(str(config.get('max_imbalance', '100')))`

## `archive/dead_2026-03-04/test_order_fresh.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L34 (`.get`): `market = requests.get(f'https://gamma-api.polymarket.com/markets/slug/{slug}', timeout=3).json()`
- L36 (`.get`): `if market.get('closed'):`
- L40 (`.get`): `token_ids = market.get('clobTokenIds', '').strip('[]"').split('","')`
- L85 (`.get`): `print(f'   Status: {order.get("status", "?")}')`

## `archive/dead_2026-03-04/test_order_simple.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L32 (`.get`): `slug = state.get('market_slug')`
- L42 (`.get`): `market = requests.get(f'https://gamma-api.polymarket.com/markets/slug/{slug}').json()`
- L43 (`.get`): `token_ids = market.get('clobTokenIds', '').strip('[]"').split('","')`
- L85 (`.get`): `print(f'   Status: {order.get("status", "?")}')`

## `archive/hesoyam_with_fill_rate_limits/backtester/bridge/paper_bridge.py` [TRANSPORT]
**Transport calls in code:**
- L39 (`.get`): `return data.get('best_params', DEFAULT_PARAMS)`
- L75 (`.get`): `queue_discount = params.get('queue_discount', 0.85)`
- L121 (`.get`): `f"qd={params.get('queue_discount', '?')} "`
- L122 (`.get`): `f"lat={params.get('latency_penalty_ms', '?')}ms")`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/lot_sizer.py` [PLATFORM]
**Transport calls in code:**
- L153 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L155 (`.get`): `bids = book.get('bids', [])`
- L156 (`.get`): `asks = book.get('asks', [])`
- L171 (`.get`): `size = float(level.get('size', 0))`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/position_tracker.py` [PLATFORM]
**Transport calls in code:**
- L140 (`.get`): `max_exposure = Decimal(str(config.get('max_total_exposure', '10000')))`
- L146 (`.get`): `max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss', '1000')))`
- L152 (`.get`): `max_position_size = Decimal(str(config.get('max_position_size', '1000')))`
- L159 (`.get`): `max_imbalance = Decimal(str(config.get('max_imbalance', '100')))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/position_tracker.py` [PLATFORM]
**Transport calls in code:**
- L140 (`.get`): `max_exposure = Decimal(str(config.get('max_total_exposure', '10000')))`
- L146 (`.get`): `max_worst_case_loss = Decimal(str(config.get('max_worst_case_loss', '1000')))`
- L152 (`.get`): `max_position_size = Decimal(str(config.get('max_position_size', '1000')))`
- L159 (`.get`): `max_imbalance = Decimal(str(config.get('max_imbalance', '100')))`

## `archive/mag_quarantine/lorine93s-analysis/src/execution/order_executor.py` [TRANSPORT]
**Transport calls in code:**
- L33 (`.post`): `response = await self.client.post(`
- L41 (`.get`): `logger.info("order_placed", order_id=result.get("id"), side=order.get("side"), price=order.get("price"))`
- L73 (`.get`): `cancelled = response.json().get("cancelled", 0)`
- L90 (`.post`): `response = await self.client.post(`

## `archive/mag_quarantine/lorine93s-analysis/src/services/auto_redeem.py` [TRANSPORT]
**Transport calls in code:**
- L20 (`.get`): `response = await self.client.get(`
- L32 (`.post`): `response = await self.client.post(`
- L50 (`.get`): `value_usd = float(position.get("value", 0))`
- L52 (`.get`): `if await self.redeem_position(position.get("id")):`

## `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_full_flow.py` [PLATFORM]
**Transport calls in code:**
- L115 (`.get`): `if rfq_request_response.get("error"):`
- L119 (`.get`): `request_id = rfq_request_response.get("requestId")`
- L148 (`.get`): `if rfq_quote_response.get("error"):`
- L152 (`.get`): `quote_id = rfq_quote_response.get("quoteId")`

## `backtester/bridge/paper_bridge.py` [TRANSPORT]
**Transport calls in code:**
- L39 (`.get`): `return data.get('best_params', DEFAULT_PARAMS)`
- L75 (`.get`): `queue_discount = params.get('queue_discount', 0.85)`
- L121 (`.get`): `f"qd={params.get('queue_discount', '?')} "`
- L122 (`.get`): `f"lat={params.get('latency_penalty_ms', '?')}ms")`

## `backtester/core/engine_v6.py` [PLATFORM]
**Transport calls in code:**
- L22 (`.get`): `_SUPPRESS_TOXIC = bool(os.environ.get('SUPPRESS_TOXIC_LOG'))`
- L124 (`.get`): `if not _SUPPRESS_TOXIC and not os.environ.get('SUPPRESS_TOXIC_LOG'):`
- L158 (`.get`): `if metrics.get('as_delta_count', 0) > 0:`
- L161 (`.get`): `if metrics.get('vpin_count', 0) > 0:`

## `fleet_results.py` [TRANSPORT]
**Transport calls in code:**
- L213 (`.get`): `anchor_bot  = ANCHORS.get(hyp_name)`
- L214 (`.get`): `anchor_data = all_data.get(anchor_bot)`
- L220 (`.get`): `anchor_data = all_data.get(a_bot)`
- L241 (`.get`): `data  = all_data.get(bot_name)`

## `scripts/ldm_analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L43 (`.get`): `if data.get("event") == "fill":`
- L44 (`.get`): `target = data.get("target_price", 0)`
- L45 (`.get`): `fill = data.get("fill_price", 0)`
- L52 (`.get`): `if "429" in str(data.get("error", "")):`

## `strategies/gabagool/grid_manager.py` [PLATFORM]
**Transport calls in code:**
- L300 (`.get`): `for tlvl in side_targets.get(pending.side, []):`
- L358 (`.get`): `last_fill = self._last_fill_time.get(tlvl.side, 0.0)`
- L376 (`.get`): `pending = self.pending_orders.get(oid)`
- L401 (`.get`): `pending = self.pending_orders.get(order_id)`

## `strategies/gabagool/lot_sizer.py` [PLATFORM]
**Transport calls in code:**
- L153 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L155 (`.get`): `bids = book.get('bids', [])`
- L156 (`.get`): `asks = book.get('asks', [])`
- L171 (`.get`): `size = float(level.get('size', 0))`

## `analysis/views/edge_view.py` [TRANSPORT]
**Transport calls in code:**
- L37 (`.get`): `data = bots_data.get(bot_id)`
- L58 (`.get`): `data = bots_data.get(bot_id)`
- L90 (`.get`): `data = bots_data.get(bot_id)`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/main.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L46 (`.post`): `async with session.post(url, json={`
- L86 (`.get`): `client = PolymarketClient(config.get('polymarket', {}))`
- L97 (`.get`): `market_slug = market.get('slug')`

## `archive/dead_2026-03-04/live_test_buy_both.py` [PLATFORM]
**Transport calls in code:**
- L48 (`.get`): `slug = state.get('market_slug', '')`
- L49 (`.get`): `time_left = state.get('time_left_sec', 0)`
- L137 (`.get`): `print(f"  {o.get('side','')} {o.get('original_size','')}@{o.get('price','')} status={o.get('status','')}")`

## `archive/dead_2026-03-04/test_single_order.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L21 (`.get`): `gamma = requests.get('https://gamma-api.polymarket.com/markets?active=true&limit=100').json()`
- L25 (`.get`): `if 'btc' in m.get('question', '').lower() and m.get('end_date_iso'):`
- L79 (`.get`): `print(f"   Status: {order.get('status', 'unknown')}")`

## `archive/hesoyam_with_fill_rate_limits/scripts/live_test_buy_both.py` [PLATFORM]
**Transport calls in code:**
- L48 (`.get`): `slug = state.get('market_slug', '')`
- L49 (`.get`): `time_left = state.get('time_left_sec', 0)`
- L137 (`.get`): `print(f"  {o.get('side','')} {o.get('original_size','')}@{o.get('price','')} status={o.get('status','')}")`

## `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/linked_orders.py` [TRANSPORT]
**Transport calls in code:**
- L132 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L133 (`.get`): `asks = book.get('asks', [])`
- L140 (`.get`): `prices = [float(a.get('price', 999)) for a in asks]`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/main.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L46 (`.post`): `async with session.post(url, json={`
- L86 (`.get`): `client = PolymarketClient(config.get('polymarket', {}))`
- L97 (`.get`): `market_slug = market.get('slug')`

## `backtester/core/engine.py` [PLATFORM]
**Transport calls in code:**
- L135 (`.get`): `if metrics.get('as_bid_adjustments', 0) > 0:`
- L140 (`.get`): `if metrics.get('vpin_skips', 0) > 0:`
- L142 (`.get`): `metrics.get('vpin_skip_sum', 0) / metrics['vpin_skips'], 4)`

## `backtester/strategy/grid_strategy_sim.py` [PLATFORM]
**Transport calls in code:**
- L275 (`.get`): `vpin_val = self.vpin.get()`
- L444 (`.get`): `size = trade.get('size', 0)`
- L445 (`.get`): `side = trade.get('side', 'buy')`

## `strategies/gabagool/linked_orders.py` [TRANSPORT]
**Transport calls in code:**
- L132 (`.get`): `book = orderbook.get(f'{leg_lower}_book', orderbook.get(leg_lower, {}))`
- L133 (`.get`): `asks = book.get('asks', [])`
- L140 (`.get`): `prices = [float(a.get('price', 999)) for a in asks]`

## `analysis/views/regime_view.py` [TRANSPORT]
**Transport calls in code:**
- L40 (`.get`): `summary = epochs_summary.get(bot_id)`
- L92 (`.get`): `epochs = epochs_by_bot.get(bot_id, [])`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/fills_handler.py` [TRANSPORT]
**Transport calls in code:**
- L32 (`.get`): `self.maker_fee_bps = Decimal(str(config.get('maker_fee_bps', 0)))`
- L33 (`.get`): `self.taker_fee_bps = Decimal(str(config.get('taker_fee_bps', 20)))`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/market/state.py` [TRANSPORT]
**Transport calls in code:**
- L54 (`.get`): `for p, s in book_data.get('bids', [])`
- L58 (`.get`): `for p, s in book_data.get('asks', [])`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/liquidity.py` [TRANSPORT]
**Transport calls in code:**
- L31 (`.get`): `levels = orderbook.get('asks' if side == 'BUY' else 'bids', [])`
- L78 (`.get`): `levels = orderbook.get('asks', [])  # Using asks for BUY side`

## `archive/dead_2026-03-04/liquidity.py` [TRANSPORT]
**Transport calls in code:**
- L31 (`.get`): `levels = orderbook.get('asks' if side == 'BUY' else 'bids', [])`
- L78 (`.get`): `levels = orderbook.get('asks', [])  # Using asks for BUY side`

## `archive/dead_2026-03-04/tbot_core_execution/fills_handler.py` [TRANSPORT]
**Transport calls in code:**
- L32 (`.get`): `self.maker_fee_bps = Decimal(str(config.get('maker_fee_bps', 0)))`
- L33 (`.get`): `self.taker_fee_bps = Decimal(str(config.get('taker_fee_bps', 20)))`

## `archive/dead_2026-03-04/tbot_core_market/state.py` [TRANSPORT]
**Transport calls in code:**
- L54 (`.get`): `for p, s in book_data.get('bids', [])`
- L58 (`.get`): `for p, s in book_data.get('asks', [])`

## `archive/hesoyam_with_fill_rate_limits/backtester/calibration/calibrator.py` [TRANSPORT]
**Transport calls in code:**
- L65 (`.get`): `fill_rates = [r.metrics.get('fill_rate', 0) for r in market_results]`
- L121 (`.get`): `return data.get('best_params', {})`

## `archive/hesoyam_with_fill_rate_limits/backtester/core/orderbook_replay.py` [TRANSPORT]
**Transport calls in code:**
- L115 (`.get`): `'price': float(lvl.get('price', 0)),`
- L116 (`.get`): `'size': float(lvl.get('size', 0)),`

## `archive/hesoyam_with_fill_rate_limits/backtester/core/trade_flow.py` [TRANSPORT]
**Transport calls in code:**
- L85 (`.get`): `if abs(level.get('price', 0) - price) < 0.005:`
- L86 (`.get`): `return float(level.get('size', 0))`

## `archive/hesoyam_with_fill_rate_limits/backtester/models/queue_aware.py` [TRANSPORT]
**Transport calls in code:**
- L139 (`.get`): `if abs(level.get('price', 0) - order.price) < 0.005:`
- L140 (`.get`): `level_size = float(level.get('size', 0))`

## `archive/hesoyam_with_fill_rate_limits/backtester/reporting/report.py` [TRANSPORT]
**Transport calls in code:**
- L151 (`.get`): `vals = [r.metrics.get(key, 0) for r in results]`
- L157 (`.get`): `vals = [r.metrics.get(key, 0) for r in results if r.metrics.get(key, 0) > 0]`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/fills_handler.py` [TRANSPORT]
**Transport calls in code:**
- L32 (`.get`): `self.maker_fee_bps = Decimal(str(config.get('maker_fee_bps', 0)))`
- L33 (`.get`): `self.taker_fee_bps = Decimal(str(config.get('taker_fee_bps', 20)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/market/state.py` [TRANSPORT]
**Transport calls in code:**
- L54 (`.get`): `for p, s in book_data.get('bids', [])`
- L58 (`.get`): `for p, s in book_data.get('asks', [])`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/liquidity.py` [TRANSPORT]
**Transport calls in code:**
- L31 (`.get`): `levels = orderbook.get('asks' if side == 'BUY' else 'bids', [])`
- L78 (`.get`): `levels = orderbook.get('asks', [])  # Using asks for BUY side`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/fills_handler.py` [TRANSPORT]
**Transport calls in code:**
- L32 (`.get`): `self.maker_fee_bps = Decimal(str(config.get('maker_fee_bps', 0)))`
- L33 (`.get`): `self.taker_fee_bps = Decimal(str(config.get('taker_fee_bps', 20)))`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/market/state.py` [TRANSPORT]
**Transport calls in code:**
- L54 (`.get`): `for p, s in book_data.get('bids', [])`
- L58 (`.get`): `for p, s in book_data.get('asks', [])`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/liquidity.py` [TRANSPORT]
**Transport calls in code:**
- L31 (`.get`): `levels = orderbook.get('asks' if side == 'BUY' else 'bids', [])`
- L78 (`.get`): `levels = orderbook.get('asks', [])  # Using asks for BUY side`

## `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/config.py` [TRANSPORT]
**Transport calls in code:**
- L36 (`.get`): `config = NEG_RISK_CONFIG.get(chainID)`
- L38 (`.get`): `config = CONFIG.get(chainID)`

## `backtester/calibration/calibrator.py` [TRANSPORT]
**Transport calls in code:**
- L65 (`.get`): `fill_rates = [r.metrics.get('fill_rate', 0) for r in market_results]`
- L121 (`.get`): `return data.get('best_params', {})`

## `backtester/core/orderbook_replay.py` [TRANSPORT]
**Transport calls in code:**
- L115 (`.get`): `'price': float(lvl.get('price', 0)),`
- L116 (`.get`): `'size': float(lvl.get('size', 0)),`

## `backtester/core/trade_flow.py` [TRANSPORT]
**Transport calls in code:**
- L85 (`.get`): `if abs(level.get('price', 0) - price) < 0.005:`
- L86 (`.get`): `return float(level.get('size', 0))`

## `backtester/models/queue_aware.py` [TRANSPORT]
**Transport calls in code:**
- L164 (`.get`): `if abs(level.get('price', 0) - order.price) < 0.005:`
- L165 (`.get`): `level_size = float(level.get('size', 0))`

## `backtester/optimizer/profiles_v6_calibrated.py` [PLATFORM]
**Transport calls in code:**
- L519 (`.get`): `n_opt = sum(1 for v in mod.values() if v.get('optimize', True) and len(v['values']) > 1)`
- L522 (`.get`): `if v.get('optimize', True) and len(v['values']) > 1:`

## `backtester/reporting/report.py` [TRANSPORT]
**Transport calls in code:**
- L151 (`.get`): `vals = [r.metrics.get(key, 0) for r in results]`
- L157 (`.get`): `vals = [r.metrics.get(key, 0) for r in results if r.metrics.get(key, 0) > 0]`

## `claim_probe.py` [TRANSPORT]
**External imports:** requests

**Transport calls in code:**
- L48 (`.get`): `relayer_nonce = n_resp.get("nonce")`
- L78 (`.post`): `resp = requests.post(f"{client.relayer_url}/submit",`

## `merge_probe.py` [TRANSPORT]
**External imports:** requests

**Transport calls in code:**
- L52 (`.get`): `relayer_nonce = n_resp.get("nonce")`
- L98 (`.post`): `resp = requests.post("https://relayer-v2.polymarket.com/submit", headers=headers, data=body_str, timeout=15)`

## `scripts/merge_probe.py` [PLATFORM]
**External imports:** requests

**Transport calls in code:**
- L38 (`.get`): `nonce = str(requests.get(n_url, timeout=5).json().get("nonce", "0"))`
- L83 (`.post`): `resp = requests.post("https://relayer-v2.polymarket.com/submit", headers=headers, data=body_str, timeout=15)`

## `scripts/Сканнеры SDK/autopsy_engine_v2.py` [TRANSPORT]
**Transport calls in code:**
- L65 (`.get`): `print(f"   Maker в подписи: {signed_order.get('maker')}")`
- L66 (`.get`): `print(f"   Signature: {signed_order.get('signature')[:40]}...")`

## `strategies/gabagool/oracle_engine.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L296 (`.get`): `best_bid = float(data.get('b', 0))`
- L297 (`.get`): `best_ask = float(data.get('a', 0))`

## `strategies/gabagool/vpin.py` [TRANSPORT]
**Transport calls in code:**
- L32 (`.get`): `current = vpin.get()   # 0.0 - 1.0`
- L100 (`.get`): `return self.get() > self.threshold`

## `analysis/views/quoting_health.py` [TRANSPORT]
**Transport calls in code:**
- L54 (`.get`): `data = bots_data.get(bot_id)`

## `api_xray.py` [PLATFORM]
**External imports:** aiohttp

**Transport calls in code:**
- L14 (`.get`): `async with session.get(url, params=params, timeout=10) as resp:`

## `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/simple_strat2.py` [TRANSPORT]
**Transport calls in code:**
- L154 (`.get`): `order = self.active_orders.get(order_id)`

## `archive/dead_2026-03-04/lhs_screening_patch.py` [TRANSPORT]
**Transport calls in code:**
- L40 (`.get`): `{indent}        imp = rf_imp.get(param, 0.0) if 'rf_imp' in dir() else 0.0`

## `archive/dead_2026-03-04/polymarket/position_sync.py` [PLATFORM]
**Transport calls in code:**
- L281 (`.get`): `remote_list = remote_by_condition.get(condition_id, [])`

## `archive/dead_2026-03-04/tbot_simulator/metrics.py` [TRANSPORT]
**Transport calls in code:**
- L265 (`.get`): `maker_trades = sum(1 for t in trades if t.get('is_maker', True))`

## `archive/hesoyam_with_fill_rate_limits/polymarket/position_sync.py` [PLATFORM]
**Transport calls in code:**
- L281 (`.get`): `remote_list = remote_by_condition.get(condition_id, [])`

## `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/simple_strat2.py` [TRANSPORT]
**Transport calls in code:**
- L154 (`.get`): `order = self.active_orders.get(order_id)`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/simple_strat2.py` [TRANSPORT]
**Transport calls in code:**
- L154 (`.get`): `order = self.active_orders.get(order_id)`

## `archive/hesoyam_with_fill_rate_limits/tbot_integration/telegram_alerts.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L114 (`.post`): `async with session.post(url, json=payload, timeout=10) as resp:`

## `archive/hesoyam_with_fill_rate_limits/tbot_simulator/metrics.py` [TRANSPORT]
**Transport calls in code:**
- L265 (`.get`): `maker_trades = sum(1 for t in trades if t.get('is_maker', True))`

## `archive/mag_quarantine/lorine93s-analysis/src/polymarket/websocket_client.py` [TRANSPORT]
**External imports:** websockets

**Transport calls in code:**
- L68 (`.get`): `message_type = data.get("type")`

## `archive/quarantine/polymarket_repos/py-clob-client/examples/get_open_orders_with_readonly_key.py` [TRANSPORT]
**Transport calls in code:**
- L20 (`.get`): `response = httpx.get(`

## `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/client.py` [PLATFORM]
**Transport calls in code:**
- L421 (`.get`): `fee_rate = result.get("base_fee") or 0`

## `backtester/scripts/acf_regime_analyzer.py` [TRANSPORT]
**Transport calls in code:**
- L289 (`.get`): `f"({r['n_markets']} markets, ACF[1]={r.get('acf_1', 0):.4f})")`

## `backtester/strategy/order_manager.py` [TRANSPORT]
**Transport calls in code:**
- L188 (`.get`): `for t in side_targets.get(side, []):`

## `dashboard/microstructure/calculator.py` [TRANSPORT]
**Transport calls in code:**
- L156 (`.get`): `pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1`

## `replayer.py` [PLATFORM]
**Transport calls in code:**
- L393 (`.get`): `self.current_time_rem = data.get('time_rem', self.current_time_rem)`

## `scripts/Сканнеры SDK/check_auth.py` [TRANSPORT]
**External imports:** requests

**Transport calls in code:**
- L33 (`.get`): `server_time = requests.get('https://clob.polymarket.com/health').json().get('timestamp')`

## `scripts/Сканнеры SDK/clob_truth.py` [PLATFORM]
**Transport calls in code:**
- L30 (`.get`): `print(f"   MIN ORDER ($): {market_info.get('minimum_order_size')}")`

## `tbot_core/strategy/simple_strat2.py` [TRANSPORT]
**Transport calls in code:**
- L154 (`.get`): `order = self.active_orders.get(order_id)`

## `tbot_integration/telegram_alerts.py` [TRANSPORT]
**External imports:** aiohttp

**Transport calls in code:**
- L114 (`.post`): `async with session.post(url, json=payload, timeout=10) as resp:`
