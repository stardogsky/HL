"""
Simple Market Making Strategy — GLFT-style minimal implementation.

Created: 2026-05-05
Purpose: Architectural ablation test — strip ~95% of GridStrategy complexity to
test whether current guard layers are net-positive in low-vol environment (5x volume drop).

Architecture:
  on_tick = read_state → oracle_fv → volatility → reservation_price → half_spread → grid_manager.sync()
  
  Total: ~6 methods vs 27 in GridStrategy.
  Total: ~400 lines vs ~7029 in grid_strategy.py.

Removed (vs GridStrategy):
  - DualCoreDefense (CVD Skew + Veto)
  - Auto-Armor stress system + 9 downstream consumers
  - Intent Mode FSM (OPTIMIZE_PRICE/BALANCED/RESTORE_BALANCE)
  - Healer + MUTEX Hunter/Healer + Toxic Recovery Protocol
  - Elastic Gravity (per-leg penalties via risk_weight_power)
  - Spread_and_Shield (multi-layer Shield/Crossfire)
  - Hard Veto + Forensic Telemetry
  - Triage logic, emergency dump, churn guard, smart GC adaptive
  - Pre-Filter Projection Check, ANTI_SNIPE_COOLDOWN, BURST_PROTECT
  - Oracle Sigmoid blending (replaced with simple weighted average)

Kept (verbatim from GridStrategy infrastructure):
  - PositionState (apply_ctf_merge, in_flight tracking, shadow accounting)
  - GridManager.sync() with conservative settings (1 level only)
  - OracleEngine.calculate_fv()  
  - Directional Cold Start Filter v3.4.1 (DCS_KILL)
  - BBO clamp, MAQ filter, profit gate (simplified)

Mock attributes (for bridge/adapter compatibility):
  - _market_regime: always "NEUTRAL"
  - _intent_mode: always "SIMPLE"  
  - _pair_state: always "BALANCED"
  - These are set static so attribution layer in PendingOrder still works
    (analysis.cli will see RegAtIntent:NEUTRAL × IMAtIntent:SIMPLE for simple bot trades)

Config:
  - Reuses GridConfig dataclass (no new SimpleConfig needed)
  - GLFT-specific params: glft_gamma, glft_k_depth, glft_b_risk, glft_vol_window_sec
    → if absent in YAML, defaults below kick in
"""

from __future__ import annotations
import math
import time
import logging
from collections import deque
from typing import Any, Optional
from dataclasses import is_dataclass, asdict
import json

from strategies.gabagool.grid_strategy import GridConfig, PositionState, TickTelemetry
from strategies.gabagool.grid_manager import GridManager, OrderAction, TICK_SIZE
from strategies.gabagool.oracle_engine import OracleEngine

logger = logging.getLogger('gabalog.simple_strategy')


# ============================================================================
# DEFAULTS for GLFT-specific config (read from GridConfig with getattr fallback)
# ============================================================================

# Risk aversion γ — controls inventory penalty curve.
# Higher γ → wider spread when q != 0 (more risk-averse).
# Reference: Avellaneda-Stoikov (2008), Guéant-Lehalle-Fernandez-Tapia (2013).
GLFT_GAMMA_DEFAULT = 0.5

# Order book depth proxy k — for binary contracts on Polymarket = 1.0 (single tick).
# Larger k → tighter spread (more competition).
GLFT_K_DEPTH_DEFAULT = 1.0

# Inventory skew coefficient B — cents shifted in reservation per share of imbalance.
# B = 0.0005 → 100 shares imbalance shifts reservation by 5 cents.
# Tunable per bot for hypothesis testing.
GLFT_B_RISK_DEFAULT = 0.0005

# Volatility window — seconds of BTC price history used for σ estimate.
# Polymarket BTC 15m markets have ~900s lifetime. 30s window = 3.3% lookback,
# enough to capture intra-tick volatility without lag.
GLFT_VOL_WINDOW_SEC_DEFAULT = 30.0


