# Polymarket-Specific Code

Все места где код хардкодит Polymarket-специфику.
Это **точно** то что менять при переходе на multi-venue.

## Hardcoded constants

### `archive/dead_2026-03-04/stress_test_v6.py`
- L35 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300, end_market_buffer_sec=30,
  ```
- L106 **market_duration_sec hardcoded**
  ```python
  ("minimal", GridBacktestConfig(deposit=75, grid_levels=1, grid_lot_size=5, vpin_threshold=0.5, market_duration_sec=300))
  ```
- L107 **market_duration_sec hardcoded**
  ```python
  ("maximal", GridBacktestConfig(deposit=200, grid_levels=3, grid_lot_size=10, vpin_threshold=0.99, market_duration_sec=30
  ```
- L108 **market_duration_sec hardcoded**
  ```python
  ("extreme_AS", GridBacktestConfig(deposit=75, risk_aversion_gamma=1.0, sigma_base=0.1, market_duration_sec=300)),
  ```
- L109 **market_duration_sec hardcoded**
  ```python
  ("tight_stop", GridBacktestConfig(deposit=200, market_pnl_stop_roi=-3.0, market_duration_sec=300)),
  ```
- L110 **market_duration_sec hardcoded**
  ```python
  ("conservative", GridBacktestConfig(deposit=75, end_market_buffer_sec=45, recovery_max_attempts=1, market_duration_sec=3
  ```

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/gabagool_strat.py`
- L2116 **market_duration=900s (15min)**
  ```python
  strat = GabagoolStrat(market_duration_sec=900)
  ```
- L2116 **market_duration_sec hardcoded**
  ```python
  strat = GabagoolStrat(market_duration_sec=900)
  ```

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/strike_fetcher.py`
- L43 **market_duration_sec hardcoded**
  ```python
  fetcher = StrikeFetcher(symbol='ETH', variant='five', market_duration_sec=300)
  ```

### `backtester/optimizer/lhs_screening.py`
- L63 **market_duration_sec hardcoded**
  ```python
  def _params_to_config_v6(params, deposit=150, market_duration_sec=300, name=''):
  ```
- L590 **market_duration_sec hardcoded**
  ```python
  market_duration_sec = 300.0 if args.market_type == '5m' else 900.0
  ```

### `backtester/optimizer/optuna_optimizer.py`
- L128 **market_duration_sec hardcoded**
  ```python
  def _ptbc_v6(params, deposit=150, market_duration_sec=300, name=''):
  ```
- L994 **market_duration_sec hardcoded**
  ```python
  market_duration_sec = 300.0 if args.market_type == '5m' else 900.0
  ```

### `backtester/optimizer/profiles.py`
- L165 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L182 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L182 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L202 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L219 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L219 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L239 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L266 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L266 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L296 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L325 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L325 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L359 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L384 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L384 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```

### `backtester/optimizer/profiles_v6.py`
- L142 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L163 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L184 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L200 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L216 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L216 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L235 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L235 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L252 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L252 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L268 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L268 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L324 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L350 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L350 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```

### `backtester/optimizer/profiles_v6_calibrated.py`
- L52 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L87 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L119 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L158 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L193 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L252 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L310 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L347 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L347 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L378 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L378 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L410 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L410 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L443 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L443 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L478 **market_duration=900s (15min)**
  ```python
  market_duration_sec=900.0,
  ```
- L478 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=900.0,
  ```
- L535 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```
- L572 **market_duration_sec hardcoded**
  ```python
  market_duration_sec=300.0,
  ```

### `strategies/gabagool/execution_engine_v6.py`
- L125 **TICK_SIZE=0.01 (Polymarket tick)**
  ```python
  При TICK_SIZE = 0.01 минимальный сдвиг — это 1 цент.
  ```

### `strategies/gabagool/gabagool_strat.py`
- L2343 **market_duration=900s (15min)**
  ```python
  strat = GabagoolStrat(market_duration_sec=900)
  ```
- L2343 **market_duration_sec hardcoded**
  ```python
  strat = GabagoolStrat(market_duration_sec=900)
  ```

### `strategies/gabagool/grid_manager.py`
- L69 **TICK_SIZE=0.01 (Polymarket tick)**
  ```python
  TICK_SIZE = 0.01
  ```

### `strategies/gabagool/grid_strategy.py`
- L1209 **TICK_SIZE=0.01 (Polymarket tick)**
  ```python
  TICK_SIZE = 0.01
  ```
- L1772 **MIN_MKT_LOT=5 (Polymarket min lot)**
  ```python
  _MIN_MKT_LOT = 5
  ```
- L5169 **MIN_MKT_LOT=5 (Polymarket min lot)**
  ```python
  MIN_MKT_LOT = 5
  ```

## Polymarket keywords usage

### `strategies/gabagool/grid_strategy.py` [PLATFORM] — 351 hits
- `CTF` (1 times) — example L7017: `♻️ CTF CLEARING (MERGE):`
- `MIN_MKT_LOT` (24 times) — example L5169: `MIN_MKT_LOT = 5`
- `condition_id` (4 times) — example L982: `def dump_market_tape(self, condition_id: str, bot_id: str = 'btc_5m') -> str:`
- `ctf` (1 times) — example L7017: `♻️ CTF CLEARING (MERGE):`
- `locked_pairs` (9 times) — example L472: `def locked_pairs(self) -> int:`
- `no_ask` (33 times) — example L1224: `no_ask = market_data.get('no_ask', 0.5)`
- `no_bid` (39 times) — example L1223: `no_bid = market_data.get('no_bid', 0.5)`
- `no_shares` (34 times) — example L445: `no_shares: int = 0          # FREE (доступно для Merge)`
- `pair_state` (4 times) — example L4288: `[v2.10 PAIR_STATE] FSM async-aware pricing.`
- `total_no` (34 times) — example L447: `total_no: int = 0           # TOTAL (все акции кошелька)`
- `total_yes` (35 times) — example L446: `total_yes: int = 0          # TOTAL (все акции кошелька)`
- `yes_ask` (46 times) — example L1222: `yes_ask = market_data.get('yes_ask', 0.5)`
- `yes_bid` (53 times) — example L1203: `oracle_fv = market_data.get('yes_bid', 0.5) # Это твой Initial placeholder`
- `yes_shares` (34 times) — example L444: `yes_shares: int = 0         # FREE (доступно для Merge)`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/gabagool_strat.py` [PLATFORM] — 164 hits
- `condition_id` (1 times) — example L1777: `condition_id=self.config.get('condition_id', ''),`
- `no_ask` (8 times) — example L738: `no_ask = min([float(a.get('price', 1)) for a in no_asks])`
- `no_bid` (21 times) — example L383: `self._bid_history: list = []  # [(timestamp, yes_bid, no_bid)]`
- `no_shares` (52 times) — example L59: `no_shares: Decimal = Decimal('0')`
- `yes_ask` (8 times) — example L737: `yes_ask = min([float(a.get('price', 1)) for a in yes_asks])`
- `yes_bid` (22 times) — example L383: `self._bid_history: list = []  # [(timestamp, yes_bid, no_bid)]`
- `yes_shares` (52 times) — example L58: `yes_shares: Decimal = Decimal('0')`

### `strategies/gabagool/gabagool_strat.py` [PLATFORM] — 164 hits
- `condition_id` (1 times) — example L1997: `condition_id=self.config.get('condition_id', ''),`
- `no_ask` (8 times) — example L775: `no_ask = min([float(a.get('price', 1)) for a in no_asks])`
- `no_bid` (21 times) — example L383: `self._bid_history: list = []  # [(timestamp, yes_bid, no_bid)]`
- `no_shares` (52 times) — example L59: `no_shares: Decimal = Decimal('0')`
- `yes_ask` (8 times) — example L774: `yes_ask = min([float(a.get('price', 1)) for a in yes_asks])`
- `yes_bid` (22 times) — example L383: `self._bid_history: list = []  # [(timestamp, yes_bid, no_bid)]`
- `yes_shares` (52 times) — example L58: `yes_shares: Decimal = Decimal('0')`

### `archive/mag_knowledge/legacy/Well start here/poly_claim/ctf_core.py` [PLATFORM] — 137 hits
- `CTF` (34 times) — example L3: `Polymarket CTF Split/Merge/Redeem via Builder Relayer`
- `GNOSIS` (3 times) — example L20: `- SAFE: Gnosis Safe wallet (Builder Relayer default)`
- `condition_id` (45 times) — example L34: `python test_split_merge_redeem.py --wallet proxy --merge-only --amount 1 -c <CONDITION_ID>`
- `ctf` (34 times) — example L3: `Polymarket CTF Split/Merge/Redeem via Builder Relayer`
- `polygon` (2 times) — example L6: `using the Builder Relayer API on Polygon Mainnet.`
- `polymarket` (14 times) — example L3: `Polymarket CTF Split/Merge/Redeem via Builder Relayer`
- `token_id` (5 times) — example L595: `2. Use CLOB /book endpoint if we have token_id`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/bvmm_strategy.py` [PLATFORM] — 78 hits
- `no_ask` (6 times) — example L404: `no_ask = self._get_best_ask(self.last_no_book)`
- `no_bid` (7 times) — example L402: `no_bid = self._get_best_bid(self.last_no_book)`
- `no_shares` (25 times) — example L5: `Цель: накопить YES_shares ≈ NO_shares так, чтобы средняя цена покупки`
- `polymarket` (2 times) — example L305: `NOTE: Polymarket orderbook has bids sorted ascending (worst to best),`
- `yes_ask` (6 times) — example L403: `yes_ask = self._get_best_ask(self.last_yes_book)`
- `yes_bid` (7 times) — example L401: `yes_bid = self._get_best_bid(self.last_yes_book)`
- `yes_shares` (25 times) — example L5: `Цель: накопить YES_shares ≈ NO_shares так, чтобы средняя цена покупки`

### `tbot_integration/bvmm_strategy.py` [PLATFORM] — 78 hits
- `no_ask` (6 times) — example L404: `no_ask = self._get_best_ask(self.last_no_book)`
- `no_bid` (7 times) — example L402: `no_bid = self._get_best_bid(self.last_no_book)`
- `no_shares` (25 times) — example L5: `Цель: накопить YES_shares ≈ NO_shares так, чтобы средняя цена покупки`
- `polymarket` (2 times) — example L305: `NOTE: Polymarket orderbook has bids sorted ascending (worst to best),`
- `yes_ask` (6 times) — example L403: `yes_ask = self._get_best_ask(self.last_yes_book)`
- `yes_bid` (7 times) — example L401: `yes_bid = self._get_best_bid(self.last_yes_book)`
- `yes_shares` (25 times) — example L5: `Цель: накопить YES_shares ≈ NO_shares так, чтобы средняя цена покупки`

### `tbot_integration/grid_adapter.py` [PLATFORM] — 64 hits
- `condition_id` (2 times) — example L912: `'condition_id': self.current_market_id,`
- `no_ask` (8 times) — example L725: `self._fill_ob_state.no_best_ask = float(orderbook.get('no_ask', 0.50))`
- `no_bid` (8 times) — example L724: `self._fill_ob_state.no_best_bid = float(orderbook.get('no_bid', 0.50))`
- `no_shares` (7 times) — example L218: `pos.no_shares = f_n`
- `polymarket` (5 times) — example L88: `"""[v11.12] Хамелеон для обхода бага SDK Polymarket: и число, и объект с .value"""`
- `token_id` (1 times) — example L188: `str(t_id),             # 2. token_id`
- `total_no` (3 times) — example L212: `if t_y != pos.total_yes or t_n != pos.total_no:`
- `total_yes` (3 times) — example L212: `if t_y != pos.total_yes or t_n != pos.total_no:`
- `yes_ask` (10 times) — example L451: `spread_at_creation=max(0.0, self._ob_cache.get('yes_ask', 0.5) - self._ob_cache.get('yes_bid', 0.5)) if hasattr(self, '_`
- `yes_bid` (10 times) — example L451: `spread_at_creation=max(0.0, self._ob_cache.get('yes_ask', 0.5) - self._ob_cache.get('yes_bid', 0.5)) if hasattr(self, '_`
- `yes_shares` (7 times) — example L216: `pos.yes_shares = f_y`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/client.py` [PLATFORM] — 51 hits
- `condition_id` (5 times) — example L988: `def get_market(self, condition_id):`
- `token_id` (46 times) — example L359: `def get_midpoint(self, token_id):`

### `archive/dead_2026-03-04/grid_adapter.py` [PLATFORM] — 45 hits
- `no_ask` (8 times) — example L261: `self._fill_ob_state.no_best_ask = float(orderbook.get('no_ask', 0.50))`
- `no_bid` (9 times) — example L260: `self._fill_ob_state.no_best_bid = float(orderbook.get('no_bid', 0.50))`
- `no_shares` (5 times) — example L456: `'no_shares': self.strategy.position.no_shares,`
- `yes_ask` (8 times) — example L259: `self._fill_ob_state.yes_best_ask = float(orderbook.get('yes_ask', 0.50))`
- `yes_bid` (9 times) — example L258: `self._fill_ob_state.yes_best_bid = float(orderbook.get('yes_bid', 0.50))`
- `yes_shares` (6 times) — example L455: `'yes_shares': self.strategy.position.yes_shares,`

### `scripts/claim_resolved.py` [PLATFORM] — 43 hits
- `CTF` (6 times) — example L2: `Claim resolved positions — redeem CTF tokens for USDC.e`
- `condition_id` (23 times) — example L9: `Нужен для получения condition_id и token_ids по slug`
- `ctf` (6 times) — example L2: `Claim resolved positions — redeem CTF tokens for USDC.e`
- `no_shares` (2 times) — example L334: `no_s  = state.get('no_shares', 0) or 0`
- `polygon` (1 times) — example L106: `RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')`
- `polymarket` (3 times) — example L185: `r = requests.get('https://gamma-api.polymarket.com/markets',`
- `yes_shares` (2 times) — example L333: `yes_s = state.get('yes_shares', 0) or 0`

### `backtester/strategy/position_tracker.py` [PLATFORM] — 42 hits
- `no_shares` (21 times) — example L21: `self.no_shares: float = 0.0`
- `yes_shares` (21 times) — example L20: `self.yes_shares: float = 0.0`

### `strategies/gabagool/live_trading_bridge.py` [PLATFORM] — 37 hits
- `condition_id` (3 times) — example L355: `'condition_id': self._logger.current_market.get('condition_id', '') if self._logger.current_market else '',`
- `no_ask` (3 times) — example L685: `no_ask = float(no_asks[0].get('price', 0) if isinstance(no_asks[0], dict) else no_asks[0][0]) if no_asks else 0`
- `no_bid` (3 times) — example L684: `no_bid = float(no_bids[0].get('price', 0) if isinstance(no_bids[0], dict) else no_bids[0][0])`
- `no_shares` (8 times) — example L344: `if pos.yes_shares > 0 or pos.no_shares > 0:`
- `polygon` (2 times) — example L812: `v2.4.6: Fetch USDC.e balance from Polygon RPC.`
- `polymarket` (1 times) — example L854: `Polymarket distributes maker rebates daily at 00:00 UTC as USDC.`
- `yes_ask` (3 times) — example L683: `yes_ask = float(yes_asks[0].get('price', 0) if isinstance(yes_asks[0], dict) else yes_asks[0][0]) if yes_asks else 0`
- `yes_bid` (6 times) — example L310: `if entry.get('type') == 'tick' and entry.get('yes_bid', 0) > 0.01:`
- `yes_shares` (8 times) — example L344: `if pos.yes_shares > 0 or pos.no_shares > 0:`

### `backtester/strategy/grid_strategy_sim.py` [PLATFORM] — 36 hits
- `no_ask` (4 times) — example L307: `no_ask = self.ob.no_best_ask or 0.50`
- `no_bid` (4 times) — example L306: `no_bid = self.ob.no_best_bid or 0.50`
- `no_shares` (8 times) — example L321: `q = self.position.yes_shares - self.position.no_shares`
- `yes_ask` (6 times) — example L293: `yes_ask = self.ob.yes_best_ask if self.ob.yes_best_ask > 0 else 0.50`
- `yes_bid` (6 times) — example L292: `yes_bid = self.ob.yes_best_bid if self.ob.yes_best_bid > 0 else 0.50`
- `yes_shares` (8 times) — example L321: `q = self.position.yes_shares - self.position.no_shares`

### `strategies/gabagool/strategy_adapter.py` [PLATFORM] — 35 hits
- `condition_id` (6 times) — example L578: `condition_id=getattr(self.strategy, 'current_condition_id', '') or "",`
- `no_shares` (2 times) — example L2275: `no_value = pos.no_shares * no_price`
- `polygon` (2 times) — example L182: `- PRIVATE_KEY: Polygon wallet private key`
- `polymarket` (2 times) — example L226: `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- `token_id` (21 times) — example L88: `self.current_token_ids: Dict[str, str] = {}  # {'YES': token_id, 'NO': token_id}`
- `yes_shares` (2 times) — example L2274: `yes_value = pos.yes_shares * yes_price`

### `tbot_integration/strategy_adapter.py` [PLATFORM] — 35 hits
- `condition_id` (6 times) — example L588: `condition_id=getattr(self.strategy, 'current_condition_id', '') or "",`
- `no_shares` (2 times) — example L2285: `no_value = pos.no_shares * no_price`
- `polygon` (2 times) — example L192: `- PRIVATE_KEY: Polygon wallet private key`
- `polymarket` (2 times) — example L236: `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- `token_id` (21 times) — example L98: `self.current_token_ids: Dict[str, str] = {}  # {'YES': token_id, 'NO': token_id}`
- `yes_shares` (2 times) — example L2284: `yes_value = pos.yes_shares * yes_price`

### `archive/dead_2026-03-04/tbot_core_blockchain/ctf_client.py` [PLATFORM] — 34 hits
- `CTF` (5 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `condition_id` (18 times) — example L128: `def build_split_data(self, condition_id: str, amount_usd: Decimal) -> str:`
- `ctf` (5 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `polygon` (2 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `polymarket` (2 times) — example L24: `RELAYER_URL = "https://relayer-v2.polymarket.com"`
- `token_id` (2 times) — example L113: `def get_token_balance(self, token_id: str, address: Optional[str] = None) -> Decimal:`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/opportunity_evaluator.py` [PLATFORM] — 34 hits
- `no_ask` (5 times) — example L554: `no_ask = self._get_best_ask(orderbook, 'no')`
- `no_bid` (3 times) — example L99: `no_bid = self._get_best_bid(orderbook, 'no')`
- `no_shares` (9 times) — example L125: `no_shares = self._get_shares(position, 'no')`
- `yes_ask` (5 times) — example L553: `yes_ask = self._get_best_ask(orderbook, 'yes')`
- `yes_bid` (3 times) — example L98: `yes_bid = self._get_best_bid(orderbook, 'yes')`
- `yes_shares` (9 times) — example L124: `yes_shares = self._get_shares(position, 'yes')`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/blockchain/ctf_client.py` [PLATFORM] — 34 hits
- `CTF` (5 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `condition_id` (18 times) — example L128: `def build_split_data(self, condition_id: str, amount_usd: Decimal) -> str:`
- `ctf` (5 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `polygon` (2 times) — example L2: `CTF Client - Conditional Token Framework operations on Polygon`
- `polymarket` (2 times) — example L24: `RELAYER_URL = "https://relayer-v2.polymarket.com"`
- `token_id` (2 times) — example L113: `def get_token_balance(self, token_id: str, address: Optional[str] = None) -> Decimal:`

### `strategies/gabagool/opportunity_evaluator.py` [PLATFORM] — 34 hits
- `no_ask` (5 times) — example L554: `no_ask = self._get_best_ask(orderbook, 'no')`
- `no_bid` (3 times) — example L99: `no_bid = self._get_best_bid(orderbook, 'no')`
- `no_shares` (9 times) — example L125: `no_shares = self._get_shares(position, 'no')`
- `yes_ask` (5 times) — example L553: `yes_ask = self._get_best_ask(orderbook, 'yes')`
- `yes_bid` (3 times) — example L98: `yes_bid = self._get_best_bid(orderbook, 'yes')`
- `yes_shares` (9 times) — example L124: `yes_shares = self._get_shares(position, 'yes')`

### `backtester/strategy/strategy_sim.py` [PLATFORM] — 32 hits
- `no_shares` (16 times) — example L487: `total_shares = self.position.yes_shares + self.position.no_shares`
- `yes_shares` (16 times) — example L487: `total_shares = self.position.yes_shares + self.position.no_shares`

### `dashboard/server.py` [PLATFORM] — 29 hits
- `condition_id` (25 times) — example L248: `condition_id: str = ""`
- `no_shares` (2 times) — example L181: `'yes_shares': 0, 'no_shares': 0,`
- `yes_shares` (2 times) — example L181: `'yes_shares': 0, 'no_shares': 0,`

### `tbot_integration/live_trading_bridge.py` [PLATFORM] — 29 hits
- `CTF` (1 times) — example L863: `logger.info("        ♻️ CTF CLEARING (MERGE):")`
- `condition_id` (8 times) — example L256: `async def _fetch_market_volume(self, condition_id: str) -> float:`
- `ctf` (1 times) — example L863: `logger.info("        ♻️ CTF CLEARING (MERGE):")`
- `no_shares` (3 times) — example L661: `snap_no = float(pos.no_shares)`
- `polygon` (3 times) — example L1545: `'https://polygon-rpc.com',`
- `polymarket` (2 times) — example L260: `url = f"https://gamma-api.polymarket.com/markets/{condition_id}"`
- `total_no` (1 times) — example L663: `snap_tot_no = float(pos.total_no)`
- `total_yes` (1 times) — example L662: `snap_tot_yes = float(pos.total_yes)`
- `yes_bid` (6 times) — example L534: `yes_bid = market_state.get('yes_bid', 0.5)`
- `yes_shares` (3 times) — example L660: `snap_yes = float(pos.yes_shares)`

### `archive/hesoyam_with_fill_rate_limits/backtester/strategy/position_tracker.py` [PLATFORM] — 28 hits
- `no_shares` (14 times) — example L15: `self.no_shares: float = 0.0`
- `yes_shares` (14 times) — example L14: `self.yes_shares: float = 0.0`

### `archive/dead_2026-03-04/ws_implementation_code.py` [PLATFORM] — 27 hits
- `condition_id` (9 times) — example L153: `condition_id:  str,`
- `polymarket` (11 times) — example L3: `POLYMARKET WEBSOCKET IMPLEMENTATION — SOURCE CODE`
- `token_id` (7 times) — example L624: `token_id:     str,`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/strategy_adapter.py` [PLATFORM] — 26 hits
- `condition_id` (5 times) — example L531: `condition_id=getattr(self.strategy, 'current_condition_id', '') or "",`
- `no_shares` (2 times) — example L1981: `no_value = pos.no_shares * no_price`
- `polygon` (2 times) — example L177: `- PRIVATE_KEY: Polygon wallet private key`
- `polymarket` (2 times) — example L221: `'clob_base_url': config.get('clob_base_url', 'https://clob.polymarket.com'),`
- `token_id` (13 times) — example L83: `self.current_token_ids: Dict[str, str] = {}  # {'YES': token_id, 'NO': token_id}`
- `yes_shares` (2 times) — example L1980: `yes_value = pos.yes_shares * yes_price`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/results_tracker.py` [PLATFORM] — 25 hits
- `condition_id` (6 times) — example L34: `condition_id: str`
- `no_shares` (9 times) — example L38: `no_shares: float`
- `polymarket` (1 times) — example L94: `GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"`
- `yes_shares` (9 times) — example L37: `yes_shares: float`

### `strategies/gabagool/results_tracker.py` [PLATFORM] — 25 hits
- `condition_id` (6 times) — example L64: `condition_id: str`
- `no_shares` (9 times) — example L68: `no_shares: float`
- `polymarket` (1 times) — example L124: `GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"`
- `yes_shares` (9 times) — example L67: `yes_shares: float`

### `archive/dead_2026-03-04/polymarket/position_sync.py` [PLATFORM] — 24 hits
- `condition_id` (13 times) — example L32: `condition_id: str`
- `no_shares` (4 times) — example L66: `no_shares: float`
- `polymarket` (3 times) — example L2: `Position Sync — Verifies local position state against Polymarket.`
- `yes_shares` (4 times) — example L65: `yes_shares: float`

### `archive/hesoyam_with_fill_rate_limits/polymarket/position_sync.py` [PLATFORM] — 24 hits
- `condition_id` (13 times) — example L32: `condition_id: str`
- `no_shares` (4 times) — example L66: `no_shares: float`
- `polymarket` (3 times) — example L2: `Position Sync — Verifies local position state against Polymarket.`
- `yes_shares` (4 times) — example L65: `yes_shares: float`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/lot_sizer.py` [PLATFORM] — 24 hits
- `no_shares` (12 times) — example L200: `no_shares = float(self._get_shares(position, 'no'))`
- `yes_shares` (12 times) — example L199: `yes_shares = float(self._get_shares(position, 'yes'))`

### `strategies/gabagool/lot_sizer.py` [PLATFORM] — 24 hits
- `no_shares` (12 times) — example L200: `no_shares = float(self._get_shares(position, 'no'))`
- `yes_shares` (12 times) — example L199: `yes_shares = float(self._get_shares(position, 'yes'))`

### `archive/dead_2026-03-04/polymarket/client.py` [PLATFORM] — 22 hits
- `condition_id` (9 times) — example L80: `condition_id: str`
- `polygon` (2 times) — example L131: `chain_id: int = 137,  # Polygon mainnet`
- `polymarket` (4 times) — example L2: `Polymarket CLOB API Client`
- `token_id` (7 times) — example L120: `result = await client.create_order(token_id, "BUY", 10, 0.45)`

### `archive/hesoyam_with_fill_rate_limits/polymarket/client.py` [PLATFORM] — 22 hits
- `condition_id` (9 times) — example L80: `condition_id: str`
- `polygon` (2 times) — example L131: `chain_id: int = 137,  # Polygon mainnet`
- `polymarket` (4 times) — example L2: `Polymarket CLOB API Client`
- `token_id` (7 times) — example L120: `result = await client.create_order(token_id, "BUY", 10, 0.45)`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/bankroll_manager.py` [PLATFORM] — 22 hits
- `no_shares` (11 times) — example L193: `def is_imbalanced(self, yes_shares: int, no_shares: int) -> bool:`
- `yes_shares` (11 times) — example L193: `def is_imbalanced(self, yes_shares: int, no_shares: int) -> bool:`

### `strategies/gabagool/bankroll_manager.py` [PLATFORM] — 22 hits
- `no_shares` (11 times) — example L193: `def is_imbalanced(self, yes_shares: int, no_shares: int) -> bool:`
- `yes_shares` (11 times) — example L193: `def is_imbalanced(self, yes_shares: int, no_shares: int) -> bool:`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/position_tracker.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L14: `no_shares: Decimal = Decimal('0')`
- `yes_shares` (10 times) — example L13: `yes_shares: Decimal = Decimal('0')`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_risk/guards.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L124: `no_shares = Decimal(str(position.get('no_shares', 0)))`
- `yes_shares` (10 times) — example L123: `yes_shares = Decimal(str(position.get('yes_shares', 0)))`

### `archive/dead_2026-03-04/tbot_core_execution/position_tracker.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L14: `no_shares: Decimal = Decimal('0')`
- `yes_shares` (10 times) — example L13: `yes_shares: Decimal = Decimal('0')`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/position_tracker.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L14: `no_shares: Decimal = Decimal('0')`
- `yes_shares` (10 times) — example L13: `yes_shares: Decimal = Decimal('0')`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/position_tracker.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L14: `no_shares: Decimal = Decimal('0')`
- `yes_shares` (10 times) — example L13: `yes_shares: Decimal = Decimal('0')`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_risk/guards.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L124: `no_shares = Decimal(str(position.get('no_shares', 0)))`
- `yes_shares` (10 times) — example L123: `yes_shares = Decimal(str(position.get('yes_shares', 0)))`

### `archive/hesoyam_with_fill_rate_limits/tbot_risk/guards.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L124: `no_shares = Decimal(str(position.get('no_shares', 0)))`
- `yes_shares` (10 times) — example L123: `yes_shares = Decimal(str(position.get('yes_shares', 0)))`

### `replayer.py` [PLATFORM] — 20 hits
- `no_ask` (4 times) — example L132: `elif side == 'NO' and market_data['no_ask'] <= price:`
- `no_bid` (4 times) — example L138: `elif side == 'NO' and market_data['no_bid'] >= price:`
- `total_no` (2 times) — example L353: `payout = pos.total_yes if winner == 'YES' else pos.total_no`
- `total_yes` (2 times) — example L353: `payout = pos.total_yes if winner == 'YES' else pos.total_no`
- `yes_ask` (4 times) — example L130: `if side == 'YES' and market_data['yes_ask'] <= price:`
- `yes_bid` (4 times) — example L136: `if side == 'YES' and market_data['yes_bid'] >= price:`

### `tbot_risk/guards.py` [PLATFORM] — 20 hits
- `no_shares` (10 times) — example L124: `no_shares = Decimal(str(position.get('no_shares', 0)))`
- `yes_shares` (10 times) — example L123: `yes_shares = Decimal(str(position.get('yes_shares', 0)))`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/ws_client.py` [PLATFORM] — 19 hits
- `condition_id` (14 times) — example L28: `self.subscribed_markets: Dict[str, Dict] = {}  # condition_id -> market data`
- `polymarket` (4 times) — example L2: `Polymarket WebSocket Client for real-time market data`
- `token_id` (1 times) — example L29: `self.orderbooks: Dict[str, Dict] = {}  # condition_id -> {token_id -> book}`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/ws_client.py` [PLATFORM] — 19 hits
- `condition_id` (14 times) — example L28: `self.subscribed_markets: Dict[str, Dict] = {}  # condition_id -> market data`
- `polymarket` (4 times) — example L2: `Polymarket WebSocket Client for real-time market data`
- `token_id` (1 times) — example L29: `self.orderbooks: Dict[str, Dict] = {}  # condition_id -> {token_id -> book}`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/ws_client.py` [PLATFORM] — 19 hits
- `condition_id` (14 times) — example L28: `self.subscribed_markets: Dict[str, Dict] = {}  # condition_id -> market data`
- `polymarket` (4 times) — example L2: `Polymarket WebSocket Client for real-time market data`
- `token_id` (1 times) — example L29: `self.orderbooks: Dict[str, Dict] = {}  # condition_id -> {token_id -> book}`

### `tbot_core/api/ws_client.py` [PLATFORM] — 19 hits
- `condition_id` (14 times) — example L28: `self.subscribed_markets: Dict[str, Dict] = {}  # condition_id -> market data`
- `polymarket` (4 times) — example L2: `Polymarket WebSocket Client for real-time market data`
- `token_id` (1 times) — example L29: `self.orderbooks: Dict[str, Dict] = {}  # condition_id -> {token_id -> book}`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/enhanced_bvmm.py` [PLATFORM] — 18 hits
- `no_ask` (5 times) — example L91: `no_ask = state.no_book['asks'][0] if state.no_book['asks'] else None`
- `no_bid` (4 times) — example L90: `no_bid = state.no_book['bids'][0] if state.no_book['bids'] else None`
- `yes_ask` (5 times) — example L89: `yes_ask = state.yes_book['asks'][0] if state.yes_book['asks'] else None`
- `yes_bid` (4 times) — example L88: `yes_bid = state.yes_book['bids'][0] if state.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/rebalancer.py` [PLATFORM] — 18 hits
- `no_shares` (9 times) — example L132: `position: PositionState с yes_shares и no_shares`
- `yes_shares` (9 times) — example L132: `position: PositionState с yes_shares и no_shares`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/enhanced_bvmm.py` [PLATFORM] — 18 hits
- `no_ask` (5 times) — example L91: `no_ask = state.no_book['asks'][0] if state.no_book['asks'] else None`
- `no_bid` (4 times) — example L90: `no_bid = state.no_book['bids'][0] if state.no_book['bids'] else None`
- `yes_ask` (5 times) — example L89: `yes_ask = state.yes_book['asks'][0] if state.yes_book['asks'] else None`
- `yes_bid` (4 times) — example L88: `yes_bid = state.yes_book['bids'][0] if state.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/enhanced_bvmm.py` [PLATFORM] — 18 hits
- `no_ask` (5 times) — example L91: `no_ask = state.no_book['asks'][0] if state.no_book['asks'] else None`
- `no_bid` (4 times) — example L90: `no_bid = state.no_book['bids'][0] if state.no_book['bids'] else None`
- `yes_ask` (5 times) — example L89: `yes_ask = state.yes_book['asks'][0] if state.yes_book['asks'] else None`
- `yes_bid` (4 times) — example L88: `yes_bid = state.yes_book['bids'][0] if state.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/live_trading_bridge.py` [PLATFORM] — 18 hits
- `condition_id` (2 times) — example L296: `'condition_id': current_market.get('condition_id') if current_market else None,`
- `no_ask` (3 times) — example L511: `no_ask = float(no_asks[0].get('price', 0) if isinstance(no_asks[0], dict) else no_asks[0][0]) if no_asks else 0`
- `no_bid` (3 times) — example L510: `no_bid = float(no_bids[0].get('price', 0) if isinstance(no_bids[0], dict) else no_bids[0][0])`
- `no_shares` (1 times) — example L522: `no_sh = float(pos.no_shares) if pos else 0`
- `polygon` (2 times) — example L638: `v2.4.6: Fetch USDC.e balance from Polygon RPC.`
- `yes_ask` (3 times) — example L509: `yes_ask = float(yes_asks[0].get('price', 0) if isinstance(yes_asks[0], dict) else yes_asks[0][0]) if yes_asks else 0`
- `yes_bid` (3 times) — example L508: `yes_bid = float(yes_bids[0].get('price', 0) if isinstance(yes_bids[0], dict) else yes_bids[0][0])`
- `yes_shares` (1 times) — example L521: `yes_sh = float(pos.yes_shares) if pos else 0`

### `strategies/gabagool/rebalancer.py` [PLATFORM] — 18 hits
- `no_shares` (9 times) — example L132: `position: PositionState с yes_shares и no_shares`
- `yes_shares` (9 times) — example L132: `position: PositionState с yes_shares и no_shares`

### `tbot_core/strategy/enhanced_bvmm.py` [PLATFORM] — 18 hits
- `no_ask` (5 times) — example L91: `no_ask = state.no_book['asks'][0] if state.no_book['asks'] else None`
- `no_bid` (4 times) — example L90: `no_bid = state.no_book['bids'][0] if state.no_book['bids'] else None`
- `yes_ask` (5 times) — example L89: `yes_ask = state.yes_book['asks'][0] if state.yes_book['asks'] else None`
- `yes_bid` (4 times) — example L88: `yes_bid = state.yes_book['bids'][0] if state.yes_book['bids'] else None`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/models.py` [PLATFORM] — 17 hits
- `no_shares` (8 times) — example L221: `no_shares: Decimal = Decimal('0')`
- `polymarket` (1 times) — example L2: `Data models for Polymarket API responses and internal data structures`
- `yes_shares` (8 times) — example L220: `yes_shares: Decimal = Decimal('0')`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/signing.py` [PLATFORM] — 17 hits
- `CTF` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `GNOSIS` (1 times) — example L14: `- GNOSIS_SAFE (2): Gnosis Safe multisig`
- `ctf` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `polygon` (1 times) — example L88: `chain_id: Polygon chain ID (137 for mainnet)`
- `polymarket` (7 times) — example L2: `Polymarket Order Signing`
- `token_id` (6 times) — example L243: `token_id: str,`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/models.py` [PLATFORM] — 17 hits
- `no_shares` (8 times) — example L221: `no_shares: Decimal = Decimal('0')`
- `polymarket` (1 times) — example L2: `Data models for Polymarket API responses and internal data structures`
- `yes_shares` (8 times) — example L220: `yes_shares: Decimal = Decimal('0')`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/signing.py` [PLATFORM] — 17 hits
- `CTF` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `GNOSIS` (1 times) — example L14: `- GNOSIS_SAFE (2): Gnosis Safe multisig`
- `ctf` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `polygon` (1 times) — example L88: `chain_id: Polygon chain ID (137 for mainnet)`
- `polymarket` (7 times) — example L2: `Polymarket Order Signing`
- `token_id` (6 times) — example L243: `token_id: str,`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/models.py` [PLATFORM] — 17 hits
- `no_shares` (8 times) — example L221: `no_shares: Decimal = Decimal('0')`
- `polymarket` (1 times) — example L2: `Data models for Polymarket API responses and internal data structures`
- `yes_shares` (8 times) — example L220: `yes_shares: Decimal = Decimal('0')`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/signing.py` [PLATFORM] — 17 hits
- `CTF` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `GNOSIS` (1 times) — example L14: `- GNOSIS_SAFE (2): Gnosis Safe multisig`
- `ctf` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `polygon` (1 times) — example L88: `chain_id: Polygon chain ID (137 for mainnet)`
- `polymarket` (7 times) — example L2: `Polymarket Order Signing`
- `token_id` (6 times) — example L243: `token_id: str,`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/rfq/rfq_client.py` [PLATFORM] — 17 hits
- `polymarket` (1 times) — example L2: `RFQ (Request for Quote) client for the Polymarket CLOB API.`
- `token_id` (16 times) — example L131: `user_order: Simplified order with token_id, price, side, size`

### `dashboard/microstructure/tape_renderer.py` [PLATFORM] — 17 hits
- `condition_id` (3 times) — example L7: `Input:  logs/market_tapes/{bot_id}_{condition_id}.json`
- `no_ask` (3 times) — example L67: `no_ask = np.array([t.get('no_ask', 0) for t in ticks])`
- `no_bid` (4 times) — example L65: `no_bid = np.array([t.get('no_bid', 0) for t in ticks])`
- `yes_ask` (3 times) — example L66: `yes_ask = np.array([t.get('yes_ask', 0) for t in ticks])`
- `yes_bid` (4 times) — example L64: `yes_bid = np.array([t.get('yes_bid', 0) for t in ticks])`

### `tbot_core/api/models.py` [PLATFORM] — 17 hits
- `no_shares` (8 times) — example L221: `no_shares: Decimal = Decimal('0')`
- `polymarket` (1 times) — example L2: `Data models for Polymarket API responses and internal data structures`
- `yes_shares` (8 times) — example L220: `yes_shares: Decimal = Decimal('0')`

### `tbot_core/api/signing.py` [PLATFORM] — 17 hits
- `CTF` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `GNOSIS` (1 times) — example L14: `- GNOSIS_SAFE (2): Gnosis Safe multisig`
- `ctf` (1 times) — example L235: `"name": "Polymarket CTF Exchange",`
- `polygon` (1 times) — example L88: `chain_id: Polygon chain ID (137 for mainnet)`
- `polymarket` (7 times) — example L2: `Polymarket Order Signing`
- `token_id` (6 times) — example L243: `token_id: str,`

### `archive/dead_2026-03-04/test_recovery_module_v6.py` [PLATFORM] — 16 hits
- `no_shares` (8 times) — example L25: `yes_shares=12, no_shares=10, total_cost=10.0, deposit=100.0,`
- `yes_shares` (8 times) — example L25: `yes_shares=12, no_shares=10, total_cost=10.0, deposit=100.0,`

### `archive/hesoyam_with_fill_rate_limits/tbot_logger/orderbook_logger.py` [PLATFORM] — 16 hits
- `condition_id` (8 times) — example L174: `market_id=self.current_market['condition_id'],`
- `polymarket` (2 times) — example L2: `Orderbook logger for Polymarket`
- `token_id` (6 times) — example L129: `token_id TEXT NOT NULL,`

### `tbot_logger/orderbook_logger.py` [PLATFORM] — 15 hits
- `condition_id` (7 times) — example L197: `market_id=self.current_market['condition_id'],`
- `polymarket` (2 times) — example L2: `Orderbook logger for Polymarket`
- `token_id` (6 times) — example L163: `token_id TEXT NOT NULL,`

### `archive/hesoyam_with_fill_rate_limits/backtester/strategy/strategy_sim.py` [PLATFORM] — 14 hits
- `no_shares` (7 times) — example L263: `total_shares = self.position.yes_shares + self.position.no_shares`
- `yes_shares` (7 times) — example L263: `total_shares = self.position.yes_shares + self.position.no_shares`

### `archive/hesoyam_with_fill_rate_limits/scripts/claim_resolved.py` [PLATFORM] — 14 hits
- `CTF` (3 times) — example L2: `Claim resolved positions — redeem CTF tokens for USDC.e`
- `condition_id` (5 times) — example L44: `"""Load claim queue from file. Format: {slug: {condition_id, added_at, status}}"""`
- `ctf` (3 times) — example L2: `Claim resolved positions — redeem CTF tokens for USDC.e`
- `polygon` (1 times) — example L117: `w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))`
- `polymarket` (2 times) — example L75: `r = requests.get('https://gamma-api.polymarket.com/markets',`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/recovery_module.py` [PLATFORM] — 14 hits
- `no_shares` (7 times) — example L87: `no_shares: int,`
- `yes_shares` (7 times) — example L86: `yes_shares: int,`

### `strategies/gabagool/recovery_module.py` [PLATFORM] — 14 hits
- `no_shares` (7 times) — example L90: `no_shares: int,`
- `yes_shares` (7 times) — example L89: `yes_shares: int,`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/orderbook_logger.py` [PLATFORM] — 11 hits
- `condition_id` (6 times) — example L167: `self.current_market['condition_id'],`
- `polymarket` (1 times) — example L2: `Orderbook logger for Polymarket`
- `token_id` (4 times) — example L91: `token_id TEXT NOT NULL,`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/orderbook_logger.py` [PLATFORM] — 11 hits
- `condition_id` (6 times) — example L167: `self.current_market['condition_id'],`
- `polymarket` (1 times) — example L2: `Orderbook logger for Polymarket`
- `token_id` (4 times) — example L91: `token_id TEXT NOT NULL,`

### `archive/dead_2026-03-04/live_test_buy_both.py` [PLATFORM] — 10 hits
- `no_bid` (3 times) — example L95: `no_bid = float(no_bids[0].price)`
- `polymarket` (2 times) — example L22: `HOST = 'https://clob.polymarket.com'`
- `token_id` (2 times) — example L114: `yes_args = OrderArgs(price=yes_price, size=1.0, side=BUY, token_id=yes_token)`
- `yes_bid` (3 times) — example L94: `yes_bid = float(yes_bids[0].price)`

### `archive/dead_2026-03-04/recovery_module_v6.py` [PLATFORM] — 10 hits
- `no_shares` (5 times) — example L64: `no_shares: int,`
- `yes_shares` (5 times) — example L63: `yes_shares: int,`

### `archive/hesoyam_with_fill_rate_limits/backtester/results_db.py` [PLATFORM] — 10 hits
- `no_shares` (5 times) — example L46: `no_shares REAL,`
- `yes_shares` (5 times) — example L45: `yes_shares REAL,`

### `archive/hesoyam_with_fill_rate_limits/scripts/live_test_buy_both.py` [PLATFORM] — 10 hits
- `no_bid` (3 times) — example L95: `no_bid = float(no_bids[0].price)`
- `polymarket` (2 times) — example L22: `HOST = 'https://clob.polymarket.com'`
- `token_id` (2 times) — example L114: `yes_args = OrderArgs(price=yes_price, size=1.0, side=BUY, token_id=yes_token)`
- `yes_bid` (3 times) — example L94: `yes_bid = float(yes_bids[0].price)`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/price_filter.py` [PLATFORM] — 10 hits
- `no_ask` (5 times) — example L5: `the all-in sum (YES_ask + NO_ask) over a lookback window.`
- `yes_ask` (5 times) — example L5: `the all-in sum (YES_ask + NO_ask) over a lookback window.`

### `backtester/core/engine_v6.py` [PLATFORM] — 10 hits
- `no_shares` (3 times) — example L111: `proj_no = strategy.position.no_shares + (0 if fill_event.is_yes else fill_event.size)`
- `total_no` (2 times) — example L48: `winner='UNKNOWN', pnl=0.0, total_yes=0.0, total_no=0.0,`
- `total_yes` (2 times) — example L48: `winner='UNKNOWN', pnl=0.0, total_yes=0.0, total_no=0.0,`
- `yes_shares` (3 times) — example L110: `proj_yes = strategy.position.yes_shares + (fill_event.size if fill_event.is_yes else 0)`

### `backtester/results_db.py` [PLATFORM] — 10 hits
- `no_shares` (5 times) — example L46: `no_shares REAL,`
- `yes_shares` (5 times) — example L45: `yes_shares REAL,`

### `strategies/gabagool/execution_engine_v6.py` [PLATFORM] — 10 hits
- `polymarket` (1 times) — example L31: `"""Глобальный сериализатор для Pydantic объектов Polymarket"""`
- `token_id` (9 times) — example L211: `token_id = self.yes_token_id if actual_side == 'YES' else self.no_token_id`

### `strategies/gabagool/price_filter.py` [PLATFORM] — 10 hits
- `no_ask` (5 times) — example L5: `the all-in sum (YES_ask + NO_ask) over a lookback window.`
- `yes_ask` (5 times) — example L5: `the all-in sum (YES_ask + NO_ask) over a lookback window.`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/claim_manager.py` [PLATFORM] — 9 hits
- `condition_id` (7 times) — example L57: `'condition_id': market.get('conditionId'),`
- `polymarket` (2 times) — example L44: `url = f"https://gamma-api.polymarket.com/events/slug/{market_slug}"`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/types.py` [PLATFORM] — 9 hits
- `condition_id` (1 times) — example L35: `condition_id: str`
- `no_ask` (2 times) — example L110: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L109: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L108: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L107: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/dead_2026-03-04/tbot_core_execution/claim_manager.py` [PLATFORM] — 9 hits
- `condition_id` (7 times) — example L57: `'condition_id': market.get('conditionId'),`
- `polymarket` (2 times) — example L44: `url = f"https://gamma-api.polymarket.com/events/slug/{market_slug}"`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/claim_manager.py` [PLATFORM] — 9 hits
- `condition_id` (7 times) — example L57: `'condition_id': market.get('conditionId'),`
- `polymarket` (2 times) — example L44: `url = f"https://gamma-api.polymarket.com/events/slug/{market_slug}"`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/types.py` [PLATFORM] — 9 hits
- `condition_id` (1 times) — example L35: `condition_id: str`
- `no_ask` (2 times) — example L110: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L109: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L108: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L107: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/claim_manager.py` [PLATFORM] — 9 hits
- `condition_id` (7 times) — example L57: `'condition_id': market.get('conditionId'),`
- `polymarket` (2 times) — example L44: `url = f"https://gamma-api.polymarket.com/events/slug/{market_slug}"`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/types.py` [PLATFORM] — 9 hits
- `condition_id` (1 times) — example L35: `condition_id: str`
- `no_ask` (2 times) — example L110: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L109: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L108: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L107: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `tbot_core/strategy/types.py` [PLATFORM] — 9 hits
- `condition_id` (1 times) — example L35: `condition_id: str`
- `no_ask` (2 times) — example L110: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L109: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L108: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L107: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/core.py` [PLATFORM] — 8 hits
- `no_ask` (2 times) — example L48: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L47: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L46: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L45: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/log_reader.py` [PLATFORM] — 8 hits
- `token_id` (8 times) — example L66: `token_id = message[token_start:token_end].strip()`

### `archive/dead_2026-03-04/test_live_order_ws.py` [PLATFORM] — 8 hits
- `condition_id` (3 times) — example L76: `condition_id = btc_market['conditionId']`
- `polymarket` (4 times) — example L31: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (1 times) — example L139: `order_args = OrderArgs(token_id=yes_token, price=deep_price, size=size, side='BUY')`

### `archive/hesoyam_with_fill_rate_limits/backtester/core/engine.py` [PLATFORM] — 8 hits
- `no_shares` (1 times) — example L136: `total_no=strategy.position.no_shares,`
- `total_no` (3 times) — example L28: `total_no: float`
- `total_yes` (3 times) — example L27: `total_yes: float`
- `yes_shares` (1 times) — example L135: `total_yes=strategy.position.yes_shares,`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/fillrate_logger.py` [PLATFORM] — 8 hits
- `no_shares` (4 times) — example L132: `no_shares = int(getattr(position, 'no_shares', 0))`
- `yes_shares` (4 times) — example L131: `yes_shares = int(getattr(position, 'yes_shares', 0))`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/core.py` [PLATFORM] — 8 hits
- `no_ask` (2 times) — example L48: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L47: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L46: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L45: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/log_reader.py` [PLATFORM] — 8 hits
- `token_id` (8 times) — example L66: `token_id = message[token_start:token_end].strip()`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/core.py` [PLATFORM] — 8 hits
- `no_ask` (2 times) — example L48: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L47: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L46: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L45: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/log_reader.py` [PLATFORM] — 8 hits
- `token_id` (8 times) — example L66: `token_id = message[token_start:token_end].strip()`

### `archive/hesoyam_with_fill_rate_limits/tbot_logger/ws_client.py` [PLATFORM] — 8 hits
- `condition_id` (3 times) — example L128: `async def subscribe_by_market(self, market_slug: str, condition_id: str, yes_token_id: str, no_token_id: str, callback):`
- `polymarket` (5 times) — example L14: `- Polymarket WS ignores "operation: subscribe" - tokens must be sent with type: MARKET`

### `backtester/core/engine.py` [PLATFORM] — 8 hits
- `no_shares` (1 times) — example L152: `total_no=strategy.position.no_shares,`
- `total_no` (3 times) — example L28: `total_no: float`
- `total_yes` (3 times) — example L27: `total_yes: float`
- `yes_shares` (1 times) — example L151: `total_yes=strategy.position.yes_shares,`

### `strategies/gabagool/fillrate_logger.py` [PLATFORM] — 8 hits
- `no_shares` (4 times) — example L132: `no_shares = int(getattr(position, 'no_shares', 0))`
- `yes_shares` (4 times) — example L131: `yes_shares = int(getattr(position, 'yes_shares', 0))`

### `tbot_core/strategy/core.py` [PLATFORM] — 8 hits
- `no_ask` (2 times) — example L48: `no_ask = self.no_book['asks'][0] if self.no_book['asks'] else None`
- `no_bid` (2 times) — example L47: `no_bid = self.no_book['bids'][0] if self.no_book['bids'] else None`
- `yes_ask` (2 times) — example L46: `yes_ask = self.yes_book['asks'][0] if self.yes_book['asks'] else None`
- `yes_bid` (2 times) — example L45: `yes_bid = self.yes_book['bids'][0] if self.yes_book['bids'] else None`

### `tbot_core/strategy/log_reader.py` [PLATFORM] — 8 hits
- `token_id` (8 times) — example L66: `token_id = message[token_start:token_end].strip()`

### `archive/dead_2026-03-04/test_api_methods.py` [PLATFORM] — 7 hits
- `polymarket` (2 times) — example L15: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137)`
- `token_id` (5 times) — example L37: `token_id = btc_markets[0]['tokens'][0]['token_id']`

### `archive/dead_2026-03-04/test_live_order_direct.py` [PLATFORM] — 7 hits
- `condition_id` (3 times) — example L45: `condition_id = state.get('condition_id')`
- `polymarket` (3 times) — example L27: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (1 times) — example L101: `order_args = OrderArgs(token_id=yes_token, price=deep_price, size=size, side='BUY')`

### `archive/dead_2026-03-04/test_live_order_v2.py` [PLATFORM] — 7 hits
- `polymarket` (2 times) — example L14: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (5 times) — example L44: `print('❌ Нет token_id в рынке')`

### `archive/dead_2026-03-04/test_single_order.py` [PLATFORM] — 7 hits
- `condition_id` (1 times) — example L37: `condition_id = btc_market['condition_id']`
- `polymarket` (2 times) — example L13: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (4 times) — example L39: `token_id = token_yes['token_id']`

### `archive/mag_knowledge/legacy/Well start here/poly_claim/bulk_redeem.py` [PLATFORM] — 7 hits
- `GNOSIS` (2 times) — example L3: `Polymarket Bulk Redeemer (Fixed for Gnosis Safe/MetaMask)`
- `condition_id` (3 times) — example L105: `for condition_id in unique_conditions:`
- `polymarket` (2 times) — example L3: `Polymarket Bulk Redeemer (Fixed for Gnosis Safe/MetaMask)`

### `archive/quarantine/polymarket_repos/py-clob-client/setup.py` [PLATFORM] — 7 hits
- `polymarket` (7 times) — example L9: `author="Polymarket Engineering",`

### `backtester/daemon/runner_v2.py` [PLATFORM] — 7 hits
- `no_shares` (1 times) — example L169: `no_shares=r.total_no,`
- `polymarket` (1 times) — example L22: `- ETH 5m рынков пока нет на Polymarket → --symbol eth для 5m бесполезен`
- `total_no` (2 times) — example L135: `'no': r.total_no,`
- `total_yes` (2 times) — example L134: `'yes': r.total_yes,`
- `yes_shares` (1 times) — example L168: `yes_shares=r.total_yes,`

### `scripts/Сканнеры SDK/get_truth.py` [PLATFORM] — 7 hits
- `polymarket` (3 times) — example L15: `gamma_url = f"https://gamma-api.polymarket.com/markets?slug={slug}"`
- `token_id` (4 times) — example L23: `token_id = m_data[0].get('clobTokenIds', [])[0]`

### `tbot_integration/core/parser.py` [PLATFORM] — 7 hits
- `pair_state` (5 times) — example L73: `r'\[PAIR_STATE\] (\w+)→(\w+) \| '`
- `yes_ask` (1 times) — example L166: `spread_at_intent: float  # [v3.3] yes_ask - yes_bid на момент создания`
- `yes_bid` (1 times) — example L166: `spread_at_intent: float  # [v3.3] yes_ask - yes_bid на момент создания`

### `api_xray.py` [PLATFORM] — 6 hits
- `polymarket` (6 times) — example L28: `print(f"🔬 POLYMARKET API X-RAY")`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/client.py` [PLATFORM] — 6 hits
- `polymarket` (3 times) — example L2: `Polymarket REST API Client`
- `token_id` (3 times) — example L358: `token_id: str,`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/engine.py` [PLATFORM] — 6 hits
- `no_shares` (1 times) — example L199: `'no_shares': position.no_shares,`
- `polymarket` (4 times) — example L61: `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- `yes_shares` (1 times) — example L198: `'yes_shares': position.yes_shares,`

### `archive/hesoyam_with_fill_rate_limits/backtester/daemon/runner_v2.py` [PLATFORM] — 6 hits
- `no_shares` (1 times) — example L136: `no_shares=r.total_no,`
- `total_no` (2 times) — example L102: `'no': r.total_no,`
- `total_yes` (2 times) — example L101: `'yes': r.total_yes,`
- `yes_shares` (1 times) — example L135: `yes_shares=r.total_yes,`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/order_logger.py` [PLATFORM] — 6 hits
- `condition_id` (4 times) — example L45: `condition_id: str           # Polymarket condition ID`
- `polymarket` (2 times) — example L45: `condition_id: str           # Polymarket condition ID`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/client.py` [PLATFORM] — 6 hits
- `polymarket` (3 times) — example L2: `Polymarket REST API Client`
- `token_id` (3 times) — example L359: `token_id: str,`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/engine.py` [PLATFORM] — 6 hits
- `no_shares` (1 times) — example L199: `'no_shares': position.no_shares,`
- `polymarket` (4 times) — example L61: `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- `yes_shares` (1 times) — example L198: `'yes_shares': position.yes_shares,`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/client.py` [PLATFORM] — 6 hits
- `polymarket` (3 times) — example L2: `Polymarket REST API Client`
- `token_id` (3 times) — example L358: `token_id: str,`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/engine.py` [PLATFORM] — 6 hits
- `no_shares` (1 times) — example L199: `'no_shares': position.no_shares,`
- `polymarket` (4 times) — example L61: `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- `yes_shares` (1 times) — example L198: `'yes_shares': position.yes_shares,`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_full_flow.py` [PLATFORM] — 6 hits
- `polymarket` (1 times) — example L75: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`
- `token_id` (5 times) — example L48: `TOKEN_ID = "34097058504275310827233323421517291090691602969494795225921954353603704046623"`

### `strategies/gabagool/order_logger.py` [PLATFORM] — 6 hits
- `condition_id` (4 times) — example L45: `condition_id: str           # Polymarket condition ID`
- `polymarket` (2 times) — example L45: `condition_id: str           # Polymarket condition ID`

### `tbot_core/api/client.py` [PLATFORM] — 6 hits
- `polymarket` (3 times) — example L2: `Polymarket REST API Client`
- `token_id` (3 times) — example L359: `token_id: str,`

### `tbot_core/engine.py` [PLATFORM] — 6 hits
- `no_shares` (1 times) — example L199: `'no_shares': position.no_shares,`
- `polymarket` (4 times) — example L61: `self.api_client = PolymarketClient(self.config.get('polymarket', {}))`
- `yes_shares` (1 times) — example L198: `'yes_shares': position.yes_shares,`

### `analysis/signals/alpha_signals.py` [PLATFORM] — 5 hits
- `pair_state` (5 times) — example L272: `[SIG_005] Если pair_state застрял в одном состоянии >85% времени — FSM не работает.`

### `archive/hesoyam_with_fill_rate_limits/scripts/safety_watchdog.py` [PLATFORM] — 5 hits
- `no_shares` (2 times) — example L111: `no = pos.get('no_shares', 0)`
- `polymarket` (1 times) — example L71: `c = ClobClient(host='https://clob.polymarket.com', chain_id=137, key=key, signature_type=0)`
- `yes_shares` (2 times) — example L110: `yes = pos.get('yes_shares', 0)`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_prices.py` [PLATFORM] — 5 hits
- `polymarket` (1 times) — example L6: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (4 times) — example L12: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `main.py` [PLATFORM] — 5 hits
- `polygon` (1 times) — example L403: `rpc_url = os.getenv('POLYGON_RPC_URL', 'https://polygon-bor-rpc.publicnode.com')`
- `polymarket` (4 times) — example L3: `TBOT - Polymarket Trading Bot`

### `scanner.py` [PLATFORM] — 5 hits
- `polymarket` (3 times) — example L29: `host="https://clob.polymarket.com",`
- `token_id` (2 times) — example L15: `TOKEN_ID = "49201965667491736410455005467661874386759195816250087757851011337285637695230"`

### `scripts/safety_watchdog.py` [PLATFORM] — 5 hits
- `no_shares` (2 times) — example L111: `no = pos.get('no_shares', 0)`
- `polymarket` (1 times) — example L71: `c = ClobClient(host='https://clob.polymarket.com', chain_id=137, key=key, signature_type=0)`
- `yes_shares` (2 times) — example L110: `yes = pos.get('yes_shares', 0)`

### `scripts/Сканнеры SDK/clob_truth.py` [PLATFORM] — 5 hits
- `polymarket` (1 times) — example L15: `host='https://clob.polymarket.com',`
- `token_id` (4 times) — example L9: `token_id = "54156619078768416591778078828753133997979141559000849301552898336814912101980"`

### `archive/dead_2026-03-04/stress_test_v6.py` [PLATFORM] — 4 hits
- `total_no` (2 times) — example L54: `total = r.total_yes + r.total_no`
- `total_yes` (2 times) — example L54: `total = r.total_yes + r.total_no`

### `archive/dead_2026-03-04/tbot_simulator/engine.py` [PLATFORM] — 4 hits
- `no_shares` (2 times) — example L81: `'no_shares': Decimal('0'),`
- `yes_shares` (2 times) — example L80: `'yes_shares': Decimal('0'),`

### `archive/hesoyam_with_fill_rate_limits/main.py` [PLATFORM] — 4 hits
- `polymarket` (4 times) — example L3: `TBOT - Polymarket Trading Bot`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/phase_manager.py` [PLATFORM] — 4 hits
- `no_shares` (2 times) — example L130: `position: Объект позиции с yes_shares, no_shares, avg prices`
- `yes_shares` (2 times) — example L130: `position: Объект позиции с yes_shares, no_shares, avg prices`

### `archive/hesoyam_with_fill_rate_limits/tbot_simulator/engine.py` [PLATFORM] — 4 hits
- `no_shares` (2 times) — example L81: `'no_shares': Decimal('0'),`
- `yes_shares` (2 times) — example L80: `'yes_shares': Decimal('0'),`

### `archive/mag_quarantine/lorine93s-analysis/src/config.py` [PLATFORM] — 4 hits
- `polygon` (1 times) — example L77: `rpc_url: str = Field(default="https://polygon-rpc.com", description="Polygon RPC endpoint")`
- `polymarket` (3 times) — example L17: `default="https://clob.polymarket.com", description="Polymarket CLOB API base URL"`

### `archive/mag_quarantine/lorine93s-analysis/src/main.py` [PLATFORM] — 4 hits
- `polymarket` (3 times) — example L16: `from src.polymarket.order_signer import OrderSigner`
- `token_id` (1 times) — example L150: `"token_id": quote.token_id,`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/place_builder_order.py` [PLATFORM] — 4 hits
- `polygon` (2 times) — example L6: `from py_clob_client.constants import POLYGON`
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L38: `token_id="104173557214744537570424345347209544585775842950109756851652855913015295701992",`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/clob_types.py` [PLATFORM] — 4 hits
- `token_id` (4 times) — example L41: `token_id: str`

### `backtester/daemon/runner_v3.py` [PLATFORM] — 4 hits
- `no_shares` (1 times) — example L180: `yes_shares=r.total_yes, no_shares=r.total_no,`
- `total_no` (1 times) — example L180: `yes_shares=r.total_yes, no_shares=r.total_no,`
- `total_yes` (1 times) — example L180: `yes_shares=r.total_yes, no_shares=r.total_no,`
- `yes_shares` (1 times) — example L180: `yes_shares=r.total_yes, no_shares=r.total_no,`

### `scripts/Сканнеры SDK/wiretap.py` [PLATFORM] — 4 hits
- `polymarket` (2 times) — example L22: `"https://clob.polymarket.com/sampling-simplified-markets",`
- `token_id` (2 times) — example L28: `match = re.search(r'"token_id":\s*"([^"]+)"', data_str)`

### `strategies/gabagool/phase_manager.py` [PLATFORM] — 4 hits
- `no_shares` (2 times) — example L130: `position: Объект позиции с yes_shares, no_shares, avg prices`
- `yes_shares` (2 times) — example L130: `position: Объект позиции с yes_shares, no_shares, avg prices`

### `analysis/cli.py` [PLATFORM] — 3 hits
- `pair_state` (3 times) — example L28: `3. Опционально: views (leaderboard / regime / toxic / edge / pair_state)`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/main.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L3: `TBOT - Polymarket Trading Bot`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/ws_user_client.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L2: `Polymarket User Channel WebSocket Client`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/market_api.py` [PLATFORM] — 3 hits
- `condition_id` (1 times) — example L46: `condition_id=market.get('conditionId'),`
- `polymarket` (2 times) — example L2: `Polymarket API interactions`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/ws_client.py` [PLATFORM] — 3 hits
- `condition_id` (2 times) — example L64: `async def subscribe_by_market(self, market_slug: str, condition_id: str, yes_token_id: str, no_token_id: str, callback):`
- `polymarket` (1 times) — example L35: `'Origin': 'https://polymarket.com',`

### `archive/dead_2026-03-04/market_api.py` [PLATFORM] — 3 hits
- `condition_id` (1 times) — example L46: `condition_id=market.get('conditionId'),`
- `polymarket` (2 times) — example L2: `Polymarket API interactions`

### `archive/dead_2026-03-04/test_order_fresh.py` [PLATFORM] — 3 hits
- `polymarket` (2 times) — example L13: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (1 times) — example L77: `order_args = OrderArgs(token_id=yes_token, price=deep_price, size=size, side='BUY')`

### `archive/dead_2026-03-04/test_order_simple.py` [PLATFORM] — 3 hits
- `polymarket` (2 times) — example L15: `client = ClobClient('https://clob.polymarket.com', key=key, chain_id=137, signature_type=0)`
- `token_id` (1 times) — example L76: `order_args = OrderArgs(token_id=yes_token, price=deep_price, size=size, side='BUY')`

### `archive/hesoyam_with_fill_rate_limits/dashboard/server.py` [PLATFORM] — 3 hits
- `condition_id` (1 times) — example L58: `condition_id: str = ""`
- `no_shares` (1 times) — example L46: `no_shares: float`
- `yes_shares` (1 times) — example L45: `yes_shares: float`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/ws_user_client.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L2: `Polymarket User Channel WebSocket Client`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/market_api.py` [PLATFORM] — 3 hits
- `condition_id` (1 times) — example L46: `condition_id=market.get('conditionId'),`
- `polymarket` (2 times) — example L2: `Polymarket API interactions`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/main.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L3: `TBOT - Polymarket Trading Bot`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/ws_user_client.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L2: `Polymarket User Channel WebSocket Client`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/market_api.py` [PLATFORM] — 3 hits
- `condition_id` (1 times) — example L46: `condition_id=market.get('conditionId'),`
- `polymarket` (2 times) — example L2: `Polymarket API interactions`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/ws_client.py` [PLATFORM] — 3 hits
- `condition_id` (2 times) — example L64: `async def subscribe_by_market(self, market_slug: str, condition_id: str, yes_token_id: str, no_token_id: str, callback):`
- `polymarket` (1 times) — example L35: `'Origin': 'https://polymarket.com',`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/strike_fetcher.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L2: `Strike Price Fetcher — gets openPrice (strike) for 15-min BTC markets from Polymarket API.`

### `archive/mag_quarantine/lorine93s-analysis/src/market_maker/quote_engine.py` [PLATFORM] — 3 hits
- `token_id` (3 times) — example L20: `token_id: str`

### `archive/mag_quarantine/lorine93s-analysis/src/polymarket/__init__.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L1: `from src.polymarket.order_signer import OrderSigner`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_balance_allowance.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L30: `token_id="52114319501245915516055106046884209969926127482827954674443846427813813222426",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_last_trades_prices.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L23: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563"`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_mid_markets_prices.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L26: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563"`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_orderbooks.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L6: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L12: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563"`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_spreads.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L6: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L12: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563"`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/orders.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L34: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/update_balance_allowance.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (2 times) — example L31: `token_id="52114319501245915516055106046884209969926127482827954674443846427813813222426",`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/rfq/rfq_types.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L2: `RFQ (Request for Quote) data types for the Polymarket CLOB API.`
- `token_id` (2 times) — example L26: `token_id: str`

### `scripts/merge_probe.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L37: `n_url = f"https://relayer-v2.polymarket.com/nonce?address={REAL_PROXY}&type=SAFE"`

### `scripts/Сканнеры SDK/check_token.py` [PLATFORM] — 3 hits
- `polymarket` (1 times) — example L10: `url = f"https://clob.polymarket.com/book?token_id={token_id}"`
- `token_id` (2 times) — example L6: `token_id = "54156619078768416591778078828753133997979141559000849301552898336814912101980"`

### `tbot_core/api/ws_user_client.py` [PLATFORM] — 3 hits
- `polymarket` (3 times) — example L2: `Polymarket User Channel WebSocket Client`

### `analysis/views/pair_state_view.py` [TRANSPORT] — 2 hits
- `pair_state` (2 times) — example L2: `views/pair_state_view.py — [v3.0] Анализ FSM pair_state.`

### `archive/dead_2026-03-04/backtester_daemon_runner.py` [PLATFORM] — 2 hits
- `total_no` (1 times) — example L85: `'no': r.total_no,`
- `total_yes` (1 times) — example L84: `'yes': r.total_yes,`

### `archive/dead_2026-03-04/backtester_scripts/run_backtest.py` [PLATFORM] — 2 hits
- `total_no` (1 times) — example L126: `'no': r.total_no,`
- `total_yes` (1 times) — example L125: `'yes': r.total_yes,`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/market_api.py` [TRANSPORT] — 2 hits
- `condition_id` (1 times) — example L64: `'condition_id': market.get('conditionId'),`
- `polymarket` (1 times) — example L2: `Polymarket REST API client`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/fills_handler.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L78: `elif fill.side == 'NO' and position.no_shares > 0 and not fill.aggressor:`
- `yes_shares` (1 times) — example L74: `if fill.side == 'YES' and position.yes_shares > 0 and not fill.aggressor:`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/execution/manager.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L2: `Order Manager - handles all order operations with Polymarket CLOB`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/strategy/optimizer.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L70: `current_no = float(current_position.get('no_shares', 0))`
- `yes_shares` (1 times) — example L69: `current_yes = float(current_position.get('yes_shares', 0))`

### `archive/dead_2026-03-04/tbot_core_execution/fills_handler.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L78: `elif fill.side == 'NO' and position.no_shares > 0 and not fill.aggressor:`
- `yes_shares` (1 times) — example L74: `if fill.side == 'YES' and position.yes_shares > 0 and not fill.aggressor:`

### `archive/dead_2026-03-04/tbot_core_execution/manager.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L2: `Order Manager - handles all order operations with Polymarket CLOB`

### `archive/hesoyam_with_fill_rate_limits/backtester/daemon/runner.py` [PLATFORM] — 2 hits
- `total_no` (1 times) — example L85: `'no': r.total_no,`
- `total_yes` (1 times) — example L84: `'yes': r.total_yes,`

### `archive/hesoyam_with_fill_rate_limits/backtester/scripts/run_backtest.py` [PLATFORM] — 2 hits
- `total_no` (1 times) — example L126: `'no': r.total_no,`
- `total_yes` (1 times) — example L125: `'yes': r.total_yes,`

### `archive/hesoyam_with_fill_rate_limits/strategies/gabagool/execution_engine.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L713: `self.no_shares = Decimal('100')`
- `yes_shares` (1 times) — example L712: `self.yes_shares = Decimal('100')`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/market_api.py` [TRANSPORT] — 2 hits
- `condition_id` (1 times) — example L64: `'condition_id': market.get('conditionId'),`
- `polymarket` (1 times) — example L2: `Polymarket REST API client`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/fills_handler.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L78: `elif fill.side == 'NO' and position.no_shares > 0 and not fill.aggressor:`
- `yes_shares` (1 times) — example L74: `if fill.side == 'YES' and position.yes_shares > 0 and not fill.aggressor:`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/execution/manager.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L2: `Order Manager - handles all order operations with Polymarket CLOB`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/strategy/optimizer.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L70: `current_no = float(current_position.get('no_shares', 0))`
- `yes_shares` (1 times) — example L69: `current_yes = float(current_position.get('yes_shares', 0))`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/market_api.py` [TRANSPORT] — 2 hits
- `condition_id` (1 times) — example L64: `'condition_id': market.get('conditionId'),`
- `polymarket` (1 times) — example L2: `Polymarket REST API client`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/fills_handler.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L78: `elif fill.side == 'NO' and position.no_shares > 0 and not fill.aggressor:`
- `yes_shares` (1 times) — example L74: `if fill.side == 'YES' and position.yes_shares > 0 and not fill.aggressor:`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/execution/manager.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L2: `Order Manager - handles all order operations with Polymarket CLOB`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/strategy/optimizer.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L70: `current_no = float(current_position.get('no_shares', 0))`
- `yes_shares` (1 times) — example L69: `current_yes = float(current_position.get('yes_shares', 0))`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/GTD_order.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L30: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_market_trades_events.py` [PLATFORM] — 2 hits
- `condition_id` (1 times) — example L22: `print(client.get_market_trades_events("condition_id"))`
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_markets.py` [PLATFORM] — 2 hits
- `condition_id` (1 times) — example L26: `print(client.get_market("condition_id"))`
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/market_buy_order.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L26: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/market_sell_order.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L26: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/order.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L30: `token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/post_only_order.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`
- `token_id` (1 times) — example L28: `token_id="102200530570339469387764365697342150521708074903735836831685780223982723092914",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_create_quote.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`
- `token_id` (1 times) — example L27: `token_id="34097058504275310827233323421517291090691602969494795225921954353603704046623",`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_create_request.py` [PLATFORM] — 2 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`
- `token_id` (1 times) — example L26: `token_id="34097058504275310827233323421517291090691602969494795225921954353603704046623",`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/http_helpers/helpers.py` [PLATFORM] — 2 hits
- `token_id` (2 times) — example L187: `if params.token_id:`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/order_builder/builder.py` [PLATFORM] — 2 hits
- `token_id` (2 times) — example L135: `tokenId=order_args.token_id,`

### `data_gateway.py` [TRANSPORT] — 2 hits
- `condition_id` (1 times) — example L145: `"slug": mkt.get("slug"), "condition_id": mkt.get("condition_id"),`
- `polymarket` (1 times) — example L6: `1. PolyOrderbookSwarm  (10 WebSocket connections to Polymarket)`

### `merge_probe.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L45: `client = RelayClient("https://relayer-v2.polymarket.com", 137, PK, b_config)`

### `scripts/Сканнеры SDK/autopsy_engine_v2.py` [TRANSPORT] — 2 hits
- `polymarket` (1 times) — example L23: `client = ClobClient('https://clob.polymarket.com', 137, pk, 1, proxy_checksum)`
- `token_id` (1 times) — example L46: `token_id=test_token,`

### `scripts/Сканнеры SDK/check_auth.py` [TRANSPORT] — 2 hits
- `polymarket` (2 times) — example L18: `host='https://clob.polymarket.com',`

### `strategies/gabagool/as_pricer.py` [PLATFORM] — 2 hits
- `no_shares` (1 times) — example L80: `q:       Inventory skew (yes_shares - no_shares), signed.`
- `yes_shares` (1 times) — example L80: `q:       Inventory skew (yes_shares - no_shares), signed.`

### `strategies/gabagool/execution_engine.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L713: `self.no_shares = Decimal('100')`
- `yes_shares` (1 times) — example L712: `self.yes_shares = Decimal('100')`

### `strategies/gabagool/grid_manager.py` [PLATFORM] — 2 hits
- `yes_ask` (1 times) — example L49: `spread_at_creation: float = 0.0  # [v3.3] yes_ask - yes_bid на момент создания (рыночные условия)`
- `yes_bid` (1 times) — example L49: `spread_at_creation: float = 0.0  # [v3.3] yes_ask - yes_bid на момент создания (рыночные условия)`

### `tbot_core/api/market_api.py` [TRANSPORT] — 2 hits
- `condition_id` (1 times) — example L64: `'condition_id': market.get('conditionId'),`
- `polymarket` (1 times) — example L2: `Polymarket REST API client`

### `tbot_core/strategy/optimizer.py` [TRANSPORT] — 2 hits
- `no_shares` (1 times) — example L70: `current_no = float(current_position.get('no_shares', 0))`
- `yes_shares` (1 times) — example L69: `current_yes = float(current_position.get('yes_shares', 0))`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Polymarket trading bot logger package."""`

### `archive/dead_2026-03-04/backup_2026-02-07_1726/tbot_core/api/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket API clients`

### `archive/dead_2026-03-04/polymarket/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket Integration Module`

### `archive/dead_2026-03-04/polymarket/order_tracker.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L74: `client: Polymarket API client`

### `archive/dead_2026-03-04/run_logger.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L34: `parser = argparse.ArgumentParser(description='Standalone Polymarket market data logger')`

### `archive/hesoyam_with_fill_rate_limits/backtester/configs/test_configs.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L24: `Key insight from Gabagool (top Polymarket trader):`

### `archive/hesoyam_with_fill_rate_limits/polymarket/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket Integration Module`

### `archive/hesoyam_with_fill_rate_limits/polymarket/order_tracker.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L74: `client: Polymarket API client`

### `archive/hesoyam_with_fill_rate_limits/tbot_core/api/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket API clients`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Polymarket trading bot logger package."""`

### `archive/hesoyam_with_fill_rate_limits/tbot_integration/backup_2026-02-07_1726/tbot_core/api/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket API clients`

### `archive/hesoyam_with_fill_rate_limits/tbot_logger/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Polymarket trading bot logger package."""`

### `archive/mag_quarantine/lorine93s-analysis/src/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Polymarket CLOB market-making bot with optimized inventory management and spread farming."""`

### `archive/mag_quarantine/lorine93s-analysis/src/execution/order_executor.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L11: `from src.polymarket.order_signer import OrderSigner`

### `archive/mag_quarantine/lorine93s-analysis/src/utils/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Utility functions for Polymarket market maker bot."""`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/are_orders_scoring.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/cancel_all.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/cancel_market_orders.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/cancel_order.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/cancel_orders.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/create_api_key.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L11: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/create_readonly_api_key.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/delete_readonly_api_key.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/derive_api_key.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L11: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/drop_notifications.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_api_keys.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_builder_trades.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L16: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_closed_only_mode.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_last_trade_price.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_mid_market_price.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_notifications.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_ok.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L5: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_open_orders_with_readonly_key.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_order.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_orderbook.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L9: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_orders.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_price.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L6: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_readonly_api_keys.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_server_time.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L5: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_spread.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/get_trades.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/is_order_scoring.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/post_heartbeat.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L15: `host = os.getenv("CLOB_API_URL", "https://clob.polymarket.com")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_accept_quote.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_approve_order.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L14: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_cancel_quote.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_cancel_request.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_config.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L12: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_get_best_quote.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_get_quotes.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/examples/rfq_get_requests.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L13: `host = os.getenv("CLOB_API_URL", "https://clob-staging.polymarket.com/")`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/constants.py` [PLATFORM] — 1 hits
- `polygon` (1 times) — example L24: `POLYGON = 137`

### `archive/quarantine/polymarket_repos/py-clob-client/py_clob_client/rfq/rfq_helpers.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `RFQ helper functions for the Polymarket CLOB API.`

### `backtester/configs/test_configs.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L24: `Key insight from Gabagool (top Polymarket trader):`

### `claim_probe.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L43: `client = RelayClient("https://relayer-v2.polymarket.com", 137, PK, b_config)`

### `dashboard/microstructure/calculator.py` [TRANSPORT] — 1 hits
- `condition_id` (1 times) — example L280: `market_id: condition_id from orderbook_snapshots`

### `run_logger.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L34: `parser = argparse.ArgumentParser(description='Standalone Polymarket market data logger')`

### `scripts/Сканнеры SDK/check_market_precision.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L8: `url = f"https://gamma-api.polymarket.com/markets?slug={slug}"`

### `scripts/Сканнеры SDK/nuclear_scanner.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L17: `client = ClobClient('https://clob.polymarket.com', 137, pk, 1, proxy)`

### `scripts/Сканнеры SDK/scan_sdk.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L10: `client = ClobClient(host='https://clob.polymarket.com', key=dummy_key, chain_id=137, signature_type=2)`

### `strategies/gabagool/vpin.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L8: `Context: On Polymarket BTC 5m/15m, "informed trading" = herd of arb bots`

### `tbot_core/api/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L2: `Polymarket API clients`

### `tbot_integration/core/epoch_tracker.py` [PLATFORM] — 1 hits
- `pair_state` (1 times) — example L37: `pair_states: list[str] = field(default_factory=list)  # состояния pair_state`

### `tbot_integration/strike_fetcher.py` [TRANSPORT] — 1 hits
- `polymarket` (1 times) — example L10: `STRIKE_API_URL = "https://polymarket.com/api/crypto/crypto-price"`

### `tbot_logger/__init__.py` [PLATFORM] — 1 hits
- `polymarket` (1 times) — example L1: `"""Polymarket trading bot logger package."""`

### `tbot_logger/poly_orderbook_swarm.py` [TRANSPORT] — 1 hits
- `condition_id` (1 times) — example L198: `async def subscribe_by_market(self, slug, condition_id, yes_id, no_id, callback):`