class SimpleStrategy:
    """
    GLFT-style market maker for Polymarket binary BTC 15m.
    
    Designed to be a clean baseline for comparing against complex GridStrategy.
    """

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    def __init__(self, config: GridConfig | None = None):
        self.config = config or GridConfig()

        # ---- Dump config for debugging (mirrors GridStrategy convention) ----
        try:
            if is_dataclass(self.config):
                cfg_dict = asdict(self.config)
            else:
                cfg_dict = vars(self.config)
            logger.info(
                f"🚨 [SIMPLE_CONFIG_DUMP] Config in memory:\n"
                f"{json.dumps(cfg_dict, indent=2, default=str)}"
            )
        except Exception as e:
            logger.info(f"[SIMPLE_CONFIG_DUMP] Dump failed: {e}")

        # ---- Core state (real, used by SimpleStrategy logic) ----
        self.position = PositionState()
        self.oracle_engine = OracleEngine()
        self.oracle_engine.config = self.config
        self.engine = None  # ExecutionEngineV6 — set externally by GridAdapter

        # GridManager with CONSERVATIVE settings (single level, no asymmetry).
        # This minimizes interference from GridManager's own complex logic
        # (asymmetric spacing, L1+ multipliers, hunter weak_leg boost).
        self.grid_manager = GridManager(
            grid_levels=1,                    # ONLY L0 — no L1+ depth
            grid_spacing_ticks=1,             # ignored (only 1 level)
            grid_lot_size=self.config.grid_lot_size,
            grid_lot_decay=1.0,
            stale_threshold_ticks=2,          # symmetric retreat tolerance
            chase_threshold_ticks=2,          # symmetric chase tolerance
            deep_level_static=False,          # irrelevant (1 level)
            event_callback=self._emit_event,
            spacing_asym_multiplier=0.0,      # disable asymmetric spacing
            config=self.config,
        )
        self.grid_manager.fill_cooldown_sec = self.config.fill_cooldown_sec

        # ---- GLFT parameters (read from config with sensible defaults) ----
        self.GLFT_GAMMA = getattr(self.config, 'glft_gamma', GLFT_GAMMA_DEFAULT)
        self.GLFT_K_DEPTH = getattr(self.config, 'glft_k_depth', GLFT_K_DEPTH_DEFAULT)
        self.GLFT_B_RISK = getattr(self.config, 'glft_b_risk', GLFT_B_RISK_DEFAULT)
        self.GLFT_VOL_WINDOW_SEC = getattr(
            self.config, 'glft_vol_window_sec', GLFT_VOL_WINDOW_SEC_DEFAULT
        )

        # ---- BTC price history for volatility computation ----
        # ~120 samples = 30s @ ~0.25s tick rate (oversized buffer is cheap)
        self._btc_price_history: deque = deque(maxlen=120)
        self._last_btc_price = 0.0
        self._last_btc_ts = 0.0

        # ---- Live state buffers (consumed by bridge for live_state_*.json) ----
        self._order_events: deque = deque(maxlen=500)
        self._market_tape_log: list = []  # bridge fallback for resolve

        # ---- Cached orderbook (one side per message → need both halves) ----
        self._last_orderbook: dict = {}

        # ---- Strike & market identity ----
        self._strike_price: Optional[float] = None
        self._is_official_strike = False
        self._c_mkt: Optional[str] = None
        self.paper_winner: Optional[str] = None

        # ---- Risk state ----
        self._session_pnl = 0.0
        self._session_peak_pnl = 0.0
        self._drawdown_stopped = False

        # ---- API request counter (bridge expects this method) ----
        self._api_requests_total = 0

        # ---- Cached current FV for telemetry ----
        self.current_fv = 0.5

        # ---- Telemetry (lightweight) ----
        self.last_telemetry = TickTelemetry()
        self.last_telemetry_pulse = {}

        # ====================================================================
        # MOCK ATTRIBUTES — required by bridge/adapter for compatibility.
        # These never change (static values). Their purpose is to prevent
        # AttributeError in bridge.py / grid_adapter.py code paths that read
        # GridStrategy state for telemetry, attribution, or logging.
        # 
        # NOT used in simple bot's own decision logic.
        # ====================================================================
        
        # CVD machinery (read by adapter for register_order attribution)
        self._market_regime = 'NEUTRAL'
        self._cvd_signal_last = 0.0
        self._cvd_toxic_streak = 0
        self._cvd_veto_active = False
        self._cvd_veto_ts = 0.0
        self._cvd_fast_signal = 0.0
        self._cvd_slow_signal = None
        self._defense_state = {'action': 'NORMAL', 'price_skew_cents': 0.0}
        self._regime_entered_ts = time.time()

        # Intent mode FSM (read by adapter for attribution)
        self._intent_mode = 'SIMPLE'
        self._intent_load = 0.0
        self._is_flow_toxic = False
        self._is_falling_knife = False

        # Pair state FSM
        self._pair_state = 'BALANCED'

        # Stress/Auto-Armor outputs (read by adapter for register_order)
        self._smooth_stress = 0.0
        self._unified_stress_level = 0.0
        self._current_stress_multiplier = 1.0
        self._is_panic_frozen = False
        self._is_at_dead_pole = False
        self._is_healing_state = False
        self._is_blind = False

        # Dynamic limits (read by other modules — kept static here)
        self._dynamic_hard_cutoff = self.config.hard_cutoff_max
        self._dynamic_hunter_thr = self.config.hunter_imb_threshold
        self._dynamic_inventory_scale = self.config.inventory_scale_shares
        self._dynamic_avg_tranche_max_size = self.config.avg_tranche_max_size

        # Counters
        self._fills_this_tick = 0
        self._pre_pull_ticks_left = 0
        self._total_fills = 0
        self._total_cancels = 0
        self._toxic_position_ticks = 0
        self._bankrupt_sides = set()
        self._consensus_confirmed = False

        # Edge cache (read by bridge for logs)
        self.last_effective_scale = self.config.inventory_scale_shares
        self.last_adaptive_edge = self.config.target_edge

        # FV tracking (read by adapter)
        self._last_fv_for_cvd = 0.5

        # Recycling state (read by adapter)
        self._recycling_sell_active = False
        self._emergency_dump_fired = False
        self._last_dump_ts = 0.0

        # Trust state
        self._current_oracle_weight = 1.0
        self._oracle_trust_state = 'NORMAL'

        # ---- Decision deduplication for log throttling ----
        self._last_decision_log_ts = 0.0
        self._last_decision = 'NORMAL'

        logger.info(
            f"🟢 [SIMPLE_STRATEGY] Initialized | "
            f"GLFT γ={self.GLFT_GAMMA} k={self.GLFT_K_DEPTH} "
            f"B={self.GLFT_B_RISK} vol_win={self.GLFT_VOL_WINDOW_SEC}s | "
            f"deposit=${self.config.deposit}"
        )

    # ========================================================================
    # ON_TICK — main loop (replaces 27-method on_tick of GridStrategy)
    # ========================================================================

    def on_tick(self, market_data: dict) -> list[OrderAction]:
        """
        Single-pass GLFT market making.

        Pipeline:
          1. Sensor & safety gates (time, blind, wide_spread, drawdown)
          2. Extract BBO + cache
          3. Update BTC price history (for σ)
          4. Oracle FV + trust check
          5. Compute σ from BTC velocity
          6. GLFT half_spread = γσ² + (2/γ)ln(1 + γ/k)
          7. Reservation price = fv - B*q
          8. Symmetric quotes
          9. BBO clamp
          10. Profit gate hard cap
          11. MAQ floor
          12. Cold start guard (DCS_KILL)
          13. Inventory hard cap & hedge mode
          14. Build target via grid_manager.calculate_target_grid
          15. Sync via grid_manager.sync
          16. Update telemetry
        """
        actions: list[OrderAction] = []

        # ----------------------------------------------------------------
        # STEP 1: Safety gates
        # ----------------------------------------------------------------
        time_rem_sec = float(market_data.get('time_remaining_sec', 900))
        self._last_time_remaining_sec = time_rem_sec
        
        # Sync market slug from per-tick data (on_market_switch may be called without slug)
        slug_from_tick = market_data.get('slug') or market_data.get('condition_id')
        if slug_from_tick and slug_from_tick != self._c_mkt:
            self._c_mkt = slug_from_tick
        is_blind = False  # adapter does not pass this; bridge handles via watchdog
        safe_mode = False
        merge_in_progress = bool(market_data.get('merge_in_progress', False))

        # Market not yet started OR market expired buffer
        if time_rem_sec > self.config.market_duration_sec:
            return []

        if time_rem_sec <= self.config.end_market_buffer_sec:
            return self._cancel_all('END_OF_MARKET')

        if is_blind or safe_mode:
            return self._cancel_all('BLIND_OR_SAFE_MODE')

        if merge_in_progress:
            return []  # bridge is mid-CTF-merge; do nothing

        if self._drawdown_stopped:
            return []

        # ----------------------------------------------------------------
        # STEP 2: Extract BBO from message (one side at a time)
        # ----------------------------------------------------------------
        yes_bid, yes_ask, no_bid, no_ask = self._extract_bbo(market_data)

        # Need both sides before quoting
        if yes_bid <= 0 or no_bid <= 0:
            return []

        # Wide market spread halt
        yes_market_spread = yes_ask - yes_bid if yes_ask > 0 else 1.0
        if yes_market_spread > self.config.max_market_spread:
            return self._cancel_all(f'WIDE_MARKET_SPREAD={yes_market_spread:.3f}')

        # ----------------------------------------------------------------
        # STEP 3: Update BTC price history (for volatility computation)
        # ----------------------------------------------------------------
        btc_price = self._get_btc_price(market_data)
        now = time.time()
        if btc_price > 100 and (now - self._last_btc_ts > 0.2):
            self._btc_price_history.append((now, btc_price))
            self._last_btc_price = btc_price
            self._last_btc_ts = now

        # ----------------------------------------------------------------
        # STEP 4: Oracle FV + Trust check (replaces Oracle Pipeline)
        # ----------------------------------------------------------------
        strike = self._get_strike(market_data)
        if strike:
            self._strike_price = strike

        vol_ratio = float(market_data.get('vol_ratio', 1.0))
        btc_delta = float(market_data.get('btc_delta', 0.0))

        mid_market = self._compute_mid_market(yes_bid, yes_ask, no_bid, no_ask)

        oracle_fv: Optional[float] = None
        if btc_price > 100 and strike and strike > 100:
            try:
                oracle_fv = self.oracle_engine.calculate_fv(
                    current_btc=btc_price,
                    strike=strike,
                    time_left_sec=time_rem_sec,
                    total_duration=self.config.market_duration_sec,
                    vol_ratio=vol_ratio,
                    btc_momentum=btc_delta,
                    p_mkt=mid_market,
                    vpin=0.5,  # SIMPLE bot: no VPIN tracking
                )
            except Exception as e:
                logger.debug(f"[SIMPLE] Oracle calc_fv failed: {e}")
                oracle_fv = None

        # Trust check — if oracle disagrees with market by > 10c, freeze.
        # This replaces OracleSigmoidBlending + BlindnessVeto.
        if oracle_fv is None:
            # Oracle not ready (no strike, BTC stale). Use mid_market only.
            fv = mid_market
        else:
            oracle_diff = abs(oracle_fv - mid_market)
            if oracle_diff > 0.10:
                return self._cancel_all(
                    f'ORACLE_TRUST_COLLAPSE diff={oracle_diff:.3f} '
                    f'oracle={oracle_fv:.3f} mid={mid_market:.3f}'
                )
            # Simple weighted blend (replaces sigmoid Kalman fusion)
            fv = 0.7 * oracle_fv + 0.3 * mid_market

        self.current_fv = fv
        self._last_fv_for_cvd = fv  # mock for adapter

        # ----------------------------------------------------------------
        # STEP 5: Volatility (replaces Auto-Armor stress system)
        # ----------------------------------------------------------------
        sigma = self._compute_volatility()  # relative volatility (e.g. 0.001 = 0.1%)

        # ----------------------------------------------------------------
        # STEP 6: GLFT half-spread
        # 
        # half_spread = γσ² + (2/γ) * ln(1 + γ/k)
        # 
        # First term: penalty for adverse selection (scales with vol²)
        # Second term: optimal spread under exponential order arrival (k=intensity)
        # ----------------------------------------------------------------
        glft_term = (
            self.GLFT_GAMMA * sigma * sigma
            + (2.0 / self.GLFT_GAMMA) * math.log(1.0 + self.GLFT_GAMMA / self.GLFT_K_DEPTH)
        )
        half_spread = max(self.config.edge_min, min(self.config.edge_max, glft_term))

        # ----------------------------------------------------------------
        # STEP 7: Reservation price — full GLFT with time + σ adaptive
        # 
        # Classical AS: r = s - q*γ*σ²*(T-t)
        # Our extension: σ-adaptive time exponent (sqrt at high vol, linear at low)
        # ----------------------------------------------------------------
        q_imbalance = self.position.q
        
        # Time factor — gradient decay over market lifetime
        T_norm = max(0.0, min(1.0, time_rem_sec / self.config.market_duration_sec))
        # σ_norm: relative vol normalized to typical 0.001 (0.1%)
        sigma_norm = min(1.0, sigma / 0.001)
        # time_exp: 1.0 (linear) at low vol, 0.5 (sqrt) at high vol
        # Smooth gradient — no thresholds
        time_exp = 1.0 - 0.5 * sigma_norm
        time_factor = T_norm ** time_exp
        
        # Pair-state pressure — gradient amplifier when tail is overpaid
        # When inv_ps > 1.00, skew becomes more aggressive to rebalance via pricing
        # (light-side bid raised, heavy-side bid lowered — pure pricing, no sells)
        ya = (self.position.yes_cost / self.position.total_yes) if self.position.total_yes > 0 else 0.0
        na = (self.position.no_cost / self.position.total_no) if self.position.total_no > 0 else 0.0
        inv_ps = ya + na if (ya > 0 and na > 0) else 1.0
        overpay = max(0.0, inv_ps - 1.00)
        ps_pressure = 1.0 + overpay * 30.0  # 1.0 (fair) → 4.0 (10c overpay)
        
        # Inventory skew — uses time_factor + ps_pressure on classical AS form
        inventory_skew = self.GLFT_B_RISK * q_imbalance * (1.0 + 2.0 * time_factor) * ps_pressure
        
        reservation = fv - inventory_skew
        reservation = max(0.05, min(0.95, reservation))
        
        # Cache for telemetry
        self._last_time_factor = time_factor
        self._last_sigma_norm = sigma_norm
        self._last_inv_ps = inv_ps
        self._last_ps_pressure = ps_pressure

        # ----------------------------------------------------------------
        # STEP 8: Symmetric quotes (NO asymmetric multipliers!)
        # YES bid below reservation, NO bid below (1 - reservation)
        # ----------------------------------------------------------------
        l0_yes_price = reservation - half_spread
        l0_no_price = (1.0 - reservation) - half_spread

        # ----------------------------------------------------------------
        # STEP 9: BBO clamp (prevent self-arbitrage on existing asks)
        # ----------------------------------------------------------------
        if yes_ask > 0:
            l0_yes_price = min(l0_yes_price, yes_ask - TICK_SIZE)
        if no_ask > 0:
            l0_no_price = min(l0_no_price, no_ask - TICK_SIZE)

        # Clamp to valid token price range [0.01, 0.99]
        l0_yes_price = max(0.01, min(0.99, l0_yes_price))
        l0_no_price = max(0.01, min(0.99, l0_no_price))

        # Round to tick size
        l0_yes_price = round(l0_yes_price, 2)
        l0_no_price = round(l0_no_price, 2)

        # ----------------------------------------------------------------
        # STEP 10: Profit gate (single hard cap, no Hunter override)
        # ----------------------------------------------------------------
        pair_cost = l0_yes_price + l0_no_price
        if pair_cost > self.config.abs_max_pair_cost:  # default 1.02
            # Reduce the more expensive side to fit cap
            overflow = pair_cost - self.config.abs_max_pair_cost
            if l0_yes_price >= l0_no_price:
                l0_yes_price = round(l0_yes_price - overflow - TICK_SIZE, 2)
                l0_yes_price = max(0.01, l0_yes_price)
            else:
                l0_no_price = round(l0_no_price - overflow - TICK_SIZE, 2)
                l0_no_price = max(0.01, l0_no_price)

        # ----------------------------------------------------------------
        # STEP 10b: Projected pair cost — gradient lot scaling (NEW)
        # 
        # Hard gate at abs_max_pair_cost=1.02 too coarse — we soft-scale lot size
        # based on projected pair cost. Gradient on lot, not on price.
        # 
        # pair_cost ≤ 0.98 → lot boost (cheap pair, take more)
        # pair_cost in (0.98, 1.00) → full size
        # pair_cost in (1.00, 1.02) → gradient decline
        # pair_cost > 1.02 → blocked by hard gate above
        # ----------------------------------------------------------------
        projected_pair_cost = l0_yes_price + l0_no_price
        if projected_pair_cost <= 0.98:
            # Underpay zone — boost lot up to +10%
            lot_scale = 1.0 + min(0.10, (0.98 - projected_pair_cost) * 5.0)
        elif projected_pair_cost <= 1.00:
            # Fair zone — full size
            lot_scale = 1.0
        elif projected_pair_cost <= 1.02:
            # Overpay zone — gradient decline
            overpay = projected_pair_cost - 1.00
            lot_scale = max(0.20, 1.0 - overpay * 40.0)
        else:
            lot_scale = 0.0  # belt-and-suspenders (hard gate already triggered)
        
        self._last_projected_pair_cost = projected_pair_cost
        self._last_lot_scale = lot_scale

        # ----------------------------------------------------------------
        # STEP 11: MAQ floor (minimum profitable quote)
        # ----------------------------------------------------------------
        yes_blocked = False
        no_blocked = False

        maq_floor = float(getattr(self.config, 'MAQ_BASE', 0.003))
        if l0_yes_price < maq_floor:
            yes_blocked = True
        if l0_no_price < maq_floor:
            no_blocked = True

        # ----------------------------------------------------------------
        # STEP 12: Cold start guard (Directional Cold Start Filter v3.4.1)
        # 
        # If completely cold (Q=0 AND total_y=0 AND total_n=0):
        #   - FV in upper crust: kill YES opening (don't buy expensive)
        #   - FV in lower crust: kill NO opening
        #   - Neutral FV: both allowed (simple bot is conservative here;
        #     extension to regime+CVD branch is left for future iteration
        #     since SIMPLE bot doesn't track CVD)
        # ----------------------------------------------------------------
        is_real_cold_start = (
            self.position.total_yes == 0
            and self.position.total_no == 0
            and self.position.q == 0
        )

        if is_real_cold_start:
            if fv > self.config.cold_start_fv_upper_thr:
                yes_blocked = True
                if self._should_log_decision('DCS_KILL_YES'):
                    logger.warning(f"🧊 [DCS_KILL_YES] FV={fv:.3f} > {self.config.cold_start_fv_upper_thr}")
            elif fv < self.config.cold_start_fv_lower_thr:
                no_blocked = True
                if self._should_log_decision('DCS_KILL_NO'):
                    logger.warning(f"🧊 [DCS_KILL_NO] FV={fv:.3f} < {self.config.cold_start_fv_lower_thr}")

        # ----------------------------------------------------------------
        # STEP 13: Inventory hard cap & hedge-only mode
        # ----------------------------------------------------------------
        abs_q = abs(q_imbalance)
        hard_cap = self.config.inventory_hard_cap
        hedge_thr = int(getattr(self.config, 'hedge_only_threshold', 0.70) * hard_cap)

        if abs_q > hedge_thr:
            # Hedge-only: kill the heavier side (force inventory reduction)
            if q_imbalance > 0:
                yes_blocked = True
            else:
                no_blocked = True
            if self._should_log_decision('HEDGE_ONLY'):
                logger.warning(f"🛡 [HEDGE_ONLY] |Q|={abs_q} > thr={hedge_thr}")

        # ----------------------------------------------------------------
        # STEP 14: weak_leg detection for GridManager hedge boost
        # ----------------------------------------------------------------
        weak_leg = ''
        imbalance_shares = 0
        is_desperate = False
        if abs_q > self.config.hunter_imb_threshold:
            weak_leg = 'NO' if q_imbalance > 0 else 'YES'
            imbalance_shares = abs_q
        if abs_q > hedge_thr:
            is_desperate = True

        # ----------------------------------------------------------------
        # STEP 15: Build target grid using REAL prices (no zeroing)
        # GridManager has internal `yes_price < 0.01: continue` which kills
        # BOTH sides if one is zero. We use post-filter on target list instead.
        # ----------------------------------------------------------------
        # STEP 16: Build target grid
        # ----------------------------------------------------------------
        budget_remaining = float(self.config.deposit) - self.position.active_total_cost
        if budget_remaining < 1.0:
            return self._cancel_all('NO_BUDGET')

        # Apply lot_scale to grid_manager before target calc
        # GridManager reads grid_lot_size_y / grid_lot_size_n attrs (continuous sizing)
        scaled_lot = max(5, int(self.config.grid_lot_size * lot_scale))  # min 5 (Polymarket platform req)
        self.grid_manager.grid_lot_size_y = scaled_lot
        self.grid_manager.grid_lot_size_n = scaled_lot
        
        target = self.grid_manager.calculate_target_grid(
            budget_remaining=budget_remaining,
            l0_yes_price=l0_yes_price,
            l0_no_price=l0_no_price,
            weak_leg=weak_leg,
            time_remaining_sec=time_rem_sec,
            imbalance_shares=imbalance_shares,
            stress_multiplier=1.0,
            is_desperate=is_desperate,
        )

        # ----------------------------------------------------------------
        # STEP 16b: Post-filter blocked sides
        # (cleaner than passing 0.0 which kills both sides via grid_manager continue)
        # ----------------------------------------------------------------
        if yes_blocked or no_blocked:
            before_n = len(target)
            target = [
                lvl for lvl in target
                if not (yes_blocked and lvl.side == 'YES')
                and not (no_blocked and lvl.side == 'NO')
            ]
            if self._should_log_decision(f'POSTFILTER_y{int(yes_blocked)}_n{int(no_blocked)}'):
                logger.info(
                    f"[SIMPLE_POSTFILTER] yes_blocked={yes_blocked} no_blocked={no_blocked} "
                    f"target {before_n}->{len(target)}"
                )

        # ----------------------------------------------------------------
        # STEP 17: Sync grid (cancels + places via OrderActions)
        # ----------------------------------------------------------------
        refresh_timeout = self.config.refresh_timeout_calm_sec
        actions = self.grid_manager.sync(target, refresh_timeout=refresh_timeout)

        # ----------------------------------------------------------------
        # STEP 18: Update telemetry + periodic pricing trace
        # ----------------------------------------------------------------
        self._update_telemetry(time_rem_sec, q_imbalance, fv, half_spread, sigma)
        self._fills_this_tick = 0
        
        # === SIMPLE_PRICING_TRACE — every 30s, mechanical visibility into gradient ===
        now = time.time()
        if now - getattr(self, '_last_pricing_trace_ts', 0) > 30.0:
            self._last_pricing_trace_ts = now
            tf = getattr(self, '_last_time_factor', 0.0)
            sn = getattr(self, '_last_sigma_norm', 0.0)
            ppc = getattr(self, '_last_projected_pair_cost', 0.0)
            ls = getattr(self, '_last_lot_scale', 1.0)
            scaled = getattr(self.grid_manager, 'grid_lot_size_y', self.config.grid_lot_size)
            ips = getattr(self, '_last_inv_ps', 1.0)
            psp = getattr(self, '_last_ps_pressure', 1.0)
            logger.info(
                f"🎯 [SIMPLE_PRICING_TRACE] "
                f"FV:{fv:.4f} σ:{sigma:.6f} σ_norm:{sn:.2f} "
                f"| Q:{q_imbalance} | T_norm:{(time_rem_sec/self.config.market_duration_sec):.2f} "
                f"| time_factor:{tf:.3f} | inv_ps:{ips:.4f} | ps_pres:{psp:.2f} "
                f"| reservation:{reservation:.4f} | half_spread:{half_spread:.4f} "
                f"| l0_yes:{l0_yes_price:.3f} l0_no:{l0_no_price:.3f} "
                f"| proj_pair:{ppc:.4f} | lot_scale:{ls:.2f} | scaled_lot:{scaled} "
                f"| target_n:{len(target)} | budget:${budget_remaining:.1f}"
            )

        return actions

    # ========================================================================
    # ON_TRADE — minimal (no CVD machinery)
    # ========================================================================

    def on_trade(self, trade: dict):
        """
        SIMPLE bot: no CVD tracking, no Market Regime FSM, no Torpedo Pull.
        BTC price comes from oracle_engine via shared memory in on_tick.
        Trade.price is Polymarket trade price, not BTC price — irrelevant here.
        """
        # No-op for SIMPLE strategy.
        # We keep last_trade_ts updated for any external monitoring.
        try:
            size = float(trade.get('size', 0))
            if size > 0:
                self.last_trade_ts = time.time()
        except Exception:
            pass

    # ========================================================================
    # ON_FILL — position update + grid_manager notification
    # ========================================================================

    def on_fill(self, fill_data: dict):
        """Handle fill confirmation: update PositionState + grid_manager."""
        try:
            side = fill_data.get('side', '')
            size = int(fill_data.get('size', 0))
            price = float(fill_data.get('price', 0))
            is_sell = bool(fill_data.get('is_sell', False))
            order_id = fill_data.get('order_id', '')

            if size <= 0:
                return

            if is_sell:
                # Recycling sell: reduce inventory + cost
                if side == 'YES':
                    self.position.yes_shares = max(0, self.position.yes_shares - size)
                    self.position.total_yes = max(0, self.position.total_yes - size)
                    self.position.yes_cost = max(0.0, self.position.yes_cost - size * price)
                else:
                    self.position.no_shares = max(0, self.position.no_shares - size)
                    self.position.total_no = max(0, self.position.total_no - size)
                    self.position.no_cost = max(0.0, self.position.no_cost - size * price)
                # Realize PnL: sold at price, originally bought at avg_cost
                self.position.realized_ctf_pnl += size * price
            else:
                # Buy: increase inventory + cost
                if side == 'YES':
                    self.position.yes_shares += size
                    self.position.total_yes += size
                    self.position.yes_cost += size * price
                elif side == 'NO':
                    self.position.no_shares += size
                    self.position.total_no += size
                    self.position.no_cost += size * price

            # Notify grid_manager
            self.grid_manager.on_fill(order_id, size, price)

            # Counters
            self._fills_this_tick += 1
            self._total_fills += 1

            # Emit event for live_state
            self._emit_event('fill', side, price, size)

            # Logging — uses gabalog.simple_strategy logger (separate namespace
            # but same format → analysis.cli FILL_RE pattern matches)
            logger.info(
                f"💰 [SIMPLE_FILL] {side} {size}@{price:.3f} "
                f"| Pos Y:{self.position.total_yes} N:{self.position.total_no} "
                f"| Q:{self.position.q} "
                f"| Cost:${self.position.total_cost:.2f} "
                f"| Realized:${self.position.realized_ctf_pnl:+.4f}"
            )
            
            # === SIMPLE_TOXIC_ORIGIN — schema mirrors GridStrategy [TOXIC_ORIGIN] ===
            # Used by analysis.cli toxic view. PS_after computed as inv_ps proxy.
            try:
                q_before = self.position.q + (size if is_sell else -size if side == 'NO' else size)
                q_after = self.position.q
                fv_now = self.current_fv
                inv_load_proxy = abs(q_after) / max(1, self.config.inventory_hard_cap)
                t_rem = int(getattr(self, '_last_time_remaining_sec', 0))
                ya = (self.position.yes_cost / max(1, self.position.total_yes)) if self.position.total_yes > 0 else 0.0
                na = (self.position.no_cost / max(1, self.position.total_no)) if self.position.total_no > 0 else 0.0
                inv_ps_after = ya + na if (ya > 0 and na > 0) else 1.0
                ps_before = inv_ps_after  # SIMPLE has no merge — PS_before == PS_after
                ya_before = ya
                na_before = na
                
                logger.warning(
                    f"☣️📊 [TOXIC_ORIGIN] Side:{side} {size}@{price:.3f} "
                    f"| PS_before:{ps_before:.4f} → PS_after:{inv_ps_after:.4f} "
                    f"| Y_avg:{ya_before:.3f}→{ya:.3f} N_avg:{na_before:.3f}→{na:.3f} "
                    f"| Q:{q_before}→{q_after} | FV:{fv_now:.3f} "
                    f"| Intent:NORMAL | Regime:NEUTRAL | RegAtIntent:NEUTRAL "
                    f"| PSAtIntent:BALANCED | IMAtIntent:SIMPLE | FVAtIntent:{fv_now:.3f} "
                    f"| SprAtIntent:0.000 | FillAge:0.0s | IntMode:SIMPLE "
                    f"| InvL:{inv_load_proxy:.2f} | T:{t_rem}sMkt:{self._c_mkt or 'unknown'} | "
                )
            except Exception as e:
                logger.debug(f"[SIMPLE_TOXIC_ORIGIN_ERR] {e}")

        except Exception as e:
            logger.error(f"❌ [SIMPLE_FILL_ERROR] {e}", exc_info=True)

    # ========================================================================
    # ON_MARKET_SWITCH — reset state for new market
    # ========================================================================

    def on_market_switch(self, new_slug: str = ''):
        """Reset state when bridge detects new market window."""
        old_slug = self._c_mkt
        # Adapter sometimes calls without arg — preserve old slug if none provided
        if new_slug:
            self._c_mkt = new_slug

        # Reset position completely (assumes resolve already paid out previous)
        self.position.reset()
        self.grid_manager.clear_all()

        # Clear historical buffers
        self._btc_price_history.clear()
        self._market_tape_log.clear()
        self._order_events.clear()

        # Reset cached state
        self.paper_winner = None
        self._strike_price = None
        self._is_official_strike = False
        self.current_fv = 0.5
        self._last_fv_for_cvd = 0.5
        self._last_btc_price = 0.0
        self._last_btc_ts = 0.0
        self._fills_this_tick = 0
        self._toxic_position_ticks = 0
        self._bankrupt_sides = set()
        self._consensus_confirmed = False
        self._regime_entered_ts = time.time()

        logger.info(f"🔄 [SIMPLE_MARKET_SWITCH] {old_slug} → {new_slug}")

    # ========================================================================
    # GET_LIVE_STATE — schema for live_state_*.json (read by HTML monitor)
    # ========================================================================

    def get_live_state(self) -> dict:
        """
        Return state dict consumed by bridge → live_state_<bot_id>.json.
        
        Schema mirrors GridStrategy keys for HTML monitor compatibility.
        Static-mock fields where SIMPLE has no equivalent (regime, intent_mode).
        """
        return {
            'strategy': 'simple',
            'slug': self._c_mkt or 'unknown',
            'events': list(self._order_events)[-50:],  # last 50 events for HUD chart
            
            # Position
            'q': self.position.q,
            'yes_shares': self.position.yes_shares,
            'no_shares': self.position.no_shares,
            'total_yes': self.position.total_yes,
            'total_no': self.position.total_no,
            'yes_cost': round(self.position.yes_cost, 3),
            'no_cost': round(self.position.no_cost, 3),
            'pos_total_cost': round(self.position.total_cost, 3),
            'pos_realized_pnl': round(self.position.realized_ctf_pnl, 4),
            'imbalance_pct': round(self.position.imbalance_pct, 2),
            'locked_pairs': self.position.locked_pairs,
            
            # Pricing
            'fv': round(self.current_fv, 4),
            'sigma': round(self._compute_volatility(), 6),
            'half_spread': round(self.last_telemetry.spread / 2, 4) if self.last_telemetry.spread else 0,
            
            # Mock state (for HTML monitor field compatibility)
            'regime': 'NEUTRAL',
            'intent_mode': 'SIMPLE',
            'pair_state': 'BALANCED',
            'cvd_signal': 0.0,
            'stress': 0.0,
            
            # Telemetry
            'tel': self._format_telemetry(),
            'telemetry': self._format_telemetry(),
            
            # Timing
            'fills_total': self._total_fills,
            'cancels_total': self._total_cancels,
        }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _extract_bbo(self, market_data: dict) -> tuple[float, float, float, float]:
        """
        Extract YES/NO bid/ask.
        
        GridAdapter._build_market_data() pre-aggregates orderbook into ready
        scalar fields: yes_bid, yes_ask, no_bid, no_ask. We read them directly.
        Adapter also caches stale values across single-sided updates (its _ob_cache),
        so we always get full BBO snapshot.
        """
        yes_bid = float(market_data.get('yes_bid', 0) or 0)
        yes_ask = float(market_data.get('yes_ask', 0) or 0)
        no_bid = float(market_data.get('no_bid', 0) or 0)
        no_ask = float(market_data.get('no_ask', 0) or 0)
        
        # Cache for telemetry / get_live_state
        if yes_bid > 0: self._last_orderbook['yes_bid'] = yes_bid
        if yes_ask > 0: self._last_orderbook['yes_ask'] = yes_ask
        if no_bid > 0: self._last_orderbook['no_bid'] = no_bid
        if no_ask > 0: self._last_orderbook['no_ask'] = no_ask
        
        return yes_bid, yes_ask, no_bid, no_ask

    def _compute_mid_market(
        self, yes_bid: float, yes_ask: float, no_bid: float, no_ask: float
    ) -> float:
        """
        Implicit mid market for binary contract.
        On Polymarket binary: YES_price + NO_price ≈ $1.00 in equilibrium.
        Mid = average of YES mid and (1 - NO mid).
        """
        yes_mid = (yes_bid + yes_ask) / 2 if yes_ask > 0 else yes_bid
        no_mid_implied_yes = 1.0 - ((no_bid + no_ask) / 2 if no_ask > 0 else no_bid)
        return (yes_mid + no_mid_implied_yes) / 2

    def _compute_volatility(self) -> float:
        """
        Compute relative volatility σ from BTC price window.
        
        Returns relative std (e.g. 0.001 = 0.1% intraday vol).
        This σ is used in GLFT half_spread formula (σ²-scaling).
        """
        if len(self._btc_price_history) < 5:
            return 0.0

        now = time.time()
        cutoff = now - self.GLFT_VOL_WINDOW_SEC
        in_window = [p for ts, p in self._btc_price_history if ts > cutoff]

        if len(in_window) < 5:
            return 0.0

        mean_p = sum(in_window) / len(in_window)
        if mean_p < 100:
            return 0.0

        variance = sum((p - mean_p) ** 2 for p in in_window) / len(in_window)
        std = math.sqrt(variance)
        return std / mean_p  # relative volatility

    def _get_btc_price(self, market_data: dict) -> float:
        """Read BTC price from market_data with shared memory fallback."""
        btc = float(market_data.get('btc_price') or 0)
        if btc < 100:
            try:
                btc = float(self.config.shared_btc_price.value)
            except Exception:
                btc = 0.0
        return btc

    def _get_strike(self, market_data: dict) -> Optional[float]:
        """Read strike from market_data with shared memory fallback."""
        strike = market_data.get('strike_price')
        if not strike or strike < 100:
            try:
                shared = float(self.config.shared_btc_strike.value)
                if shared > 100:
                    strike = shared
            except Exception:
                strike = None
        return strike

    def _cancel_all(self, reason: str) -> list[OrderAction]:
        """Cancel all pending orders with given reason."""
        actions: list[OrderAction] = []
        for oid in list(self.grid_manager.pending_orders.keys()):
            actions.append(OrderAction(action='cancel', order_id=oid, reason=reason))
        if actions and self._should_log_decision(f'CANCEL_ALL_{reason}'):
            logger.warning(f"❌ [SIMPLE_CANCEL_ALL] {reason} | n={len(actions)}")
        return actions

    def _emit_event(self, action: str, side: str, price: float, size: int):
        """
        Append event to internal deque (consumed by bridge for live_state.json).
        Format mirrors GridStrategy event schema for HTML monitor compatibility.
        """
        event = {
            'type': action,  # 'place' | 'cancel' | 'fill'
            'side': side,
            'price': float(price),
            'size': int(size),
            'ts': time.time(),
            'is_taker': False,
            'intent': 'SIMPLE',
        }
        self._order_events.append(event)
        # Tape log for resolve fallback (bridge reads strat._market_tape_log)
        self._market_tape_log.append({
            **event,
            'type': 'tick',
            'yes_bid': self._last_orderbook.get('yes_bid', 0),
            'no_bid': self._last_orderbook.get('no_bid', 0),
        })
        # Limit tape size to avoid memory bloat
        if len(self._market_tape_log) > 1000:
            self._market_tape_log = self._market_tape_log[-500:]

        if action == 'cancel':
            self._total_cancels += 1

    def _update_telemetry(
        self, time_rem: float, q: int, fv: float, half_spread: float, sigma: float
    ):
        """Update lightweight telemetry for dashboards."""
        tel = self.last_telemetry
        tel.q = q
        tel.fv = fv
        tel.spread = half_spread * 2
        tel.time_remaining = time_rem
        tel.timestamp = time.time()
        tel.regime = 'NEUTRAL'
        tel.step_reached = 'COMPLETE'
        tel.cvd_sig = 0.0
        tel.stress = 0.0
        tel.imbalance_pct = self.position.imbalance_pct

    def _format_telemetry(self) -> dict:
        """Telemetry → dict for live_state.json."""
        return {
            'q': self.last_telemetry.q,
            'fv': round(self.last_telemetry.fv, 4),
            'spread': round(self.last_telemetry.spread, 4),
            'regime': self.last_telemetry.regime,
            'step_reached': self.last_telemetry.step_reached,
            'time_remaining': round(self.last_telemetry.time_remaining, 1),
        }

    def _calculate_unrealized_pnl(self) -> dict:
        """
        Bridge price_ticker_loop reads this method.
        Estimate winner + payout based on current BTC vs strike.
        """
        strike = self._strike_price or 0
        btc = self._last_btc_price or 0

        if btc > 0 and strike > 100:
            likely_winner = 'YES' if btc > strike else 'NO'
        else:
            likely_winner = '?'

        if likely_winner == 'YES':
            payout = self.position.total_yes  # $1 each on win
        elif likely_winner == 'NO':
            payout = self.position.total_no
        else:
            payout = 0.0

        unrealized = payout - self.position.total_cost + self.position.realized_ctf_pnl
        deposit = max(1.0, float(self.config.deposit))
        roi_pct = unrealized / deposit * 100.0

        return {
            'likely_winner': likely_winner,
            'pnl': float(unrealized),
            'roi_pct': float(roi_pct),
        }

    def record_api_request(self, n: int):
        """Bridge engine callback for API request rate tracking."""
        self._api_requests_total += n

    def _should_log_decision(self, decision_key: str) -> bool:
        """Anti-spam log throttle: same decision logs once every 5s."""
        now = time.time()
        last = getattr(self, f'_log_dedup_{decision_key}', 0)
        if now - last > 5.0:
            setattr(self, f'_log_dedup_{decision_key}', now)
            return True
        return False

    # ========================================================================
    # last_trade_ts — required by some bridge code paths
    # ========================================================================
    last_trade_ts: float = 0.0
