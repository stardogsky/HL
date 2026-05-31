"""
Grid market making strategy coordinator.

6-step pipeline per tick:
1. RISK_CHECK    - drawdown stop?
3. TIME_CHECK    - end of market? -> cancel all
4. GRID_CALCULATE - AS prices for grid levels
5. GRID_SYNC     - cancel stale + place new (batch)
6. LOG           - telemetry

See: docs/STRATEGY_V6_GRID.md section 6.1
"""

from __future__ import annotations
import json
import asyncio
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Any, Optional
import logging
logger = logging.getLogger('gabalog.grid_strategy')

import time
from datetime import datetime, timezone
from strategies.gabagool.oracle_engine import OracleEngine
import math
        
from collections import deque

from strategies.gabagool.grid_manager import GridManager, OrderAction, TICK_SIZE, GridLevel


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class DualCoreDefense:
    """
    Двухслойная защита на основе CVD.
    Слой 1: Инвентарный SKEW (динамический порог страха).
    Слой 2: Momentum VETO (детектор торпеды).
    """

    def __init__(self, config):
        cfg = config

        # --- Слой 1: SKEW параметры ---
        self.skew_base_thr  = getattr(cfg, 'cvd_skew_activation_threshold', -0.05)
        self.skew_max_cents = getattr(cfg, 'cvd_skew_max_cents', 0.015)
        self.hunter_thr     = getattr(cfg, 'hunter_imb_threshold', 15)
        self.avgmax_q       = getattr(cfg, 'cvd_avgmax_q', 35.0)

        # --- Слой 2: VETO параметры ---
        self.momentum_veto_thr = getattr(cfg, 'cvd_momentum_veto_thr', -0.25)
        self.momentum_window   = getattr(cfg, 'cvd_momentum_window', 3.0)
        self.veto_cooldown     = getattr(cfg, 'cvd_veto_cooldown', 8.0)
        self.veto_min_q        = self.hunter_thr

        # --- Deadband: подавление реквот-спама ---
        self.skew_deadband  = 0.04          # не реквотить если сигнал у границы
        self.last_skew_thr  = 0.0
        self.last_veto_ts   = 0.0

        # --- История CVD (кольцевой буфер ~15 тиков по 2s) ---
        self.cvd_history: deque = deque(maxlen=15)

    def reset(self):
        """Полный сброс контура при смене рынка."""
        self.cvd_history.clear()
        self.last_veto_ts = 0.0
        self.last_skew_thr = 0.0    

    # ------------------------------------------------------------------
    # СЛОЙ 1: Сенсор — вычисляет динамический порог и интенсивность SKEW
    # ------------------------------------------------------------------
    def _compute_layer1_skew(self, cvd_sig: float, open_q: int) -> dict:
        """< 1ms — только арифметика."""
        q_excess   = max(0, abs(open_q) - self.hunter_thr)
        q_ratio    = min(1.0, q_excess / max(1.0, self.avgmax_q - self.hunter_thr))
        dyn_shift  = (q_ratio ** 1.5) * 0.40          # нелинейный сдвиг [0, 0.40]
        dyn_thr    = self.skew_base_thr - dyn_shift    # порог уходит глубже при Q↑

        skew_active    = cvd_sig < dyn_thr
        skew_intensity = max(0.0, dyn_thr - cvd_sig)  # насколько ниже порога
        skew_pct       = min(1.0, skew_intensity / 0.40)  # 0→1 (интенсивность)

        # Deadband: реквот только если порог сдвинулся значимо
        thr_changed    = abs(dyn_thr - self.last_skew_thr) > self.skew_deadband
        if thr_changed:
            self.last_skew_thr = dyn_thr

        # Смещение цены пропорционально интенсивности
        price_skew_cents = skew_pct * self.skew_max_cents if skew_active else 0.0

        return {
            'skew_active':       skew_active,
            'dynamic_threshold': round(dyn_thr, 4),
            'skew_intensity':    round(skew_intensity, 4),
            'skew_pct':          round(skew_pct, 3),
            'price_skew_cents':  round(price_skew_cents, 4),
            'requote_allowed':   thr_changed,
        }

    # ------------------------------------------------------------------
    # СЛОЙ 2: Детектор торпеды — вычисляет momentum и решает о VETO
    # ------------------------------------------------------------------
    def _compute_layer2_veto(self, cvd_sig: float, open_q: int, ts: float) -> dict:
        """< 1ms — сканирование кольцевого буфера."""
        self.cvd_history.append((ts, cvd_sig))

        momentum   = 0.0
        veto_ready = False

        if len(self.cvd_history) >= 2:
            # Ищем точку ~3s назад
            for hist_ts, hist_val in reversed(list(self.cvd_history)[:-1]):
                if ts - hist_ts >= self.momentum_window - 0.5:
                    momentum = (cvd_sig - hist_val) / max(0.1, ts - hist_ts)
                    break

            cooldown_ok = (ts - self.last_veto_ts) > self.veto_cooldown
            q_at_risk   = abs(open_q) >= self.veto_min_q  # VETO бессмысленен без позы

            if momentum < self.momentum_veto_thr and cooldown_ok and q_at_risk:
                veto_ready = True
                self.last_veto_ts = ts

        return {
            'veto_active':   veto_ready,
            'momentum':      round(momentum, 4),
            'veto_cooldown': round(max(0.0, self.veto_cooldown - (ts - self.last_veto_ts)), 1),
        }

    # ------------------------------------------------------------------
    # ГЛАВНЫЙ МЕТОД: Реакция — принимает решение на основе двух слоёв
    # ------------------------------------------------------------------
    def evaluate(self, cvd_sig: float, open_q: int) -> dict:
        """
        Вызывать из on_tick после расчёта CVD_Sig.
        Возвращает action и hunter_mode для передачи в pricing pipeline.
        """
        ts = time.monotonic()

        layer1 = self._compute_layer1_skew(cvd_sig, open_q)
        layer2 = self._compute_layer2_veto(cvd_sig, open_q, ts)

        # --- Финальное решение ---
        if layer2['veto_active']:
            # Торпеда: стоп новых входов, существующие ордера НЕ трогать
            action       = 'VETO'
            hunter_mode  = 'FREEZE'
            choke_mult   = 0.0

        elif layer1['skew_active']:
            skew_pct = layer1['skew_pct']
            action   = 'SKEW'

            if skew_pct > 0.75:
                # Глубокий SKEW: Hunter агрессивен, новые входы заморожены
                hunter_mode = 'AGGRESSIVE'
                choke_mult  = 0.0
            elif skew_pct > 0.40:
                # Средний SKEW: Hunter под давлением, входы урезаны
                hunter_mode = 'PRESSURE'
                choke_mult  = 0.5
            else:
                # Лёгкий SKEW: Hunter пассивен, входы умеренно урезаны
                hunter_mode = 'PASSIVE'
                choke_mult  = 0.75

        else:
            action      = 'NORMAL'
            hunter_mode = 'PASSIVE' if abs(open_q) > self.hunter_thr else 'OFF'
            choke_mult  = 1.0

        return {
            # Для pricing pipeline
            'action':            action,
            'hunter_mode':       hunter_mode,
            'choke_mult':        choke_mult,
            'price_skew_cents':  layer1['price_skew_cents'],

            # Для логирования (Слой 6 метрики)
            'dynamic_threshold': layer1['dynamic_threshold'],
            'skew_intensity':    layer1['skew_intensity'],
            'momentum':          layer2['momentum'],
            'veto_active':       layer2['veto_active'],
            'requote_allowed':   layer1['requote_allowed'],
        }    


@dataclass
class GridConfig:
    """All strategy parameters in one place."""

    # Budget
    deposit: float = 150.0
    bankroll_usd: float = 300.0

    
    # Grid
    grid_levels: int = 3
    grid_spacing_ticks: int = 1
    spacing_asym_multiplier: float = 2.5
    grid_lot_size: int = 5
    grid_refresh_interval: float = 1.0

    # Risk
    drawdown_pct: float = 10.0
    market_pnl_stop_roi: float = -5.0

    # ── ДИНАМИЧЕСКОЕ ЦЕНООБРАЗОВАНИЕ (Module 2: Profit Engine) ──
    edge_min: float = 0.015            # Пол спреда (1.5 цента)
    edge_max: float = 0.050            # Потолок спреда (5 центов)
    edge_vol_sensitivity: float = 0.01 # Сила реакции на ln(vol_ratio)
    target_edge: float = 0.02          # Текущее (динамическое)
    
    max_penalty_dev: float = 0.15      # Лимит штрафа (будет пересчитан)
    # --- CVD SENSOR & PROTECTION ---
    cvd_window_sec: float = 60.0                 # Окно замера CVD в секундах
    cvd_streak_toxic_threshold: float = 0.5      # Уровень токсичности для отсчета страйков
    cvd_skew_activation_threshold: float = -0.30 # Сигнал активации асимметричного смещения L0
    cvd_skew_max_cents: float = 0.015            # Максимальное смещение котировки (1.5 цента)
    cvd_avgmax_q: float = 35.0
    cvd_momentum_veto_thr: float = -0.25
    cvd_momentum_window: float = 3.0
    cvd_veto_cooldown: float = 8.0

    # [MARKET REGIME FSM v2.4]
    cvd_fast_window_sec: float = 6.0          # Fast CVD окно для TORPEDO (сек)
    cvd_slow_window_sec: float = 45.0         # Slow CVD окно для DIR (сек)
    cvd_slow_min_trades: int = 6              # Мин. трейдов в slow-окне для валидности
    regime_torpedo_momentum_thr: float = 0.20 # |momentum| выше → TORPEDO
    regime_dir_slow_cvd_thr: float = 0.35    # |CVD_slow| выше → кандидат в DIR
    regime_dir_momentum_max: float = 0.08    # |momentum| ниже → подтверждение DIR
    regime_dir_min_streak: int = 15          # streak выше → подтверждение DIR
    regime_torpedo_lock_sec: float = 3.0     # Мин. время в TORPEDO до выхода (сек)
    streak_decay_rate: int = 3               # Decay streak вместо hard reset

    # ── ДЕТЕКТОР РЕЖИМОВ (Velocity) ── 
    velocity_memory_sec: float = 8.0
    velocity_flat_threshold: float = 0.030
    velocity_trend_threshold: float = 0.055

    btc_vel_stress_threshold: float = 50.0
    
    # ── ВНЕДРЕНО ИЗ YAML (Оракул и Токсик) ──
    toxic_end_buffer_sec: float = 225.0
    toxic_price_threshold: float = 0.15
    # [v11.70] Параметры Вентиля Волатильности
    oracle_drift_threshold: float = 0.004   # Порог подтвержденного движения BTC
    oracle_panic_threshold: float = 0.020   # Порог для Ядерной Заморозки
   

    # ── TEMPORAL DECAY (Затухание страха) ──
    fade_half_life_sec: float = 3.0   # Время в секундах от глухой блокировки до полного возврата к торговле

    blindness_floor: float = 0.04      # Аппаратный пол VETO (ниже не опускаемся)
    blindness_vol_sens: float = 0.5    # Коэффициент чувствительности VETO к волатильности
    oracle_min_weight: float = 0.20       # Минимальный вес Оракула (Якорь)
    oracle_recovery_rate: float = 0.05    # Шаг плавного возврата веса (за тик)

    # --- НОВЫЕ ПАРАМЕТРЫ СЖАТИЯ ---
    oracle_edge_compression_power: float = 1.0  # 1.0 = парабола, 0.0 = выключено
    oracle_edge_compression_min: float = 0.20   # Пол (минимум 20% от базового люфта)
    oracle_sigmoid_steepness: float = 4.5        # Крутизна переключения (Sigmoid k)

    # Timing & Execution
    endgame_fade_start_sec: float = 300   # (С какой секунды начинается сжатие инвентаря. По умолчанию 5 минут).
    refresh_timeout_calm_sec: float = 15.0   # Спокойный рынок Refresh Timeout
    refresh_timeout_panic_sec: float = 2.5   # Напряженный рынок Refresh Timeout
    market_duration_sec: float = 900.0
    end_market_buffer_sec: float = 30.0
    stale_threshold_ticks: int = 1      # RETREAT tolerance for cheap leg (ticks) (Asymmetric Hysteresis)
    chase_threshold_ticks: int = 2      # FIFO tolerance when chasing price up (Asymmetric Hysteresis)
    deep_level_static: bool = True      # L1+ don't move (anchor for squeezes) (Asymmetric Hysteresis)
    fill_cooldown_sec: float = 0.0      # 0=disabled; seconds to wait before placing on filled side (Emergency brake — hard imbalance cutoff)
    

    # Regime cascade — parent (15m) → child (5m) regime escalation
    regime_cascade_enabled: bool = False       # off by default
    regime_cascade_file: str = ''              # path to parent regime JSON (read by child)
    regime_broadcast_file: str = ''            # path to write own regime JSON (parent broadcasts)
    cascade_decay_factor: float = 0.0          # √T dampening: 0.5 for 15m→5m (0 = off)

    # ── ЭЛАСТИЧНЫЙ ЗАТВОР (Module 4: Iron Gate) ──
    # Мы заменяем всю старую группу Profit Gate на эти 4 параметра
    gate_min: float = 0.970            # Лимит стоимости пары на старте (вместо ps_min/max)
    gate_max: float = 1.010            # Лимит стоимости в Эндшпиле
    profit_gate_ps_max: float = 0.985  # Текущий динамический лимит (Master Limit)
    hunter_max_gate: float = 1.000     # Лимит для Охотника
    inventory_scale_shares: int = 15

    # --- Блок 9: Dual Hard Cutoff ---
    inventory_hard_cap: int = 350           # Жёсткий лимит акций на ногу (глобальный q).
                                            # Используется в Orchestrator, Forensic.
    open_q_sensitivity_cap: int = 60        # Делитель чувствительности inv_load в Auto Armor.
                                            # Калиброван под диапазон open_q (10-40 акций).
    
    hard_cutoff_max: int = 35              # Стена на старте (T-900)
    hard_cutoff_min: int = 7               # Стена в финале (T-0)
    hard_cutoff_shares: int = 35           # Текущее значение (будет перезаписано)           

    # ── АДАПТИВНЫЙ КАЛИБР (Module 3: Kelly Sizing) ──
    lot_k_min: float = 0.6             # Множитель "разведки" (3 акции при базе 5)
    lot_k_max: float = 3.0             # Множитель "снайпера" (15 акций при базе 5)
    alpha_ramp_min: float = 0.01       # 1 цент разрыва (старт роста)
    alpha_ramp_max: float = 0.04       # 4 цента разрыва (пик уверенности)
    latency_trust_threshold: float = 500.0 # Порог лага (мс) для сброса Kelly в 1.0
    
    max_single_lot: int = 30           # Абсолютный хард-кап калибра
    avg_tranche_max_size: int = 5      # Будет пересчитан динамически

    # Maker Inventory Recycling — sell heavy leg to free capital
    recycling_enabled: bool = False
    recycling_utilization_threshold: float = 0.80   # trigger when cap util >= 80%
    recycling_imbalance_threshold: float = 30.0     # OR imbalance >= 30%
    recycling_min_profit_ticks: int = 2              # sell at avg_cost + N ticks minimum
    recycling_max_excess_pct: float = 0.20           # sell max 20% of excess per order

    # Emergency Inventory Dump — sell excess when stuck with 100% directional exposure
    
    emergency_dump_slippage: float = 0.03  # Проскальзывание для Taker-удара
    emergency_dump_imb_pct: float = 85.0      # trigger when imbalance >= this %
    # ── ЕДИНЫЙ КОНТУР ВЫЖИВАНИЯ (Module 6: Unified Triage) ──
    emergency_dump_enabled: bool = False # МАСТЕР-РУБИЛЬНИК
    emergency_price_floor: float = 0.08  # Пол цен (ниже такером не бьем)
    toxic_q_safe: int = 5

    max_patience_ticks: int = 30        # Макс. тиков терпения на старте
    _triage_active_side: Optional[str] = None # 'YES', 'NO' или None

    # MERGING
    min_merge_size: int = 5            # Минимум 15 полных пар для запуска Merge
    merge_cooldown_sec: float = 30.0    # Пауза между слияниями 30 секунд
    max_market_spread: float = 0.15
    shared_btc_price: Any = None
    shared_btc_strike: Any = None # Добавляем общую ячейку для страйка
    shared_btc_ts: Any = None
    nudge_size: float = 0.01
    hft_latency_halt_ms: float = 250.0 

    # ── ПАТЧ v12.3-SURVIVAL (Vega-Aware) ──
    # 1. Триггеры и коэффициенты
    momentum_halt_thr: float = 15.0      # Порог рывка BTC в $ за 1 тик для паузы
    gamma_aggression: float = 120.0      # Коэффициент расширения спреда (120.0 / T_rem)
    vol_memory_fast: int = 300           # Окно быстрой волатильности (5 мин)
    vol_memory_slow: int = 1800          # Окно медленной волатильности (30 мин)
    
    # 2. Аппаратные лимиты безопасности (чтобы математика не сошла с ума)
    max_adaptive_edge: float = 0.15      # Максимальный спред (15 центов)
    max_vol_ratio: float = 10.0          # Ограничитель всплеска множителя Vega
    
    # 3. Shared-память для связи Оракула и Стратегии
    shared_vol_ratio: Any = None         
    shared_btc_delta: Any = None

    # --- Cyber-Shield Params ---
    shield_threshold: float = 0.75        # Порог включения защиты (75%)
    shield_max_boost: float = 0.08       # Макс. надбавка к цене Охотника ($0.08)
    shield_scale_cutoff: float = 0.60    # На сколько режем scale (0.60 = на 60%)

    # Recovery
    recovery_enabled: bool = True
    recovery_max_attempts: int = 3
    recovery_max_ask_price: float = 0.75
    recovery_max_budget_pct: float = 30.0
    recovery_imbalance_threshold: float = 30.0  # percent

    recovery_inv_ps_threshold: float = 1.005  # Порог, при котором инвентарь считается токсичным
    recovery_discount_cents: float = 0.05    # Скидка (в центах) от средней цены, при которой бот начинает усреднять позицию

    merge_lock_sec: float = 1.5           # Пауза для разлока акций перед Merge
    knife_protection_cents: float = 0.15   # Порог обвала (15 центов от средней цены)
    endgame_hunter_buffer_sec: float = 180.0 # За сколько секунд до конца выключать Hunter
    survivor_lock_enabled: bool = True

    # [v12.2.2-PRO] Новые параметры контура выживания
    hunter_max_gate: float = 1.05          # Максимальная цена пары при хеджировании
    hunter_imb_threshold: int = 5          # ДОБАВЛЕНО: Порог включения Hunter в акциях
    hunter_chunk_size: int = 15   # Размер транша Охотника (будет density-aware после валидации DS данных)

    # Task 1 & 3: Survival Thresholds
    stress_quote_suppress: float = 0.99
    stress_avg_allow: float = 0.995
    toxic_exit_fv_threshold: float = 0.04
    avg_tranche_max_size: int = 5
    
    # Task 2: Anti-Snipe
    pre_pull_cooldown_ticks: int = 10
    max_fills_per_tick: int = 2
    
    # Task 3: Progressive Exit
    taker_exit_toxic_ticks: int = 15
    urgency_discount_base: float = 0.005
    urgency_discount_max: float = 0.04
    exit_floor_fv_pct: float = 0.85

    # --- Эластичность и Защита (v15.2) ---
    empty_book_premium: float = 0.10          # Наценка поверх FV, если стакан пуст
    maq_trend_threshold: float = 0.30         # Отклонение FV от 0.50 (края рынка), где MAQ снижается
    maq_trend_value: float = 0.025            # Значение MAQ на краях рынка (допускаем копеечные ордера)
    hunter_escalation_shares: float = 10.0    # За сколько акций сверх порога паника разгонится на 100%
    toxic_max_premium: float = 0.06           # Жесткий потолок переплаты над Справедливой Ценой
    garbage_dist_base: float = 0.08           # Расстояние в центах от спреда до ордера, считающегося "мусором"
    MAQ_BASE: float = 0.06                    # Базовая защита от копеечных сделок (минимальный профит)
    veto_panic_gate: float = 1.02             # Абсолютный потолок цены пары, разрешенный VETO при панике
    gamma_maq_min_discount: float = 0.5       # [NEW] Управление жадностью в Гамма-зоне
    maq_asym_hedge_threshold: int = 10
    base_deadband: float = 2.0
    emergency_dump_sell_pct: float = 0.80   # <--- ДОБАВИТЬ
    emergency_dump_slippage: float = 0.04   # <--- ДОБАВИТЬ

    # [NEW] Добавить в блок ценообразования
    max_adaptive_edge: float = 0.15     # Потолок спреда
    
    # [NEW] Добавить в блок Щита
    shield_threshold: float = 0.75      # Порог активации
    shield_max_boost: float = 0.08      # Макс помощь хеджу
    shield_scale_cutoff: float = 0.60   # Сила удушения риска

    sigma_base: float = 0.02
    healer_max_overpay: float = 0.030
    tick_base_gate_cap: float = 0.995
    hunter_min_penetration: float = 0.25  # Минимальное проникновение в спред (25%) при низком давлении
    asym_cvd_threshold: float = 0.40   # Порог CVD_Sig для активации асимметричного сайзинга
    asym_time_gate_sec: float = 600.0  # Только в первые 10 минут рынка (t_rem > 600s)

    abs_max_pair_cost: float = 1.02
    mirror_min_improvement: float = 0.04
    torpedo_pull_streak: int = 25      # streak при котором отменяем тяжёлую сторону
    torpedo_pull_cooldown: float = 15.0  # минимальный интервал между отменами (сек)
    hunter_imb_tolerance_pct: float = 0.10 # Охотник игнорирует перекос < 10% от общего инвентаря
    dir_regime_mode: str = 'OPTIMIZE_PRICE'
    cold_start_fv_upper_thr: float = 0.55
    cold_start_fv_lower_thr: float = 0.45
    hunter_locked_ps_guard: float = 1.005
# ---------------------------------------------------------------------------
# Position state
# ---------------------------------------------------------------------------

@dataclass
class PositionState:
    """Tracks current inventory for a single market."""
    yes_shares: int = 0         # FREE (доступно для Merge)
    no_shares: int = 0          # FREE (доступно для Merge)
    total_yes: int = 0          # TOTAL (все акции кошелька)
    total_no: int = 0           # TOTAL (все акции кошелька)
    yes_cost: float = 0.0
    no_cost: float = 0.0
    yes_in_flight: int = 0  # Акции в пути (отправлены, но нет подтверждения)
    no_in_flight: int = 0
    realized_ctf_pnl: float = 0.0 # Трекер прибыли от Merge

    # --- НОВЫЕ ПОЛЯ ДЛЯ ВЕЛОСИТИ (v3.0) ---
    session_merge_volume: float = 0.0    # Сколько долларов прокрутили через Merge
    profit_merges_count: int = 0        # Пар, схлопнутых в плюс (PS < 1.0)
    salvage_merges_count: int = 0       # Пар, схлопнутых в минус (PS > 1.0)

    @property
    def q(self) -> int:
        # [v11.64-ULTIMATE] Единственно верная формула экспозиции:
        # Акции в кошельке + Акции, обещанные к покупке в стакане
        total_y = self.total_yes + self.yes_in_flight
        total_n = self.total_no + self.no_in_flight
        return int(total_y - total_n)

    @property
    def total_cost(self) -> float:
        return self.yes_cost + self.no_cost

    @property
    def locked_pairs(self) -> int:
        """Количество захеджированных пар (замок)."""
        return min(self.total_yes, self.total_no)

    @property
    def active_total_cost(self) -> float:
        """
        [SHADOW ACCOUNTING] 
        Стоимость инвентаря за вычетом прибыльных/безубыточных замков.
        Используется только для фильтров и ценообразования.
        """
        y_avg = self.yes_cost / max(1, self.total_yes) if self.total_yes > 0 else 0.0
        n_avg = self.no_cost / max(1, self.total_no) if self.total_no > 0 else 0.0
        inv_ps = y_avg + n_avg
        
        # Если замок стоит <= 1.00, он не несет риска потери капитала
        if inv_ps <= 1.00 and self.locked_pairs > 0:
            locked_cost = self.locked_pairs * inv_ps
            return max(0.0, self.total_cost - locked_cost)
        return self.total_cost

    @property
    def imbalance_pct(self) -> float:
        total = self.yes_shares + self.no_shares
        if total == 0: return 0.0
        return abs(self.yes_shares - self.no_shares) / total * 100.0

    def apply_ctf_merge(self, size: int) -> tuple[float, float]:
        """Мгновенно списывает пары YES+NO. Возвращает цену схлопывания (Inv PS) и PnL."""
        if size <= 0 or self.yes_shares < size or self.no_shares < size:
            return 0.0, 0.0

        # 1. Считаем средние цены ДО списания
        y_avg = self.yes_cost / max(1, self.total_yes)
        n_avg = self.no_cost / max(1, self.total_no)
        inv_ps = y_avg + n_avg  # Цена, которую мы заплатили за одну полную пару

        # 2. Считаем PnL (Мы получаем $1.00 за пару, которая стоила нам inv_ps)
        merge_pnl = size * (1.0 - inv_ps)
        self.realized_ctf_pnl += merge_pnl

        # --- ОБНОВЛЕНИЕ БУХГАЛТЕРИИ ---
        self.session_merge_volume += (size * inv_ps) # Накапливаем оборот
        if inv_ps <= 1.0:
            self.profit_merges_count += size
        else:
            self.salvage_merges_count += size

        # 3. КРИТИЧЕСКОЕ ДЕЙСТВИЕ: Списываем акции и стоимость из инвентаря
        merged_yes_cost = size * y_avg
        merged_no_cost = size * n_avg
        
        self.yes_cost = max(0.0, self.yes_cost - merged_yes_cost)
        self.no_cost = max(0.0, self.no_cost - merged_no_cost)
        self.yes_shares -= size
        self.no_shares -= size
        self.total_yes -= size
        self.total_no -= size

        # --- [ФИКС УТЕЧКИ БАЛАНСА] ---
        if hasattr(self, 'total_cost') and not isinstance(getattr(type(self), 'total_cost', None), property):
            self.total_cost = max(0.0, self.total_cost - (merged_yes_cost + merged_no_cost))

        # Hard Reset: Привязываемся к TOTAL балансу.
        # Обнуляем стоимость только если в кошельке физически не осталось акций (включая In-Flight).
        if self.total_yes <= 0: 
            self.yes_cost = 0.0
        if self.total_no <= 0: 
            self.no_cost = 0.0
        if self.yes_shares <= 0 and self.no_shares <= 0 and hasattr(self, 'total_cost') and not isinstance(getattr(type(self), 'total_cost', None), property):
            self.total_cost = 0.0

        # 4. Логирование и статистика
        merge_type = "🟢 PROFIT" if merge_pnl >= 0 else "🔴 SALVAGE"
        
        
        logger.info(
            f"💰 [CTF_MERGE] {merge_type} | Схлопнуто: {size} пар | "
            f"INVPS: {inv_ps:.3f} | PnL: ${merge_pnl:+.4f} | "
            f"Остаток: Y{self.yes_shares}/N{self.no_shares}"
        )
        
        return inv_ps, merge_pnl

    def reset(self) -> None:
        """[v11.60-HFT] Полная очистка всех контуров баланса."""
        self.yes_shares = 0
        self.no_shares = 0
        self.total_yes = 0  # <--- ФИКС: Обнуляем общий баланс
        self.total_no = 0   # <--- ФИКС: Обнуляем общий баланс
        self.yes_cost = 0.0
        self.no_cost = 0.0
        self.yes_in_flight = 0
        self.no_in_flight = 0
        self.realized_ctf_pnl = 0.0




# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

@dataclass
class TickTelemetry:
    """Per-tick telemetry counters."""
    step_reached: str = ''
    gamma_eff: float = 0.0
    sigma_eff: float = 0.0
    as_delta: float = 0.0
    q: int = 0
    imbalance_pct: float = 0.0
    utilization: float = 0.0
    time_remaining: float = 0.0
    cancels: int = 0
    places: int = 0
    recovery_triggered: bool = False
    regime: str = "INIT"           # Добавляем это
    price_delta: float = 0.0       # Добавляем это
    spread: float = 0.0            # И это
    # --- НОВЫЕ МЕТРИКИ CYBORG ---
    fv: float = 0.50             # Справедливая цена (Оракул)
    deadband: float = 0.0        # Допустимый туннель перекоса
    penalty: float = 0.0         # Текущий штраф в центах
    # --- CVD SENSOR (ДИНАМИЧЕСКИЕ ПОРОГИ) ---
    cvd_sig: float = 0.0         # Текущее значение Oracle-Relative CVD
    cvd_momentum: float = 0.0    # Ускорение (Drop) за последние N секунд
    stress: float = 0.0          # Текущий уровень стресса бота (если он считается на тик)
    timestamp: float = 0.0       # UNIX-время тика (ОБЯЗАТЕЛЬНО для временного ряда!)

# ---------------------------------------------------------------------------
# GridStrategy
# ---------------------------------------------------------------------------

class GridStrategy:

    def __init__(self, config: GridConfig | None = None):
        self.config = config or GridConfig()
        self._unified_stress_level = 0.0
        self.defense_core = DualCoreDefense(self.config)
        self._defense_state = {} # Сюда будем складывать вердикт на каждом тике
        self._last_hunter_side = None

                # --- [ТЕСТОВЫЙ ДАМП КОНФИГА] ---
        try:
            if is_dataclass(self.config):
                cfg_dict = asdict(self.config)
            elif hasattr(self.config, '__dict__'):
                cfg_dict = vars(self.config)
            else:
                cfg_dict = str(self.config)
                
            # Выводим в лог красивым JSON-форматом с отступами
            import logging
            logging.getLogger('gabalog.grid_strategy').info(
                f"🚨 [CONFIG DUMP] Реальный конфиг в памяти бота:\n{json.dumps(cfg_dict, indent=2, default=str)}"
            )
        except Exception as e:
            import logging
            logging.getLogger('gabalog.grid_strategy').info(f"🚨 [CONFIG DUMP] Ошибка дампа ({e}), сырой вид: {self.config}")
        # -------------------------------
        
        # [CVD OBSERVER] инициализация
        self._cvd_raw = 0.0
        self._cvd_oracle = 0.0
        self._cvd_window_vol = 0.0
        self._cvd_tape = deque()
        self._cvd_last_log_ts = 0.0
        self._last_fv_for_cvd = 0.5
        # --- Добавлено для Контуров 2 и 3 (Удушение и Смещение) ---
        self._cvd_toxic_streak = 0
        self._cvd_signal_last = 0.0
        self._cvd_veto_active = False
        self._cvd_veto_ts     = 0.0
        self._cvd_history     = []  # список (timestamp, cvd_sig) для momentum

        # --- [MARKET REGIME FSM v2.4] ---
        self._market_regime      = 'NEUTRAL'   # 'NEUTRAL' / 'DIR' / 'TORPEDO' / 'RECOVERY'
        self._regime_entered_ts  = 0.0         # timestamp входа в текущий режим
        # [POST-TORPEDO COOLDOWN 2026-05-13] last NEUTRAL transition from TORPEDO/RECOVERY
        self._last_torpedo_exit_ts = 0.0
        self._cvd_fast_signal    = 0.0         # CVD fast window (6 сек)
        self._cvd_slow_signal    = None        # CVD slow window (45 сек), None если мало трейдов
        self._cvd_slow_tape      = deque()     # отдельный tape для slow window

        # --- ИНИЦИАЛИЗАЦИЯ ИНВЕНТАРЯ И СТАТИСТИКИ ---
        self.position = PositionState()
        self.recovery_attempts = 0
        self.paper_winner = None
        self.last_telemetry_pulse = {}

        self.vpin_buckets = deque()
        self.trade_tape = deque()
        
        # Статистика для финального отчета [FINAL_MARKET_REPORT]
        self.session_stats = {
            'profit_merges_count': 0, 
            'salvage_merges_count': 0, 
            'total_round_volume': 0.0
        }

        # --- ИНИЦИАЛИЗАЦИЯ ОРАКУЛОВ ---
        self.oracle_engine = OracleEngine()
        self.oracle_engine.config = self.config
        self._oracle_started = False
        self.oracle_fade_yes = False
        self.oracle_fade_no = False

        # --- ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРА ---
        self.grid_manager = GridManager(
            grid_levels=self.config.grid_levels,
            grid_spacing_ticks=self.config.grid_spacing_ticks,
            grid_lot_size=self.config.grid_lot_size,
            stale_threshold_ticks=self.config.stale_threshold_ticks,
            chase_threshold_ticks=self.config.chase_threshold_ticks,
            deep_level_static=self.config.deep_level_static,
            event_callback=self._emit_event,
        )
        self.grid_manager.fill_cooldown_sec = self.config.fill_cooldown_sec

        self.engine = None # Ссылка на движок (уже прокидывается адаптером)
        self._emergency_hunter_boost = 0.0

        self._last_momentum_log = 0.0
        self._last_vega_log = 0.0
        self._last_theta_log = 0.0
        self._last_iron_gate_log = 0.0
        self._last_maq_shift_log = 0.0
        self._last_maq_log_y = 0.0
        self._last_maq_log_n = 0.0
        self._current_proj_ps = 0.0

        # --- [NEW] Глобальные состояния системы (между тиками) ---
        self._current_oracle_weight = 1.0    # Начальное доверие Оракулу (100%)
        self._oracle_trust_state = 'NORMAL'  # Режим доверия (NORMAL / DISCONNECTED)
        self._is_panic_frozen = False        # Флаг заморозки DEFCON 1
        self._last_decision = 'NORMAL'       # Для анти-спама в логах (Decision Deduplication)
        self.defcon_risky_side = None        # <--- ДОБАВИТЬ ЭТУ СТРОКУ
        self._block_state = {'HEALER_CVD': False, 'MIRROR_CVD': False, 'HUNTER_SLEEP': False, 'SPACE_LOW': False}

        # --- [NEW] Таймеры для троттлинга логов (Анти-спам) ---
        self._last_math_log = 0.0
        self._last_xray_log = 0.0
        self._last_usd_lock_y = 0.0
        self._last_usd_lock_n = 0.0
        self._last_defcon_log = 0.0
        self._last_trust_shift_log = 0.0

        self.vpin_bucket_min = getattr(self.config, 'vpin_bucket_min', 1200.0)
        self.vpin_bucket_max = getattr(self.config, 'vpin_bucket_max', 2000.0)
        self.vpin_target_sec = getattr(self.config, 'vpin_target_sec', 10.0)

        # --- [NEW] Конфигурационные дефолты (Защита от отсутствия в YAML) ---
        
        # Блок 7: Dynamic Blending
        if not hasattr(self.config, 'oracle_blindness_thr'):   self.config.oracle_blindness_thr = 0.05
        if not hasattr(self.config, 'oracle_min_weight'):      self.config.oracle_min_weight = 0.20
        if not hasattr(self.config, 'oracle_recovery_rate'):   self.config.oracle_recovery_rate = 0.05
        
        # Блок 9: Dual Hard Cutoff
        if not hasattr(self.config, 'inventory_hard_cap'):     self.config.inventory_hard_cap = 25
        if not hasattr(self.config, 'open_q_sensitivity_cap'): self.config.open_q_sensitivity_cap = 60

        if not hasattr(self.config, 'side_usd_limit_pct'):     self.config.side_usd_limit_pct = 0.60
        if not hasattr(self.config, 'max_single_lot'):         self.config.max_single_lot = 15

        # Блок 6: Profit Gate
        if not hasattr(self.config, 'profit_gate_imb_max'):    self.config.profit_gate_imb_max = 15.0
        # [v12.2.2-PRO] Конфигурационные дефолты для контура выживания

        if not hasattr(self.config, 'hunter_max_gate'):        self.config.hunter_max_gate = 1.05
        if not hasattr(self.config, 'emergency_dump_slippage'): self.config.emergency_dump_slippage = 0.03

          # 2. Инструменты замера скорости (Velocity Tape)
        self.trade_tape = deque()  # Хранит кортежи: (timestamp, size)
        self.current_market_velocity = 0.0  # Текущая скорость (контракты в секунду)
        
        # 3. Состояние ведер
        self.current_bucket = {'buy_vol': 0.0, 'total_vol': 0.0, 'start_ts': time.time()}
        
        # --- [NEW] ФЛАГИ СОСТОЯНИЯ (Для логики ENTER/EXIT) ---
        self._lock_yes_active = False
        self._lock_no_active = False
        self._hunter_mutex_active = False
        
        # СТАЛО (Добавить в __init__)
        self._last_theta_log = 0.0          # Таймер для форензика времени

        # --- СОСТОЯНИЯ ДЛЯ ЭКСТРЕННОГО СБРОСА ---
        self._emergency_dump_fired = False  # Флаг принудительного сброса (Full House)
        self._last_dump_ts = 0.0            # Таймер кулдауна между сбросами

        # --- [v15] ED TRIAGE MATRIX ---
        self._ed_level = 0                  # 0=NORMAL, 1=PROFIT_SHIELD, 2=YELLOW_ZONE, 3=RED_ZONE
        self._ed_level_enter_ts = 0.0       # Момент входа в текущий уровень
        self._ed_q_history = deque(maxlen=30)  # История Q за последние 30 тиков (для ΔQ)
        self._ed_survivor_lock_side = None  # Сторона под карантином (None / 'YES' / 'NO')
        self._ed_yellow_urgency = 0.0       # Накопленная urgency в Yellow Zone
        self._ed_last_maker_sell_ts = 0.0   # Таймер Maker-продаж в Yellow Zone
        self._bankrupt_sides = set()        # Множество сторон под Survivor Lock

        # self._endgame_fade_start_sec = 300 # (С какой секунды начинается сжатие инвентаря. По умолчанию 5 минут).
        logging.getLogger('gabalog.grid_strategy').info(
        f"🛠 [INIT] Endgame Fade Start: {self.config.endgame_fade_start_sec}s"
        )

        # 4. Итоговый выходной сигнал
        self.last_trade_ts = time.time()

        self._last_iron_gate_log = 0.0      # Таймер для логов блокировки по PS
        self._last_iron_gate_status = False # Статус для отслеживания входа/выхода

        # Risk state
        self._session_pnl: float = 0.0
        self._session_peak_pnl: float = 0.0
        self._drawdown_stopped: bool = False

        self._total_fills = 0
        self._total_cancels = 0

        # Флаги Veto
        self._veto_yes_active = False
        self._veto_no_active = False

        # Maker Volume tracking (for rebate estimation)
        import time as _t
        self._maker_volume_usd: float = 0.0
        self._maker_fills_count: int = 0
        self._volume_reset_date: str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Fill at Peak detection (adverse selection metric)
        self._peak_fills: int = 0
        self._total_fills_tracked: int = 0
        self._peak_fill_cost: float = 0.0
        

        # API request counter (for dashboard)
        self._api_requests_total: int = 0
        self._api_requests_window: list = []  # [(timestamp, count)]

        # Market Tape — event buffers for dashboard
        self._order_events = deque(maxlen=500)  # live: last 50 events for WS
        self._regime_history = deque(maxlen=900)  # ~5 min at 1 tick/sec
        self._market_tape_log: list = []       # full: all events for post-market PNG
        self._last_orderbook: dict = {}        # last seen orderbook for get_live_state

        self.last_telemetry = TickTelemetry()  # Защита от краша

        # --- HFT STRESS & DECAY STATE ---
        self._last_tick_ts = time.time()
        self._current_stress_multiplier = 1.0  # Текущий множитель стресса
        self._last_fade_ts_no = 0.0
        self._last_fade_ts_yes = 0.0
        self._fade_active_yes = False
        self._fade_active_no = False
        self._pending_merge_size = 0
        self._pending_merge_ts = 0.0
        self._pending_merge_side = ""
        self._merge_state = 'IDLE' # Состояния: IDLE, PREPARING, EXECUTING
        self._log_cooldowns = {} # [v11.56] Анти-спам таймеры для DECISION
        self._block_state = {'HEALER_CVD': False, 'MIRROR_CVD': False, 'HUNTER_SLEEP': False, 'SPACE_LOW': False}

        # --- [FORENSICS & STATE INITIALIZATION] ---
        self._fills_this_tick = 0
        self._is_official_strike = False
        self._current_profit_buffer = 0.0
        self.current_fv = 0.50
        self.last_effective_scale = self.config.inventory_scale_shares
        self.last_adaptive_edge = self.config.target_edge
        self._pre_pull_ticks_left = 0
        self._toxic_position_ticks = 0
        self._is_dumping_in_flight = False
        self._last_dump_time = 0.0
        self._smooth_stress = 0.0
        # [v14.7 Forensic] State Tracking
        self._last_intent = "NORMAL"
        
        # [v14.7-CORE] Триаж-инициализация
        self._triage_active_side = None
        self._triage_decision = "NONE"
        self._current_patience = 0
        self._last_expected_pnl = 0.0

        # Добавить в конец __init__ И в on_market_switch:
        self._consensus_charge = 0.0        # Накопленный "заряд" (сек)
        self._consensus_confirmed = False   # Флаг капитуляции
        self._consensus_peak = 0.5          # Точка экстремума для замера отката
        self._last_consensus_ts = time.time()

        # --- [v14.2 HEALER INITIALIZATION] ---
        self._last_toxic_recovery_log = 0.0
        self._current_proj_ps = 0.0  # Для мониторинга Iron Gate

        # --- [v14.5 ELASTIC INITIALIZATION] ---
        self._last_maq_log_y = 0.0
        self._last_maq_log_n = 0.0
        self._last_anti_panic_log = 0.0

        # [v14.6-CORE] Mutex: Память о сброшенных сторонах (Survivor Lock)
        self._bankrupt_sides = set()

    
    # ------------------------------------------------------------------
    # Live state export (for dashboard)
    # ------------------------------------------------------------------

    def get_live_state(self) -> dict:
        """Export current state for dashboard (v7.9 Optimized)."""
        import time as time_module

        # Снапшот ордеров
        pending = [{'side': p.side, 'price': p.price, 'size': p.size} for p in self.grid_manager.pending_orders.values()]
        pending_sells = [{'side': info['side'], 'price': info['price'], 'size': info['size'], 'type': 'sell'} for info in self.grid_manager.pending_sell_orders.values()]
        
        # [PHASE 1] Интеграция Rolling CFR и FTC %
        engine = getattr(self, 'engine', None)
        live_cfr = engine.get_live_cfr() if engine else 0.0
        
        # Считаем FTC Ratio на основе живой истории из двигателя (200 событий)
        history = list(getattr(engine, '_action_history', []))
        f_count = history.count('F')
        c_count = history.count('C')
        # Итоговый процент эффективности (сколько % действий привели к филлу)
        ftc_ratio = (f_count / max(1, f_count + c_count)) * 100


        # Телеметрия
        tel = self.last_telemetry if self.last_telemetry is not None else TickTelemetry()

        # Подготовка чистых чисел инвентаря (TOTAL для UI, FREE для логики)
        y_sh_total = int(round(self.position.total_yes))
        n_sh_total = int(round(self.position.total_no))
        y_avg = float(self.position.yes_cost / max(1, y_sh_total)) if y_sh_total > 0 else 0.0
        n_avg = float(self.position.no_cost / max(1, n_sh_total)) if n_sh_total > 0 else 0.0
        
        # Честный IMB по общим остаткам
        total_inv = y_sh_total + n_sh_total
        imb_val = (abs(y_sh_total - n_sh_total) / total_inv * 100.0) if total_inv > 0 else 0.0

        return {
            'strategy': 'grid_v6',
            'slug': getattr(self, '_c_mkt', 'unknown'),
            'events': list(self._order_events),
            'time_left_sec': tel.time_remaining,
            'shadow_forensics': {
                'realized_ctf_pnl': float(round(self.position.realized_ctf_pnl, 4)),
                'profit_buffer': round(getattr(self, '_current_profit_buffer', 0.0), 4),
                'strike_verified': bool(self._is_official_strike),
                'fills_this_tick': int(self._fills_this_tick)
            },
            'timestamp': time_module.time(),
            'yes_shares': y_sh_total,
            'no_shares': n_sh_total,
            'total_cost': round(float(self.position.total_cost), 2),
            'q': y_sh_total - n_sh_total,
            'imbalance_pct': round(imb_val, 1),
            'orderbook': self._last_orderbook,

            'position': {
                'yes_shares': y_sh_total,
                'no_shares': n_sh_total,
                'yes_avg_price': round(y_avg, 3),
                'no_avg_price': round(n_avg, 3),
                'yes_cost': round(float(self.position.yes_cost), 2),
                'no_cost': round(float(self.position.no_cost), 2),
                'total_cost': round(float(self.position.total_cost), 2),
                'imbalance_pct': round(imb_val, 1),
                'realized_ctf_pnl': round(self.position.realized_ctf_pnl, 4),
            },
            'edge': {
                'all_in_sum': round(y_avg + n_avg, 3) if (y_sh_total > 0 and n_sh_total > 0) else 0.0,
                'edge_pct': round(getattr(self, 'last_telemetry', TickTelemetry()).as_delta * 100, 2),
                'fair_odds': round(getattr(self, 'current_fv', 0.5), 3),
                'ctf_pnl': round(self.position.realized_ctf_pnl, 4),
                # --- [FIX] СЛОВАРЬ ДЛЯ ИНВЕСТОРОВ ---
                'merge_stats': {
                    'volume': round(self.position.session_merge_volume, 2),
                    'velocity': round(self.position.session_merge_volume / max(1.0, self.config.deposit), 2),
                    'profit_count': getattr(self.position, 'profit_merges_count', 0),
                    'salvage_count': getattr(self.position, 'salvage_merges_count', 0)
                },
                # Считаем PnL от ОБЩЕГО количества акций, а не только от свободных
                'pnl_if_yes': round(float(self.position.total_yes - self.position.total_cost), 2),
                'pnl_if_no': round(float(self.position.total_no - self.position.total_cost), 2),
            },
            'stats': {
                'bankroll_usd': float(getattr(self.config, 'deposit', 150) * 2),
                'deposit_usd': float(getattr(self.config, 'deposit', 150)),
                'max_position_pct': 0.5,
                'ftc_ratio_pct': round(ftc_ratio, 2), 
                'total_fills': getattr(self, '_total_fills', 0),    # Добавили счетчик сделок
                'total_cancels': getattr(self, '_total_cancels', 0),
                'edge_pct': round(tel.as_delta * 100, 2),
                'live_cfr': live_cfr  # Прокидываем в дашборд
            },
            'maker_volume': {
                'daily_usd': round(self._maker_volume_usd, 2),
                'daily_fills': self._maker_fills_count,
                'date': self._volume_reset_date,
            },
            'api_rate': {
                'per_min': self.api_requests_per_min,
                'total': self._api_requests_total,
            },
            'pending_orders': pending,
            'pending_sells': pending_sells,
            'order_events': list(self._order_events),

            'telemetry': self.last_telemetry_pulse if hasattr(self, 'last_telemetry_pulse') else {},
                
        }

    def dump_market_tape(self, condition_id: str, bot_id: str = 'btc_5m') -> str:
        """Save full market tape log for post-market replay PNG.

        Called by adapter/bridge at market settlement.
        Returns path to saved file.
        """
        import json
        from pathlib import Path

        tape_dir = Path(__file__).parent.parent.parent / 'logs' / 'market_tapes'
        tape_dir.mkdir(parents=True, exist_ok=True)
        tape_file = tape_dir / f'{bot_id}_{condition_id}.json'

        with open(tape_file, 'w') as f:
            json.dump({
                'condition_id': condition_id,
                'bot_id': bot_id,
                'events_count': len(self._market_tape_log),
                'config': {
                    'deposit': self.config.deposit,
                    'grid_levels': self.config.grid_levels,
                    'grid_lot_size': self.config.grid_lot_size,
                    'hard_cutoff_shares': getattr(self, '_dynamic_hard_cutoff', 350),
                },
                'events': self._market_tape_log,
            }, f)

        return str(tape_file)

    # ------------------------------------------------------------------
    # Market Tape event logging
    # ------------------------------------------------------------------

    def _emit_event(self, event_type: str, side: str, price: float, size: int, is_taker: bool = False, intent: str = 'UNKNOWN'):
        """Record order event to both live buffer and full tape log."""
        event = {
            'type': event_type,  # 'fill' | 'cancel' | 'place' | 'sell_fill'
            'side': side,        # 'YES' | 'NO'
            'price': round(price, 4),
            'size': size,
            'ts': time.time(),
            'is_taker': is_taker, 
            'intent': intent,    # <--- [PATCH] Передаем автора сделки на фронт
        }
        self._order_events.append(event)
        self._market_tape_log.append(event)

    def _calculate_implied_strike(self, current_btc: float, mid_market: float, time_rem: float, vol_ratio: float) -> Optional[float]:
        """
        Математика v14.0: Вычисление страйка на основе рыночного консенсуса (стакана).
        Использует аппроксимацию erfinv.
        """
        if time_rem <= 60: return None # Не калибруем в конце
        
        # Повторяем параметры сигмы из основной модели для точности
        dur = self.config.market_duration_sec
        time_factor = max(0.05, time_rem / dur)
        adaptive_mult = math.sqrt(max(0.5, min(vol_ratio, 10.0)))
        sigma = current_btc * 0.008 * math.sqrt(time_factor) * adaptive_mult
        
        try:
            # Приближенная инверсия функции ошибок (erfinv) для малых значений
            # z = sqrt(pi)/2 * ( (p - 0.5) * ... )
            # Для HFT используем упрощенную логику нормального распределения
            p_clamped = max(0.01, min(mid_market, 0.99))
            # Приблизительный расчет Z-score из вероятности (Price)
            z_implied = -1.58 * math.log(1.0 / p_clamped - 1.0) / (1.0 + 0.1 * abs(math.log(1.0 / p_clamped - 1.0)))
            
            # Strike = BTC - (Z * Sigma)
            return round(current_btc - (z_implied * sigma), 2)
        except:
            return None 

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def _calculate_dynamic_pricing(self, vol_ratio: float):
        """[MOD 2] Elastic Profit Engine (Unified Stress)."""
        v_factor = max(1.0, vol_ratio)
        base_edge = self.config.edge_min + (self.config.edge_vol_sensitivity * math.log(v_factor))
        
        # Читаем единый стресс
        stress = getattr(self, '_unified_stress_level', 0.0)
        p_mult = getattr(self.config, 'vpin_penalty_max', 3.5) # Конфиг пока не переименовываем
        toxic_mult = 1.0 + (stress * p_mult)
        
        self.config.target_edge = round(min(self.config.edge_max, base_edge * toxic_mult), 4)
        self.config.max_penalty_dev = round(self.config.target_edge * 3.0, 4)
        self.config.recovery_discount_cents = round(self.config.target_edge * 1.2, 4)

    def _calculate_dynamic_trust(self, vol_ratio: float):
        """[MOD 5] Smooth Trust & Veto (Unified Stress)."""
        base_drift = getattr(self.config, 'oracle_drift_threshold', 0.08)
        vol_boost = math.sqrt(max(1.0, vol_ratio))
        raw_b_thr = base_drift * vol_boost * self.config.blindness_vol_sens
        self.config.oracle_blindness_thr = round(max(self.config.blindness_floor, raw_b_thr), 4)

        # Штраф доверия на основе единого стресса
        stress = getattr(self, '_unified_stress_level', 0.0)
        smooth_mult = 1.0 + math.pow(stress, getattr(self.config, 'vpin_power', 2.0)) * (getattr(self.config, 'vpin_penalty_max', 3.5) - 1.0)
        self._live_stress_penalty = round(smooth_mult, 3)

    def _apply_triage_logic(self, market_data: dict, q: int, t_rem: float, target: list[GridLevel]) -> list[GridLevel]:
        """[MOD 6] Unified Triage Gateway (Persistent)."""
        if not self.config.emergency_dump_enabled: return target

        # 1. Квадратичное терпение (Theta Decay)
        t_f = max(0.0, min(1.0, t_rem / self.config.market_duration_sec))
        raw_pat = int(self.config.max_patience_ticks * (t_f ** 2))
        self._current_patience = max(5, raw_pat) if t_rem > 120 else raw_pat
        
        # 2. Latch Logic (С защитой от переворота)
        heavy_side = 'YES' if q > 0 else 'NO'
        safe_q = getattr(self.config, 'toxic_q_safe', 5)
        
        # [v15.9] Детектор переворота инвентаря
        # Если в памяти одна сторона, а по факту перекос в другую - это FLIP
        inventory_flipped = (self._triage_active_side and self._triage_active_side != heavy_side)

        if (self._toxic_position_ticks > self._current_patience and abs(q) > safe_q) or inventory_flipped:
            # Если инвентарь перевернулся, МГНОВЕННО переключаем сторону дампа
            if inventory_flipped:
                logging.getLogger('gabalog.grid_strategy').warning(f"🔄 [TRIAGE_FLIP] Side reset: {self._triage_active_side} -> {heavy_side} (Q:{q})")
            
            self._triage_active_side = heavy_side
            
        elif abs(q) <= safe_q:
            self._triage_active_side = None
            self._triage_decision = "NONE"
            return target

        if not self._triage_active_side: return target

        side = self._triage_active_side
        
        # [v14.9.5] HANDSHAKE PROTOCOL
        # Если Охотник (is_desperate) уже работает над этой ногой, 
        # Триаж не должен удалять ордера, пока не пришло время TAKER_DUMP.
        is_hunter_active = (abs(q) > self.config.hunter_imb_threshold)
        if is_hunter_active and "TAKER_DUMP" not in self._triage_decision:
            return target 

        # Сначала определяем данные!
        bid_p = market_data.get(f'{side.lower()}_bid', 0.0)
        floor = self.config.emergency_price_floor
        fv_now = getattr(self, 'current_fv', 0.5)
        fv_side = fv_now if side == 'YES' else (1.0 - fv_now)

        # --- [v16.0] UNIFIED DECISION ENGINE ---
        # Очищаем таргет от старых ордеров этой стороны, чтобы не мешали дампу
        target = [lvl for lvl in target if lvl.side != side]
        
        # 1. Проверяем возможность Taker-удара (мгновенный выход)
        if bid_p >= floor:
            # Если цена в стакане выше нашего "пола" — отдаем команду на TAKER_DUMP.
            # Само исполнение (OrderAction) произойдет в основном цикле on_tick.
            self._triage_decision = f"TAKER_DUMP({bid_p:.2f})"
        else:
            # 2. РЕЖИМ RECOVERY (Бид ниже пола, пытаемся "выцепить" филл лимиткой)
            # Считаем динамический дисконт на основе стресс-метрик (0.02 -> 0.06)
            stress_factor = getattr(self, '_smooth_stress', 0.5)
            dynamic_discount = 0.02 + (0.04 * stress_factor)
            
            # Находим целевую цену выхода относительно Оракула
            target_exit_p = fv_side - dynamic_discount
            
            # Агрессивный перехват: мы должны стоять не выше текущего бида
            # (даже если он ниже пола, мы пытаемся быть первыми в очереди на слив)
            recovery_p = min(bid_p, target_exit_p) if bid_p > 0.01 else target_exit_p
            
            # Финальный зажим: не падаем ниже floor, если только FV не заставит
            recovery_p = max(floor, round(recovery_p, 2))
            
            # Размер ордера спасения (используем % из конфига)
            dump_pct = getattr(self.config, 'emergency_dump_sell_pct', 0.4)
            recovery_qty = max(self.config, 'grid_lot_size', int(abs(q) * dump_pct))

            # Впрыскиваем лимитку спасения в таргет
            target.append(GridLevel(
                side=side, 
                price=recovery_p, 
                size=recovery_qty, 
                level_idx=0
            ))
            
            self._triage_decision = f"RECOVERY({recovery_p:.2f})"
            
        return target

    def on_tick(self, market_data: dict) -> list[OrderAction]:

        # === [STEP 0: SENSOR GATHERING] ===
        tick_start_time = time.time()
        now = time.time()
         
        m_slug = market_data.get('slug', 'unknown')

        # === [CRITICAL PATCH: STRIKE SYNC FIX] ===
        # Читаем ПРАВИЛЬНЫЙ ключ из твоей даты
        _is_off_strike = market_data.get('is_official_strike', False)
        if _is_off_strike and not getattr(self, '_history_wiped_for_strike', False):
            self._price_history = [] 
            self._history_wiped_for_strike = True
            logger.critical("🪦🎯 [STRIKE_SYNC] Официальный страйк зафиксирован. История очищена ДО расчета Velocity.")

            logging.getLogger('gabalog.grid_strategy').critical(
                f"🎯🧹 [STRIKE_SYNC_WIPE] Память оракула сброшена! Начинаем новый цикл со страйком {market_data.get('strike_price')}"
            )
        # =========================================

        # --- [v14.7-CORE] ГАРАНТИЯ ИНИЦИАЛИЗАЦИИ (Защита от UnboundLocalError) ---
        target = []
        actions = []
        recovery_tag = ""
        diagnosis = "INIT"          # <--- КРИТИЧНО для лога
        new_weight = 1.0            # <--- КРИТИЧНО для лога
        is_readonly = False         # <--- КРИТИЧНО для логики
        q = self.position.q         # глобальный q — только для Iron Gate,
                                    # Orchestrator и Triage. Нигде больше.
        adaptive_edge = 0.038
        oracle_fv = market_data.get('yes_bid', 0.5) # Это твой Initial placeholder
        fv_yes = oracle_fv


        l0_y = 0.0
        l0_n = 0.0
        TICK_SIZE = 0.01
        is_deadlocked = False
        _weak_side = None
        _probe_safe = 0.0
        hunter_gate = getattr(self.config, 'profit_gate_ps_max', 0.985)
        m_state = "INIT"      
        p_yes = 0.0
        p_no = 0.0
        effective_scale = 10.0
        active_gate_limit = 0.995

        # [v14.5-STABLE FIX] Немедленная распаковка цен для Пульса
        yes_bid = market_data.get('yes_bid', 0.5)
        yes_ask = market_data.get('yes_ask', 0.5)
        no_bid = market_data.get('no_bid', 0.5)
        no_ask = market_data.get('no_ask', 0.5)

        api_latency = market_data.get('api_latency_ms', 0)
        max_rtt = getattr(self.config, 'hft_latency_halt_ms', 250.0)
        engine = getattr(self, 'engine', None)
        current_cfr = engine.get_live_cfr() if engine else 0.0
        is_throttled = engine and now < engine._throttle_until

        # 1. ТАЙМИНГ И ПРОГРЕСС
        raw_t_rem = float(market_data.get('time_remaining_sec', self.config.market_duration_sec))
        
        # Защита от timestamp в миллисекундах
        if raw_t_rem > self.config.market_duration_sec * 10:
            raw_t_rem /= 1000.0
            
        # Жестко зажимаем время в рамках [0, market_duration_sec]
        time_rem_sec = max(0.0, min(raw_t_rem, float(self.config.market_duration_sec)))

        # --- ЖУЧОК [TIME_JUMP] ---
        _last_t = getattr(self, '_prev_time_rem', time_rem_sec)
        if abs(_last_t - time_rem_sec) > 10.0 and time_rem_sec > 0:
            logging.getLogger('gabalog.grid_strategy').error(
                f"🪦🚨 [TIME_JUMP] Временной скачок! Было: {_last_t:.1f}s | Стало: {time_rem_sec:.1f}s"
            )
        self._prev_time_rem = time_rem_sec

        t_rem = int(time_rem_sec)
        time_passed = self.config.market_duration_sec - time_rem_sec
        
        # Рассчитываем коэффициент прогресса (1.0 в начале -> 0.0 в конце)
        t_f = max(0.0, min(1.0, time_rem_sec / self.config.market_duration_sec))
        # Форензик-логирование времени раз в 30 сек
        if now - getattr(self, '_last_theta_log', 0) > 30.0:
            logging.getLogger('gabalog.grid_strategy').info(f"⏳ [THETA_CORE] Progress: {t_f:.2f} | Time_Left: {time_rem_sec:.0f}s")
            self._last_theta_log = now

        # --- [!] ВОТ ЭТИ 3 СТРОКИ НУЖНО ДОБАВИТЬ ---
        # Сначала считаем сырой перекос и достаем чистый риск (open_q) из Shadow Book
        q_current = (self.position.yes_shares + self.position.yes_in_flight) - \
                    (self.position.no_shares + self.position.no_in_flight)
        
        shadow = self._compute_shadow_accounting(q_current)
        open_q = shadow.get('open_q', q_current)
        # --------------------------------------------

        # --- [ПАТЧ 1: Средо-зависимая емкость] ---
        cvd_toxic = getattr(self, '_cvd_toxic_streak', 0) > 2
        _target_mult = 0.4 if cvd_toxic else 1.0
        _prev_mult = getattr(self, '_env_multiplier_smooth', 1.0)
        # Быстро сжимаемся (alpha=0.5), медленно расширяемся (alpha=0.05)
        _alpha = 0.5 if _target_mult < _prev_mult else 0.05
        env_multiplier = _alpha * _target_mult + (1 - _alpha) * _prev_mult      

        self._env_multiplier_smooth = env_multiplier
        
        cap = getattr(self.config, 'open_q_sensitivity_cap', 60)
        inv_load = min(1.0, abs(open_q) / max(1, cap))
        
        hc_max = getattr(self.config, 'hard_cutoff_max', 35) * env_multiplier
        hc_min = getattr(self.config, 'hard_cutoff_min', 7) * env_multiplier
        
        dyn_hc = hc_max - ((hc_max - hc_min) * inv_load)
        self._dynamic_hard_cutoff = max(int(hc_min), int(dyn_hc))

        # --- ЖУЧОК [CAPACITY_CRUSH] (ТЕПЕРЬ ТУТ) ---
        if env_multiplier < 0.6:
            _now = time.time()
            if _now - getattr(self, '_last_cap_crush_log', 0) > 15.0:
                logging.getLogger('gabalog.grid_strategy').warning(
                    f"🪦☢️🦾 [CAPACITY_CRUSH] Емкость рынка подавлена! Mult: {env_multiplier:.2f} | "
                    f"CVD_Toxic: {cvd_toxic} | HC: {self._dynamic_hard_cutoff} | {self._std_ctx()}"
                )
                self._last_cap_crush_log = _now

        # 2.2 Hunter Threshold (ГИБРИД: Твой конфиг + Защита глиссады)
        # Читаем твои 15 из YAML
        yaml_thr = int(getattr(self.config, 'hunter_imb_threshold', 20))
        
        # --- [ГЛОБАЛЬНЫЙ КОНТРОЛЬ ДИСБАЛАНСА v2.5] ---
        total_sh = self.position.yes_shares + self.position.no_shares
        fv_distance = abs(getattr(self, 'current_fv', 0.5) - 0.5)
        fv_fear_mult = max(0.25, 1.0 - (fv_distance * 2.0) ** 2)
        tolerance_pct = getattr(self.config, 'hunter_imb_tolerance_pct', 0.10)
        dynamic_from_gross = int(total_sh * tolerance_pct)
        base_thr = max(yaml_thr, dynamic_from_gross)
        self._dynamic_hunter_thr = max(3, int(base_thr * fv_fear_mult))
        # --------------------------------------------------

        # 2.3 Inventory Scale (30% от стены - пружина штрафа)
        dyn_is = max(2.0, dyn_hc * 0.3)
        self._dynamic_inventory_scale = dyn_is
        
        # 2.4 Deadband (Линейное исчезновение комфорта)
        cfg_db = getattr(self.config, 'base_deadband', 3.0)
        dyn_base_deadband = cfg_db * t_f 

        # 3. ОБНОВЛЕНИЕ ДИНАМИЧЕСКИХ ДВИЖКОВ (Module 2 & 5)
        current_vol_ratio = market_data.get('vol_ratio', 1.0)
        
        # --- [v16.7] UNIVERSAL ADAPTIVE ENGINE ---
        # Считаем множители один раз за тик
        v_ratio = current_vol_ratio
        
        # Адаптация СТЕНОК ведра (для on_trade)
        # В штиль стенки: 1200 - 8000. В шторм: 500 - 3000.
        self.vpin_bucket_min = max(500.0, min(1200.0, 1200.0 / math.sqrt(v_ratio)))
        self.vpin_bucket_max = max(3000.0, min(8000.0, 8000.0 / v_ratio))
        
        # Адаптация ОКНА ПАМЯТИ (для on_trade)
        self.config.vpin_window_buckets = 2 if v_ratio < 1.5 else 3

        # Адаптация ПРЕДОХРАНИТЕЛЕЙ (для on_tick)
        base_suppress = 0.98
        current_suppress_thr = max(0.85, min(0.99, base_suppress / (v_ratio ** 0.08)))
        self.config.garbage_dist_base = max(0.03, min(0.07, 0.07 / v_ratio))
        # -----------------------------------------

        self._calculate_dynamic_pricing(current_vol_ratio)
        self._calculate_dynamic_trust(current_vol_ratio)
        
        # Пред-расчет мида и получение BTC
        mid_market = ((yes_bid + yes_ask)/2.0 + (1.0 - (no_bid + no_ask)/2.0)) / 2.0
        p_obj = self.config.shared_btc_price
        current_btc = p_obj.value if hasattr(p_obj, 'value') else float(p_obj or 0)
        if current_btc == 0: current_btc = market_data.get('btc_price', 0.0)

        # =========================================

        safety = self._run_safety_and_merge(
            market_data=market_data, time_rem_sec=time_rem_sec,
            yes_bid=yes_bid, no_bid=no_bid,
        )
        if safety.get('early_exit'):
            return safety['actions']

        is_warmup    = safety['is_warmup']
        api_latency  = safety['api_latency']
        max_rtt      = safety['max_rtt']
        live_cfr     = safety['live_cfr']
        is_throttled = safety['is_throttled']
        is_readonly  = safety['is_readonly']
        hedged_pairs = safety['hedged_pairs']

        # Этап 12 — первым, даёт q, fv_yes, time_rem_sec и всё остальное
        oracle_prep = self._run_oracle_data_prep(
            market_data=market_data, yes_bid=yes_bid, yes_ask=yes_ask,
            no_bid=no_bid, no_ask=no_ask, q=q, oracle_fv=oracle_fv,
            actions=actions, target=target, is_readonly=is_readonly,
            l0_y=l0_y, l0_n=l0_n,
        )
        current_btc        = oracle_prep['current_btc']
        strike             = oracle_prep['strike']
        mid_market         = oracle_prep['mid_market']
        oracle_fv          = oracle_prep['oracle_fv']
        fv_yes             = oracle_prep['fv_yes']
        self._last_fv_for_cvd = oracle_fv  # [CVD OBSERVER] снапшот FV для on_trade
        momentum_side_lock = oracle_prep['momentum_side_lock']
        is_data_corrupt    = oracle_prep['is_data_corrupt']
        is_readonly        = oracle_prep['is_readonly']
        actions            = oracle_prep['actions']
        target             = oracle_prep['target']
        l0_y               = oracle_prep['l0_y']
        l0_n               = oracle_prep['l0_n']

        # Этап 2  — shadow accounting   ← вот тут q уже есть        
        shadow = self._compute_shadow_accounting(q)
        MAX_SKEW_DELTA       = shadow['MAX_SKEW_DELTA']
        active_y_shares      = shadow['active_y_shares']
        active_n_shares      = shadow['active_n_shares']
        y_avg_price          = shadow['y_avg_price']
        n_avg_price          = shadow['n_avg_price']
        is_inventory_healthy = shadow['is_inventory_healthy']
        eval_y_shares        = shadow['eval_y_shares']
        eval_n_shares        = shadow['eval_n_shares']
        eval_y_cost          = shadow['eval_y_cost']
        eval_n_cost          = shadow['eval_n_cost']
        # [SHADOW BOOK v2.0]
        open_q            = shadow['open_q']
        locked_pairs_cost = shadow['locked_pairs_cost']
        open_cost         = shadow['open_cost']

        gate = self._compute_elastic_iron_gate(
            q=q, time_rem_sec=time_rem_sec, oracle_fv=oracle_fv,
        )
        active_gate_limit = gate['active_gate_limit']
        hc_limit          = gate['hc_limit']

        preflight = self._run_preflight(
            market_data=market_data, api_latency=api_latency, max_rtt=max_rtt,
            is_throttled=is_throttled, target=target, current_btc=current_btc,
            strike=strike, fv_yes=fv_yes, oracle_fv=oracle_fv,
            active_gate_limit=active_gate_limit, yes_bid=yes_bid, yes_ask=yes_ask,
            no_bid=no_bid, no_ask=no_ask, q=q, p_yes=p_yes, p_no=p_no,
            adaptive_edge=adaptive_edge, effective_scale=effective_scale,
            m_slug=m_slug, current_cfr=current_cfr, now=now,
        )
        if preflight.get('early_exit'):
            return preflight['actions']

        status_tag           = preflight['status_tag']
        base_lot             = preflight['base_lot']
        final_lot_y          = preflight['final_lot_y']
        final_lot_n          = preflight['final_lot_n']
        current_cfr          = preflight['current_cfr']
        inv_load             = preflight['inv_load']
        required_sec         = preflight['required_sec']
        current_dump_mult    = preflight['current_dump_mult']
        dyn_share_limit_y    = preflight['dyn_share_limit_y']
        dyn_share_limit_n    = preflight['dyn_share_limit_n']
        actions              = preflight['actions']
        is_medical_averaging = preflight['is_medical_averaging']
        is_desperate         = preflight['is_desperate']
        tick_start_time      = preflight['tick_start_time']
        tel                  = preflight['tel']

        # [INVENTORY PANIC] Принудительный desperate при критическом перекосе
        hunter_thr = getattr(self, '_dynamic_hunter_thr', getattr(self.config, 'hunter_imb_threshold', 15))
        is_healing = recovery_tag != "" and "🩺" in recovery_tag

        # 1. is_desperate — бинарный для downstream совместимости
        # _intent_load [0.0-1.0] — градиентная замена, читается из self._intent_load
        is_desperate = getattr(self, '_intent_load', 0.0) > 0.70

        # 2. Оставляем маркировку для логов, если Лекарь работает до включения Охотника
        if is_healing and not is_desperate:
            recovery_tag += "⚡[SYNC]"

            # Этап 3  — velocity
        eff_delta = self._compute_velocity(tick_start_time, fv_yes, current_btc)

        # Этап 7  — oracle pipeline
        oracle = self._run_oracle_pipeline(
            tick_start_time=tick_start_time, eff_delta=eff_delta,
            oracle_fv=oracle_fv, mid_market=mid_market,
            time_rem_sec=time_rem_sec, strike=strike,
            current_btc=current_btc, current_vol_ratio=current_vol_ratio,
            q=q, time_passed=time_passed,
        )
        if oracle.get('early_exit'):
            return oracle['actions']

        new_weight   = oracle['new_weight']
        diagnosis    = oracle['diagnosis']
        fv_yes       = oracle['fv_yes']
        oracle_fv    = oracle['oracle_fv']
        m_state      = oracle['m_state']
        time_passed  = oracle['time_passed']
        strike       = oracle['strike']    

        # [ИНТЕГРАЦИЯ DUAL-CORE DEFENSE]
        # 1. Забираем свежие сенсоры
        cvd_val = getattr(self, '_cvd_signal_last', 0.0)
        q_val = getattr(self.position, 'q', 0) # Твой чистый риск
        
        # 2. Получаем вердикт управляющего контура
        if hasattr(self, 'defense_core') and not getattr(self, '_is_at_dead_pole', False):
            self._defense_state = self.defense_core.evaluate(cvd_val, q_val)
        else:
            self._defense_state = {}
        # --------------------------------

        # Этап 4  — auto_armor
        armor = self._compute_auto_armor(
            market_data=market_data, oracle_fv=oracle_fv, mid_market=mid_market,
            yes_ask=yes_ask, yes_bid=yes_bid, no_ask=no_ask, no_bid=no_bid,
            time_passed=time_passed, t_f=t_f,
            open_q=open_q,
        )
        self._last_open_q = open_q
        self._last_t_rem = time_rem_sec
        # [FILL_CTX] Сохраняем инвентарное здоровье
        _y = (self.position.yes_cost / max(1, self.position.total_yes)) if self.position.total_yes > 0 else 0.0
        _n = (self.position.no_cost / max(1, self.position.total_no)) if self.position.total_no > 0 else 0.0
        self._last_inv_ps = round(_y + _n, 3) if (_y > 0 or _n > 0) else 0.0
        self._last_gamma_dist = abs(current_btc - strike) if (current_btc > 1000 and strike > 1000) else 0.0
        self._last_gamma_maq_active = (
            self._last_gamma_dist < 150.0 and
            time_rem_sec > 180.0 and
            getattr(self, '_smooth_stress', 1.0) < 0.3
        )
        
        smooth_stress        = armor['smooth_stress']
        p_stress_mult        = armor['p_stress_mult']
        dyn_oracle_min_weight = armor['dyn_oracle_min_weight']
        dyn_base_deadband    = armor['dyn_base_deadband']
        dyn_inv_scale        = armor['dyn_inv_scale']
        inv_load             = armor['inv_load']
        # Этап 4б — Intent Mode (централизованный диспетчер)
        self._compute_intent_mode(
            inv_load=inv_load,
            smooth_stress=smooth_stress,
            mid_market=mid_market,
        )

        # [v2.10 PAIR_STATE] FSM async-aware. Вычисляется ДО spread/gravity/lot_sizing —
        # все три модуля читают self._pair_state и self._closing_side.
        self._compute_pair_state(q=open_q)

        # Этап 8  — spread & shield
        spread = self._compute_spread_and_shield(
            time_rem_sec=time_rem_sec, market_data=market_data,
            yes_ask=yes_ask, yes_bid=yes_bid, q=q,
            eff_delta=eff_delta, fv_yes=fv_yes, t_f=t_f, hc_limit=hc_limit,
        )
        base_lot       = spread['base_lot']
        base_lot       = spread['base_lot']
        t_factor       = spread['t_factor']
        effective_scale = spread['effective_scale']
        adaptive_edge  = spread['adaptive_edge']
        edge_y         = spread['edge_y']
        edge_n         = spread['edge_n']
        heavy_leg      = spread['heavy_leg']
        critical_util  = spread['critical_util']
        # Этап 5  — elastic gravity
        # СТАЛО:
        gravity = self._compute_elastic_gravity(
            fv_yes=fv_yes, q=open_q, eff_delta=eff_delta,
            dyn_base_deadband=dyn_base_deadband, effective_scale=effective_scale,
            p_stress_mult=p_stress_mult, heavy_leg=heavy_leg, TICK_SIZE=TICK_SIZE,
        )
        p_yes       = gravity['p_yes']
        p_no        = gravity['p_no']
        dynamic_q   = gravity['dynamic_q']
        vel_panic   = gravity['vel_panic']
        price_factor = gravity['price_factor']
        p_side      = gravity['p_side']
        # Этап 6  — healer
        
        healer = self._compute_healer(
            q=open_q, mid_market=mid_market, yes_ask=yes_ask,
            yes_bid=yes_bid, TICK_SIZE=TICK_SIZE, fv_yes=fv_yes,
        )
        y_avg                = healer['y_avg']
        n_avg                = healer['n_avg']
        inv_ps               = healer['inv_ps']
        is_toxic_bag         = healer['is_toxic_bag']
        recovery_tag         = healer['recovery_tag']
        price_rec_y          = healer['price_rec_y']
        price_rec_n          = healer['price_rec_n']
        is_recovery_active_y = healer['is_recovery_active_y']
        is_recovery_active_n = healer['is_recovery_active_n']
        is_flow_toxic        = healer['is_flow_toxic']
   
        # --- ПАТЧ 3: МЬЮТЕКС РЕЖИМОВ (Изоляция Лекаря и Охотника) ---
        hunter_thr_mutex = getattr(self, '_dynamic_hunter_thr', getattr(self.config, 'hunter_imb_threshold', 20))
        
        # Режим Охотника — если Q критический, Лекарь замолкает
        if abs(open_q) > hunter_thr_mutex:
            # Принудительно отключаем Лекаря
            is_recovery_active_y = False
            is_recovery_active_n = False
            price_rec_y = 0.0  # [MUTEX FIX] цены не утекают в арбитраж
            price_rec_n = 0.0  # [MUTEX FIX] цены не утекают в арбитраж
            recovery_tag = recovery_tag.replace("🩺[AVG_Y]", "").replace("🩺[AVG_N]", "")
            if "🩺" in recovery_tag:
                recovery_tag = recovery_tag.replace("🩺", "")
                
        # Режим Лекаря — если Q небольшой и Лекарь активен, Hunter работает пассивно
        elif is_recovery_active_y or is_recovery_active_n:
            # Hunter не получает is_desperate от Лекаря
            # (is_desperate остаётся False пока Q < hunter_thr, что мы уже обеспечили в Патче 1)
            pass

        # Этап 9  — lot sizing
        lots = self._compute_lot_sizing(
            time_rem_sec=time_rem_sec, api_latency=api_latency,
            fv_yes=fv_yes, mid_market=mid_market, q=open_q,
            hc_limit=hc_limit,
            is_desperate=is_desperate, is_deadlocked=is_deadlocked,
            recovery_tag=recovery_tag,
            eff_delta=eff_delta,
        )
        final_lot_y   = lots['final_lot_y']
        final_lot_n   = lots['final_lot_n']
        base_lot      = lots['base_lot']
        k_y           = lots['k_y']
        k_n           = lots['k_n']
        alpha_y       = lots['alpha_y']
        alpha_n       = lots['alpha_n']
        t_kelly       = lots['t_kelly']
        current_k_max = lots['current_k_max']
        space_y       = lots['space_y']
        space_n       = lots['space_n']
        
        # --- [ОБЛАСТЬ 2] Pre-Filter Projection Check ---
        _pf_mode = getattr(self, '_intent_mode', 'BALANCED')
        self._last_pf_resist = 0.0
        if _pf_mode == 'RESTORE_BALANCE':
            _pf_load = getattr(self, '_intent_load', 0.0)
            _pf_resist = max(0.0, (_pf_load - 0.30) / 0.70)  # 0.0 при load=0.30, 1.0 при load=1.0
            self._last_pf_resist = _pf_resist
            projected_q_y = open_q + final_lot_y
            projected_q_n = open_q - final_lot_n
            delta_imb_y = abs(projected_q_y) - abs(open_q)
            delta_imb_n = abs(projected_q_n) - abs(open_q)
            _orig_lot_y = final_lot_y
            _orig_lot_n = final_lot_n
            if delta_imb_y > 0:
                final_lot_y = max(0, int(round(final_lot_y * max(0.0, 1.0 - _pf_resist))))
                if final_lot_y != _orig_lot_y:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🔭 [PROJ_CUT] Side:YES | LotOrig:{_orig_lot_y} | LotFinal:{final_lot_y} | DeltaQ:{delta_imb_y:+d} | Resist:{_pf_resist:.2f} | Mode:{_pf_mode}"
                    )
            if delta_imb_n > 0:
                final_lot_n = max(0, int(round(final_lot_n * max(0.0, 1.0 - _pf_resist))))
                if final_lot_n != _orig_lot_n:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🔭 [PROJ_CUT] Side:NO | LotOrig:{_orig_lot_n} | LotFinal:{final_lot_n} | DeltaQ:{delta_imb_n:+d} | Resist:{_pf_resist:.2f} | Mode:{_pf_mode}"
                    )

        # --- [DIRECTIONAL_COLD_START_FILTER v3.4.1] Защита от chasing-trend opening при cold start ---
        # При настоящем cold start (Q=0 AND total_yes=0 AND total_no=0) разрешаем открывать
        # только ДЕШЁВУЮ сторону относительно FV. Дорогая сторона = chasing trend, обречённая.
        # FV > upper_thr → дорогая YES, открываем только NO (mean-revert ставка).
        # FV < lower_thr → дорогая NO, открываем только YES (mean-revert ставка).
        # В нейтральной зоне (lower < FV < upper) обе стороны разрешены.
        # При существующих позициях patch неактивен — стандартная логика работает как раньше.
        # Closing legs всегда свободны (бот может закрывать перекосы любой ценой).
        _is_real_cold_start = (open_q == 0
                               and self.position.total_yes == 0
                               and self.position.total_no == 0)
        if _is_real_cold_start:
            _fv_upper = getattr(self.config, 'cold_start_fv_upper_thr', 0.55)
            _fv_lower = getattr(self.config, 'cold_start_fv_lower_thr', 0.45)

            # FV высокий → YES дорогая → режем YES opening (мы не chasing вверх)
            if fv_yes > _fv_upper and final_lot_y > 0:
                _orig_y_dcs = final_lot_y
                final_lot_y = 0
                logging.getLogger('gabalog.grid_strategy').warning(
                    f"🎯 [DCS_KILL] Side:YES cold_start chasing | LotOrig:{_orig_y_dcs} → 0 | "
                    f"FV:{fv_yes:.3f} > Upper:{_fv_upper:.3f} | "
                    f"yes_bid:{yes_bid:.3f} no_ask:{no_ask:.3f}"
                )

            # FV низкий → NO дорогая → режем NO opening (мы не chasing вниз)
            if fv_yes < _fv_lower and final_lot_n > 0:
                _orig_n_dcs = final_lot_n
                final_lot_n = 0
                logging.getLogger('gabalog.grid_strategy').warning(
                    f"🎯 [DCS_KILL] Side:NO cold_start chasing | LotOrig:{_orig_n_dcs} → 0 | "
                    f"FV:{fv_yes:.3f} < Lower:{_fv_lower:.3f} | "
                    f"no_bid:{no_bid:.3f} yes_ask:{yes_ask:.3f}"
                )

        # Этап 10 — price pipeline
        toxic = self._run_toxic_recovery_protocol(
            active_gate_limit=active_gate_limit, market_data=market_data,
            q=q, fv_yes=fv_yes, y_avg=y_avg, n_avg=n_avg,
            is_deadlocked=is_deadlocked, _weak_side=_weak_side,
            edge_y=edge_y, edge_n=edge_n,
            hunter_gate=hunter_gate, _probe_safe=_probe_safe,
            final_lot_y=final_lot_y, final_lot_n=final_lot_n,
            p_yes=p_yes, p_no=p_no, recovery_tag=recovery_tag,
            is_active_y=is_recovery_active_y, 
            is_active_n=is_recovery_active_n,
            yes_ask=yes_ask, no_ask=no_ask, TICK_SIZE=TICK_SIZE,
        )
        p_yes        = toxic['p_yes']
        p_no         = toxic['p_no']
        l0_y_std     = toxic['l0_y_std']
        l0_n_std     = toxic['l0_n_std']
        final_lot_y  = toxic['final_lot_y']
        final_lot_n  = toxic['final_lot_n']
        recovery_tag = toxic['recovery_tag']

        pricing = self._compute_vector_pricing_and_hunter(
            fv_yes=fv_yes, edge_y=edge_y, edge_n=edge_n,
            p_yes=p_yes, p_no=p_no, time_rem_sec=time_rem_sec,
            q=q, yes_ask=yes_ask, yes_bid=yes_bid,
            no_ask=no_ask, no_bid=no_bid, TICK_SIZE=TICK_SIZE,
            is_desperate=is_desperate, price_rec_y=price_rec_y,
            price_rec_n=price_rec_n, recovery_tag=recovery_tag,
            is_toxic_bag=is_toxic_bag, effective_scale=effective_scale,
            l0_y_std=l0_y_std, l0_n_std=l0_n_std,
            is_flow_toxic=is_flow_toxic,
        )
        l0_y         = pricing['l0_y']
        l0_n         = pricing['l0_n']
        l0_y_std     = pricing['l0_y_std']
        l0_n_std     = pricing['l0_n_std']
        hunter_gate  = pricing['hunter_gate']
        ps_limit     = pricing['ps_limit']
        recovery_tag = pricing['recovery_tag']

        bbo = self._apply_bbo_clamp(
            fv_yes=fv_yes, edge_y=edge_y, edge_n=edge_n,
            p_yes=p_yes, eff_delta=eff_delta,
            l0_y=l0_y, l0_n=l0_n,
            yes_ask=yes_ask, yes_bid=yes_bid,
            no_ask=no_ask, no_bid=no_bid,
            TICK_SIZE=TICK_SIZE,
        )
        l0_y       = bbo['l0_y']
        l0_n       = bbo['l0_n']
        clip_y_tag = bbo['clip_y_tag']
        clip_n_tag = bbo['clip_n_tag']

        maq = self._apply_maq_filter(
            t_kelly=t_kelly, fv_yes=fv_yes,
            recovery_tag=recovery_tag, l0_y=l0_y, l0_n=l0_n,
            TICK_SIZE=TICK_SIZE,
            open_q=q,
            current_btc=current_btc,
            strike=strike,
            time_rem=time_rem_sec,
        )
        l0_y        = maq['l0_y']
        l0_n        = maq['l0_n']
        dynamic_maq = maq['dynamic_maq']
        eff_maq     = maq['eff_maq']
        log_maq     = maq['log_maq']

        # СТАЛО:
        veto = self._apply_profit_gate_sanitizer(
            q=open_q, is_desperate=is_desperate,
            final_lot_y=final_lot_y, final_lot_n=final_lot_n,
            recovery_tag=recovery_tag, l0_y=l0_y, l0_n=l0_n,
            is_flow_toxic=is_flow_toxic,
        )
        l0_y         = veto['l0_y']
        l0_n         = veto['l0_n']
        max_gate_val = veto['max_gate_val']
        safe_y       = veto['safe_y']
        safe_n       = veto['safe_n']

        # [ВОТ ЗДЕСЬ ВСТАВЛЯЕМ ВЫЗОВ]
        decision = getattr(self, '_last_decision', 'NORMAL')
        self._last_intent_tag = self._synthesize_master_intent(
            decision=decision, 
            recovery_tag=recovery_tag, 
            l0_y=l0_y, 
            l0_n=l0_n, 
            q=open_q
        )

        gc = self._apply_smart_gc(
            oracle_fv=oracle_fv, q=q, recovery_tag=recovery_tag,
            yes_bid=yes_bid, no_bid=no_bid, l0_y=l0_y, l0_n=l0_n,
        )
        l0_y          = gc['l0_y']
        l0_n          = gc['l0_n']
        dist_thr      = gc['dist_thr']
        in_rescue_mode = gc['in_rescue_mode']
        saving_leg    = gc['saving_leg']

        # === [FINAL BBO ANCHOR 2026-05-13 Option C] =====================
        # The closing-leg BBO pull-up applied in _apply_bbo_clamp ran BEFORE
        # _apply_maq_filter, _apply_profit_gate_sanitizer, and _apply_smart_gc
        # — any of which can shave a tick off the price. Final maker price
        # ends up at bid-tick instead of bid (queue position #2, not #1).
        # We re-apply the pull-up here AFTER all sanitizers as a final
        # anchor. Done only on the closing leg (Variant B); opening leg
        # keeps its edge-below-FV intent.
        _open_q_final = getattr(self, '_last_open_q', 0)
        _hedge_thr_final = getattr(self, '_dynamic_hunter_thr',
                                    getattr(self.config, 'hunter_imb_threshold', 5))
        _yes_close_final = _open_q_final < -_hedge_thr_final
        _no_close_final  = _open_q_final > _hedge_thr_final
        _bbo_max_spread = getattr(self.config, 'bbo_max_spread', 0.06)
        TICK_FINAL = 0.01

        if l0_y > 0.0 and yes_bid > 0.0 and yes_ask > 0.0:
            _spread = yes_ask - yes_bid
            if _spread <= _bbo_max_spread and _yes_close_final and l0_y < yes_bid:
                _target = min(yes_bid, yes_ask - TICK_FINAL)
                if _target > 0.01:
                    l0_y = round(_target, 2)
        if l0_n > 0.0 and no_bid > 0.0 and no_ask > 0.0:
            _spread = no_ask - no_bid
            if _spread <= _bbo_max_spread and _no_close_final and l0_n < no_bid:
                _target = min(no_bid, no_ask - TICK_FINAL)
                if _target > 0.01:
                    l0_n = round(_target, 2)

        # [П5 v2.6] Hunter Lot Override — иммунный лот равный размеру перекоса
        # Hunter выиграл ценовой арбитраж (l0_y/n > 0) при активном перекосе →
        # перезаписываем final_lot на abs(q), игнорируя CVD choke и Kelly decay.
        # space_y/n гарантируют непревышение hc_limit.
        _MIN_MKT_LOT = 5
        _hunter_thr_ovr = getattr(self.config, 'hunter_imb_threshold', 8)
        _max_lot_ovr = getattr(self.config, 'max_single_lot', 50)
        if q < -_hunter_thr_ovr and l0_y > 0:
            # Перекос в NO → Hunter покупает YES → лот = весь перекос
            _hunter_lot_y = max(_MIN_MKT_LOT, min(abs(q), _max_lot_ovr, space_y))
            if _hunter_lot_y > final_lot_y:
                logging.getLogger('gabalog.grid_strategy').info(
                    f"🏹 [HUNTER_LOT] YES лот {final_lot_y}→{_hunter_lot_y} "
                    f"(Q:{q} | Space:{space_y}) | {self._std_ctx()}"
                )
                final_lot_y = _hunter_lot_y
        elif q > _hunter_thr_ovr and l0_n > 0:
            # Перекос в YES → Hunter покупает NO → лот = весь перекос
            _hunter_lot_n = max(_MIN_MKT_LOT, min(abs(q), _max_lot_ovr, space_n))
            if _hunter_lot_n > final_lot_n:
                logging.getLogger('gabalog.grid_strategy').info(
                    f"🏹 [HUNTER_LOT] NO лот {final_lot_n}→{_hunter_lot_n} "
                    f"(Q:{q} | Space:{space_n}) | {self._std_ctx()}"
                )
                final_lot_n = _hunter_lot_n

        orch = self._run_grid_orchestrator(
            fv_yes=fv_yes, time_rem_sec=time_rem_sec, mid_market=mid_market,
            q=q, final_lot_y=final_lot_y, final_lot_n=final_lot_n,
            l0_y=l0_y, l0_n=l0_n, is_desperate=is_desperate,
            is_warmup=is_warmup, is_medical_averaging=is_medical_averaging,
            recovery_tag=recovery_tag, current_suppress_thr=current_suppress_thr,
            edge_y=edge_y, edge_n=edge_n, adaptive_edge=adaptive_edge,
            m_state=m_state,
        )
        if orch.get('early_exit'):
            return orch['actions']

        target            = orch['target']
        dyn_share_limit_y = orch['dyn_share_limit_y']
        dyn_share_limit_n = orch['dyn_share_limit_n']
        budget_rem        = orch['budget_rem']
        usd_limit         = orch['usd_limit']
        t_factor          = orch['t_factor']
        fv_certainty      = orch['fv_certainty']
        edge_y            = orch['edge_y']
        edge_n            = orch['edge_n']
        adaptive_edge     = orch['adaptive_edge']
        m_state           = orch['m_state']

        # Этап 11 — grid execution
        pruning = self._run_grid_pruning(
            q=open_q, target=target, now=now, momentum_side_lock=momentum_side_lock,
        )
        target      = pruning['target']
        _abs_q      = pruning['_abs_q']
        _heavy_side = pruning['_heavy_side']
        current_hc  = pruning['current_hc']

        immunity = self._run_hedge_immunity(
            target=target,
            q=q,
            eval_y_shares=eval_y_shares,
            eval_y_cost=eval_y_cost,
            eval_n_shares=eval_n_shares,
            eval_n_cost=eval_n_cost,
            dyn_share_limit_y=dyn_share_limit_y,
            dyn_share_limit_n=dyn_share_limit_n,
            usd_limit=usd_limit,
            MAX_SKEW_DELTA=self._dynamic_hard_cutoff  # <-- Решение здесь
        )
        target        = immunity['target']
        is_yes_blocked = immunity['is_yes_blocked']
        is_no_blocked  = immunity['is_no_blocked']

        veto = self._run_hard_veto(
            fv_yes=fv_yes, mid_market=mid_market,
            recovery_tag=recovery_tag, q=q, target=target,
            is_desperate=is_desperate,
        )
        target        = veto['target']
        veto_thr      = veto['veto_thr']
        oracle_diff   = veto['oracle_diff']
        is_bunker     = veto['is_bunker']

        sync = self._run_final_sync_and_triage(
            market_data=market_data, time_rem_sec=time_rem_sec,
            q=q, fv_yes=fv_yes, active_gate_limit=active_gate_limit,
            is_desperate=is_desperate, recovery_tag=recovery_tag,
            is_readonly=is_readonly, target=target, m_state=m_state,
        )
        if sync.get('early_exit'):
            return sync['actions']

        actions    = sync['actions']
        t_limit    = sync['t_limit']
        is_in_rescue = sync['is_in_rescue']
        m_state    = sync['m_state']
    

        # Этап 1  — forensic telemetry  ← финальный return
        _cvd_for_skew = getattr(self, '_cvd_signal_last', 0.0)
        _streak_for_skew = getattr(self, '_cvd_toxic_streak', 0)
        _hc_for_skew = getattr(self, '_dynamic_hard_cutoff', 350)
        _space_for_skew = round((1.0 - abs(open_q) / max(1, _hc_for_skew)) * 100)

        return self._run_forensic_telemetry(
            yes_bid=yes_bid, no_bid=no_bid, yes_ask=yes_ask, no_ask=no_ask,
            mid_market=mid_market, current_btc=current_btc, strike=strike,
            fv_yes=fv_yes, oracle_fv=oracle_fv, new_weight=new_weight,
            diagnosis=diagnosis, eff_delta=eff_delta,
            current_vol_ratio=current_vol_ratio, alpha_y=alpha_y, alpha_n=alpha_n,
            dynamic_maq=dynamic_maq, current_k_max=current_k_max,
            l0_y=l0_y, l0_n=l0_n, final_lot_y=final_lot_y, final_lot_n=final_lot_n,
            q=q, dynamic_q=dynamic_q, effective_scale=effective_scale,
            p_yes=p_yes, p_no=p_no, active_gate_limit=active_gate_limit,
            recovery_tag=recovery_tag, is_desperate=is_desperate, is_warmup=is_warmup,
            required_sec=required_sec, current_cfr=current_cfr, api_latency=api_latency,
            m_slug=m_slug, t_rem=t_rem, tick_start_time=tick_start_time,
            m_state=m_state, inv_load=inv_load, dyn_is=dyn_is,
            target=target, actions=actions, tel=tel, market_data=market_data,
            cvd_skew=_cvd_for_skew, streak_skew=_streak_for_skew,
            open_q_skew=open_q, space_skew=_space_for_skew,
        )

    def _compute_oracle_fv(
        self,
        current_btc: float,
        strike: float,
        time_rem_sec: float,
        current_vol_ratio: float,
        mid_market: float,
    ) -> float:
        try:
            if strike < 1000 or current_btc < 1000:
                return mid_market

            current_delta = getattr(self, '_last_effective_delta', 0.0)
            if current_delta is None:
                current_delta = 0.0

            return self.oracle_engine.calculate_fv(  # ← вот правильный вызов
                current_btc=current_btc,
                strike=strike,
                time_left_sec=time_rem_sec,
                total_duration=self.config.market_duration_sec,
                vol_ratio=current_vol_ratio,
                btc_momentum=current_delta,
                p_mkt=mid_market,
                vpin=0.5
            )

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_ORACLE_FV] CRITICAL ERROR: {e} | "
                f"current_btc={current_btc:.0f}, strike={strike:.0f}, "
                f"time_rem_sec={time_rem_sec:.1f}, mid_market={mid_market:.4f}"
            )
            return mid_market

    def _compute_elastic_iron_gate(
        self,
        q: int,
        time_rem_sec: float,
        oracle_fv: float,
    ) -> dict:
        try:
            hc_limit   = getattr(self, '_dynamic_hard_cutoff', 350)
            q_c        = (abs(q) / max(1, hc_limit)) * 0.02
            fade_start = getattr(self.config, 'endgame_fade_start_sec', 300.0)
            t_c        = (1.0 - (time_rem_sec / fade_start)) * 0.02 if time_rem_sec < fade_start else 0.0

            fv_divergence_gate = abs(oracle_fv - 0.50)
            elastic_k_gate     = max(0, fv_divergence_gate - 0.15)
            raw_elastic_gate   = (elastic_k_gate ** 1.5) * 0.45

            trend_gate_bonus = 0.0
            if fv_divergence_gate > 0.20:
                trend_gate_bonus = (fv_divergence_gate - 0.20) * 0.20

            abs_gate_max = getattr(self.config, 'gate_max', 1.040)
            
            active_gate_limit = min(
                abs_gate_max,
                self.config.gate_min + q_c + t_c + raw_elastic_gate + trend_gate_bonus
            )

            # [ЧИСТАЯ АРХИТЕКТУРА] Сохраняем в state, НЕ МУТИРУЕМ self.config
            cap = getattr(self.config, 'tick_base_gate_cap', 0.995)
            self._tick_base_gate = round(min(active_gate_limit, cap), 4)   # кэпированный — для PS_LIMIT и Sanitizer
            self._tick_hunter_gate = round(active_gate_limit, 4)            # полный — для Hunter

            n_size = getattr(self.config, 'nudge_size', 0.01)
            self._tick_hunter_gate = round(active_gate_limit + n_size, 4)

            if fv_divergence_gate > 0.20 and time.time() - getattr(self, '_last_trend_gate_log', 0) > 30.0:
                logger.info(
                    f"📈 [GATE_CONSOLIDATED] Limit: {active_gate_limit:.3f} | "
                    f"Cap: {cap:.3f} | "           # ← добавить
                    f"Base: {self._tick_base_gate:.3f} | "  # ← добавить
                    f"Trend_B: +{trend_gate_bonus:.3f}"
                )
                self._last_trend_gate_log = time.time()

            # Триггер: инвентарь > 20 акций, но лимит гейта расширился менее чем на 1 цент от базы
            if abs(q) > 20 and (active_gate_limit - self.config.gate_min) < 0.01:
                now = time.time()
                if now - getattr(self, '_last_gate_tight_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦🧱 [GATE_TIGHT] Инвентарь растет (Q:{q}), но ворота не расширяются! "
                        f"Limit: {active_gate_limit:.3f} (Base: {self.config.gate_min:.3f}) | "
                        f"q_c: {q_c:.4f} | raw_elastic: {raw_elastic_gate:.4f}"
                    )
                    self._last_gate_tight_log = now

            return {
                'active_gate_limit': active_gate_limit,
                'hc_limit':          hc_limit,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_ELASTIC_IRON_GATE] CRITICAL ERROR: {e} | "
                f"q={q}, time_rem_sec={time_rem_sec:.1f}, oracle_fv={oracle_fv:.4f}"
            )
            raise

    def _run_safety_and_merge(
        self,
        market_data: dict,
        time_rem_sec: float,
        yes_bid: float,
        no_bid: float,
    ) -> dict:
        try:
            # 2.1 Watchdog — слепота WebSocket
            if market_data.get('is_blind', False):
                return {'early_exit': True, 'actions': []}

            # Warmup
            c_mkt = market_data.get('market', market_data.get('market_slug', 'unknown'))
            if getattr(self, '_c_mkt', None) != c_mkt:
                self._c_mkt   = c_mkt
                self._m_start = time.time()
                logger.info(f"⏱️ Warmup start: {c_mkt}")

            is_warmup = (time.time() - getattr(self, '_m_start', time.time())) < 5.0

            # --- ЖУЧОК [WARMUP_LEAK] ---
            # Если вармап длится более 10 секунд (что-то пошло не так с таймером)
            _w_dur = time.time() - getattr(self, '_m_start', time.time())
            if _w_dur > 10.0 and not getattr(self, '_warmup_ended', False):
                 if time.time() - getattr(self, '_last_warmup_leak_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦⏳💤 [WARMUP_LEAK] Затянувшийся вармап: {_w_dur:.1f}с. Бот всё еще заблокирован!"
                    )
                    self._last_warmup_leak_log = time.time()
            # ---------------------------

            if not is_warmup and not getattr(self, '_warmup_ended', False):
                logger.info("🌱 [WARMUP END] | Действие: Снятие блокировки ордеров | Причина: 12 сек прошло")
                self._warmup_ended = True

            # 2.2 HFT Halt
            api_latency = market_data.get('api_latency_ms', 0)
            max_rtt     = getattr(self.config, 'hft_latency_halt_ms', 250.0)

            if api_latency > max_rtt:
                if not getattr(self, '_hft_halt_active', False):
                    self._hft_halt_active = True
                    self._log_decision('HFT_HALT',
                        f"⚡ [HOT_PATH] Сеть деградировала ({api_latency}ms). Эвакуация!")
                    return {
                        'early_exit': True,
                        'actions': [OrderAction(action='CANCEL_ALL_NUCLEAR', reason="HFT_LATENCY_SPIKE")],
                    }
                if time.time() - getattr(self, '_last_halt_msg_ts', 0) > 10.0:
                    logger.warning(f"⏳ [HFT_HALT_ACTIVE] Бот в укрытии. Сеть: {api_latency}ms > {max_rtt:.0f}ms")
                    self._last_halt_msg_ts = time.time()
                return {'early_exit': True, 'actions': []}

            self._hft_halt_active = False

            # 2.3 Троттлинг
            engine      = getattr(self, 'engine', None)
            live_cfr    = engine.get_live_cfr() if engine else 0.0
            is_throttled = engine and time.time() < engine._throttle_until

            if is_throttled:
                self.grid_manager.stale_threshold_ticks = 15
                self.grid_manager.chase_threshold_ticks  = 15
                if time.time() - getattr(self, '_last_throttle_log', 0) > 10.0:
                    logger.warning(f"🐢 [SURVIVAL MODE] API Throttle! Deadband: 15 ticks. CFR: {live_cfr}")
                    self._last_throttle_log = time.time()
            else:
                self.grid_manager.stale_threshold_ticks = self.config.stale_threshold_ticks
                self.grid_manager.chase_threshold_ticks  = self.config.chase_threshold_ticks

            # Time Stop
            if time_rem_sec <= getattr(self.config, 'end_market_buffer_sec', 15):
                if not getattr(self, '_time_stop_fired', False):
                    self._time_stop_fired = True
                    logger.warning(f"🏁 [TIME STOP] Финал рынка (T-{time_rem_sec:.0f}s). Полная зачистка.")
                    return {
                        'early_exit': True,
                        'actions': [OrderAction(action='CANCEL_ALL_NUCLEAR', reason="TIME_STOP")],
                    }
                return {'early_exit': True, 'actions': []}

            # 2.4 Merge Gate
            is_readonly           = False
            merge_active_externally = market_data.get('merge_in_progress', False)
            now                   = time.time()

            if self._merge_state != 'IDLE' or merge_active_externally:
                is_readonly = True

                if self._merge_state != 'IDLE':
                    lock_duration  = now - self._pending_merge_ts
                    watchdog_limit = max(getattr(self.config, 'merge_lock_sec', 2.0) * 4.0, 6.0)

                    if lock_duration > watchdog_limit:
                        self._merge_state     = 'IDLE'
                        self._pending_merge_size = 0
                        logger.error(f"🚨 [WATCHDOG] Внутренний таймаут Merge ({lock_duration:.1f}s)! Принудительный разлок.")
                        is_readonly = False

                    if self._merge_state == 'PREPARING':
                        if lock_duration >= getattr(self.config, 'merge_lock_sec', 2.0):
                            size    = self._pending_merge_size
                            cond_id = self._pending_merge_side
                            self._merge_state = 'EXECUTING'
                            self._log_decision('MERGE_EXECUTE',
                                f"🚀 [DECISION] MERGE_EXECUTE | Выстрел на {size} пар.")
                            return {
                                'early_exit': True,
                                'actions': [OrderAction(action='CTF_MERGE', size=size, side=cond_id)],
                            }

            # Smart Merge Logic
            hedged_pairs = min(self.position.yes_shares, self.position.no_shares)

            if not is_readonly and hedged_pairs >= getattr(self.config, 'min_merge_size', 10):
                now = time.time()
                if (now - getattr(self, '_last_merge_ts', 0)) > self.config.merge_cooldown_sec:
                    y_avg   = self.position.yes_cost / max(1, self.position.yes_shares)
                    n_avg   = self.position.no_cost  / max(1, self.position.no_shares)
                    inv_ps  = y_avg + n_avg
                    potential_pnl = 1.0 - inv_ps

                    # --- ЖУЧОК [MERGE_POISON] ---
                    # Если PnL отрицательный, Merge превращается в фиксацию убытка
                    if potential_pnl < 0:
                        _now = time.time()
                        if _now - getattr(self, '_last_merge_poison_log', 0) > 30.0:
                            logging.getLogger('gabalog.grid_strategy').error(
                                f"🪦☣️📉 [MERGE_POISON] Попытка Merge убыточной позиции! "
                                f"PS: {inv_ps:.4f} | PnL: {potential_pnl:.4f}"
                            )
                            self._last_merge_poison_log = _now
                    # ----------------------------

                    is_full_house     = self.position.total_cost >= (self.config.deposit * 0.80)
                    is_endgame        = time_rem_sec <= 300
                    is_merge_profitable = inv_ps < 0.985

                    total_sh  = self.position.yes_shares + self.position.no_shares
                    imb_pct   = (abs(self.position.yes_shares - self.position.no_shares) /
                                total_sh * 100.0) if total_sh > 0 else 0.0
                    is_balance_perfect = imb_pct <= 7.0

                    should_merge = (
                        (is_merge_profitable and is_balance_perfect and is_full_house) or
                        (is_endgame and is_merge_profitable)
                    )

                    if should_merge:
                        self._last_merge_ts      = now
                        cond_id                  = market_data.get('condition_id')
                        self._pending_merge_size = int(hedged_pairs)
                        self._pending_merge_side = cond_id
                        self._pending_merge_ts   = now
                        self._merge_state        = 'PREPARING'
                        logger.warning(
                            f"🧠 [DECISION] MERGE_TRIGGER | Состояние: PREPARING | "
                            f"Найдено {hedged_pairs} пар (PnL: {potential_pnl:+.4f})"
                        )
                        return {
                            'early_exit': True,
                            'actions': [OrderAction(action='CANCEL_ALL_NUCLEAR', reason="PRE_MERGE")],
                        }

            # Paper Winner snapshot
            if 5 <= time_rem_sec <= 10:
                self.paper_winner = 'YES' if yes_bid > no_bid else 'NO'

            return {
                'early_exit':  False,
                'is_warmup':   is_warmup,
                'api_latency': api_latency,
                'max_rtt':     max_rtt,
                'live_cfr':    live_cfr,
                'is_throttled': is_throttled,
                'is_readonly': is_readonly,
                'hedged_pairs': hedged_pairs,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_SAFETY_AND_MERGE] CRITICAL ERROR: {e} | "
                f"time_rem_sec={time_rem_sec:.1f}, "
                f"merge_state={getattr(self, '_merge_state', 'N/A')}, "
                f"yes_bid={yes_bid:.4f}, no_bid={no_bid:.4f}"
            )
            raise

    def _run_preflight(
        self,
        market_data: dict,
        api_latency: int,
        max_rtt: int,
        is_throttled: bool,
        target: list,
        current_btc: float,
        strike: float,
        fv_yes: float,
        oracle_fv: float,
        active_gate_limit: float,
        yes_bid: float,
        yes_ask: float,
        no_bid: float,
        no_ask: float,
        q: int,
        p_yes: float,
        p_no: float,
        adaptive_edge: float,
        effective_scale: float,
        m_slug: str,
        current_cfr: float,
        now: float,
    ) -> dict:
        try:
            # HUD статус теги
            hft_tag        = "⚡HALT"   if api_latency > max_rtt else ""

            # --- ЖУЧОК [LATENCY_SPIKE] ---
            if hft_tag == "⚡HALT":
                now_ts = time.time()
                if now_ts - getattr(self, '_last_latency_spike_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"⚡🪦⚠️ [LATENCY_SPIKE] API задержка ({api_latency}ms) выше лимита ({max_rtt}ms). Тик будет заморожен!"
                    )
                    self._last_latency_spike_log = now_ts
            # -----------------------------

            snipe_tag      = "🛡️FREEZ" if self._pre_pull_ticks_left > 0 else ""
            thro_tag       = "🐢THRO"   if is_throttled else ""
            rescue_tag_pulse = "🚑RESC" if getattr(self, '_is_healing_state', False) else ""
            status_tag     = hft_tag or snipe_tag or thro_tag or rescue_tag_pulse or "💎ACTV"

            # Pulse словарь (читается дашбордом каждый тик)
            self.last_telemetry_pulse = {
                'status':      getattr(self, '_market_regime', 'NEUTRAL'),  # <--- ЖЕСТКО ПРИВЯЗЫВАЕМ К FSM
                'timestamp':   time.time(),             # [NEW] Метка времени сервера для оси X
                'momentum':    float(getattr(self, '_momentum', 0.0)),       # [NEW] Для монитора
                'cvd':         float(getattr(self, '_cvd_fast_signal', 0.0)),# [NEW] Для монитора
                
                't_len':       int(len(target)),
                'rtt':         int(api_latency),
                'btc':         float(current_btc),
                'stk':         float(strike),
                'stk_v':       1 if market_data.get('strike_verified', False) else 0,
                'fv':          round(fv_yes, 3),
                'raw_fv':      round(oracle_fv, 3),
                'trust':       round(getattr(self, '_current_oracle_weight', 1.0), 2),
                'q':           int(q),
                'cost':        float(self.position.total_cost),
                'shadow_cost': float(self.position.active_total_cost),
                'pnl':         float(self.position.realized_ctf_pnl),
                'util':        round((self.position.total_cost / self.config.deposit * 100), 1) if self.config.deposit > 0 else 0,
                'gate':        float(active_gate_limit),
                'proj_ps':     float(getattr(self, '_current_proj_ps', 0.0)),
                'inv_ps':      float((self.position.yes_cost / max(1, self.position.total_yes) +
                                    self.position.no_cost / max(1, self.position.total_no))
                                    if self.position.total_yes > 0 else 0),
                'stress':      float(self._smooth_stress),
                'cfr':         float(current_cfr),
                'scale':       float(effective_scale),
                'penalty':     float(max(abs(p_yes), abs(p_no))),
                'edge':        float(adaptive_edge),
                'spread':      float(abs(yes_ask - yes_bid)),
            }

            # Pulse лог (раз в 2 секунды)
            if now - getattr(self, '_last_pulse', 0) > 1: # <--- 0.1s
                logger.info(
                    f"🧠 [PULSE] {status_tag} | Mkt:{m_slug} | "
                    f"Y:{yes_bid:.3f}-{yes_ask:.3f} | N:{no_bid:.3f}-{no_ask:.3f} | "
                    f"BTC:{current_btc:.0f} | STK:{strike:.0f} | FV:{fv_yes:.3f} | "
                    f"Q:{q} | PnL:{self.position.realized_ctf_pnl:+.4f}"
                )
                self._last_pulse = now

            # Risk Stop
            is_healing_active_prev = getattr(self, '_is_healing_state', False)
            if self._check_risk_stop(market_data):

                # --- ВОТ СЮДА ВСТАВЛЯЕМ ЖУЧОК [PREFLIGHT_ABORT] ---
                now_ts = time.time()
                if now_ts - getattr(self, '_last_risk_abort_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').critical(
                        f"🪦☢️ [PREFLIGHT_ABORT] Риск-стоп активирован! "
                        f"Status: {status_tag} | Latency: {api_latency}ms | "
                        f"Healing: {is_healing_active_prev}"
                    )
                    self._last_risk_abort_log = now_ts
                # --------------------------------------------------

                if is_healing_active_prev:
                    if not hasattr(self, '_rescue_start_ts'):
                        self._rescue_start_ts = now
                        logger.critical("🆘 [RESCUE] Risk Stop! Таймер реанимации 60с...")
                    if now - self._rescue_start_ts < 60.0:
                        pass
                    else:
                        logging.getLogger('gabalog.grid_strategy').critical(
                            "💀 [RESCUE] Время вышло. RISK_STOP_FINAL.")
                        return {
                            'early_exit': True,
                            'actions': [OrderAction(action='cancel', order_id=oid, reason="RISK_STOP_FINAL")
                                        for oid in self.grid_manager.cancel_all()],
                        }
                else:
                    return {
                        'early_exit': True,
                        'actions': [OrderAction(action='cancel', order_id=oid, reason="RISK_STOP")
                                    for oid in self.grid_manager.cancel_all()],
                    }
            else:
                if hasattr(self, '_rescue_start_ts'):
                    del self._rescue_start_ts

            # Safe Initialization
            base_lot          = self.config.grid_lot_size
            final_lot_y       = base_lot
            final_lot_n       = base_lot
            current_cfr_out   = self.engine.get_live_cfr() if self.engine else 0.0
            self._fills_this_tick   = 0
            self._is_official_strike = market_data.get('strike_verified', False)
            inv_load          = 0.0
            required_sec      = 120.0
            current_dump_mult = getattr(self.config, 'emergency_dump_sell_pct', 0.5)

            base_cap          = getattr(self.config, 'inventory_hard_cap', 25)
            dyn_share_limit_y = base_cap
            dyn_share_limit_n = base_cap

            actions              = []
            is_medical_averaging = False
            is_desperate         = False

            tick_start_time = time.time()
            tel             = TickTelemetry()

            # Orderbook snapshot
            if yes_bid > 0 or no_bid > 0:
                self._last_orderbook = {
                    'yes_bid': yes_bid, 'yes_ask': yes_ask,
                    'no_bid':  no_bid,  'no_ask':  no_ask,
                }

            return {
                'early_exit':         False,
                'status_tag':         status_tag,
                'base_lot':           base_lot,
                'final_lot_y':        final_lot_y,
                'final_lot_n':        final_lot_n,
                'current_cfr':        current_cfr_out,
                'inv_load':           inv_load,
                'required_sec':       required_sec,
                'current_dump_mult':  current_dump_mult,
                'dyn_share_limit_y':  dyn_share_limit_y,
                'dyn_share_limit_n':  dyn_share_limit_n,
                'actions':            actions,
                'is_medical_averaging': is_medical_averaging,
                'is_desperate':       is_desperate,
                'tick_start_time':    tick_start_time,
                'tel':                tel,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_PREFLIGHT] CRITICAL ERROR: {e} | "
                f"q={q}, api_latency={api_latency}, max_rtt={max_rtt}, "
                f"fv_yes={fv_yes:.4f}, oracle_fv={oracle_fv:.4f}, "
                f"is_throttled={is_throttled}"
            )
            raise

    def _run_oracle_data_prep(
        self,
        market_data: dict,
        yes_bid: float,
        yes_ask: float,
        no_bid: float,
        no_ask: float,
        q: int,
        oracle_fv: float,
        actions: list,
        target: list,
        is_readonly: bool,
        l0_y: float,
        l0_n: float,
    ) -> dict:
        try:
            # 3.1 BTC и страйк
            p_obj      = self.config.shared_btc_price
            current_btc = p_obj.value if hasattr(p_obj, 'value') else float(p_obj or 0)
            if current_btc == 0:
                current_btc = market_data.get('btc_price', 0.0)

            s_obj  = self.config.shared_btc_strike
            strike = s_obj.value if (s_obj and hasattr(s_obj, 'value')) else 0.0
            if strike < 1000:
                strike = float(market_data.get('strike_price') or 0.0)

            self._is_official_strike = bool(market_data.get('strike_verified', False))

            # Synthetic Mid
            mid_yes     = (yes_bid + yes_ask) / 2.0 if (yes_bid > 0 and yes_ask > 0) else 0.50
            mid_no      = (no_bid + no_ask)   / 2.0 if (no_bid  > 0 and no_ask  > 0) else 0.50
            implied_yes = 1.0 - mid_no
            mid_market  = (mid_yes + implied_yes) / 2.0

            # --- ЖУЧОК [MID_DIVERGENCE] ---
            # Если разница между мидом YES и мидом NO > 3 центов, стаканы рассинхронены
            _mid_div = abs(mid_yes - implied_yes)
            if _mid_div > 0.03:
                _now = time.time()
                if _now - getattr(self, '_last_mid_div_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦👻⚠️ [MID_DIVERGENCE] Рассинхрон стаканов! Diff: {_mid_div:.3f} | "
                        f"Mid_Y: {mid_yes:.3f} | Impl_Y (from NO): {implied_yes:.3f} | {self._std_ctx()}"
                    )
                    self._last_mid_div_log = _now
            # ------------------------------

            # Anti-Ghost
            if strike < 1000:
                self._is_official_strike       = False
                market_data['strike_verified'] = False

            is_data_corrupt = current_btc < 1000 or strike < 1000

            if is_data_corrupt:
                target   = []
                l0_y     = 0.0
                l0_n     = 0.0
                if time.time() - getattr(self, '_last_halt_log', 0) > 10.0:
                    err_msg = "[STRIKE_MISSING]" if strike < 1000 else "[BTC_PRICE_MISSING]"
                    logger.error(f"🛑 [DATA_HALT] {err_msg} | BTC:{current_btc} Strike:{strike}")
                    self._last_halt_log = time.time()
                actions += [OrderAction(action='cancel', order_id=oid, reason="DATA_HALT")
                            for oid in self.grid_manager.cancel_all()]
                is_readonly = True

            # Awaiting Strike Fix
            if not getattr(self, '_is_official_strike', False):
                oracle_fv = mid_market

            # Dead Zone
            self._is_at_dead_pole = (oracle_fv > 0.90 or oracle_fv < 0.10)
            if self._is_at_dead_pole:
                if time.time() - getattr(self, '_last_deadzone_log', 0) > 30.0:
                    logger.info(f"🧱 [DEAD_ZONE_AWARE] FV:{oracle_fv:.3f}. Стендбай режим активен.")
                    self._last_deadzone_log = time.time()

            # Momentum Veto
            btc_delta          = market_data.get('btc_delta', 0.0)
            momentum_side_lock = None
            if abs(btc_delta) >= self.config.momentum_halt_thr:
                is_healing = getattr(self, '_is_healing_state', False)
                if btc_delta < 0:
                    if not (q < -5 or is_healing):
                        momentum_side_lock = 'YES'
                else:
                    if not (q > 5 or is_healing):
                        momentum_side_lock = 'NO'
                self._log_decision('MOMENTUM_LOCK',
                    f"🌊 [MOMENTUM] BTC {'CRASH' if btc_delta < 0 else 'ROCKET'} ({btc_delta:+.2f}$). Блокировка {momentum_side_lock}")

            # Oracle None fallback
            if oracle_fv is None:
                target    = []
                oracle_fv = mid_market
                actions += [OrderAction(action='cancel', order_id=oid, reason="ORACLE_MATH_HALT")
                            for oid in self.grid_manager.cancel_all()]

            # Spread Guard
            mkt_spread        = yes_ask - yes_bid
            max_allowed_spread = getattr(self.config, 'max_market_spread', 0.15)
            if mkt_spread > max_allowed_spread:
                if time.time() - getattr(self, '_last_spread_log', 0) > 30.0:
                    logger.warning(f"📉 [HALT] Пустой стакан! Spread: {mkt_spread:.3f} > {max_allowed_spread}")
                    self._last_spread_log = time.time()
                actions += [OrderAction(action='cancel', order_id=oid, reason="WIDE_SPREAD_HALT")
                            for oid in self.grid_manager.cancel_all()]
                is_readonly = True

            # FV финализация
            fv_yes = oracle_fv

            return {
                'current_btc':       current_btc,
                'strike':            strike,
                'mid_market':        mid_market,
                'oracle_fv':         oracle_fv,
                'fv_yes':            fv_yes,
                'momentum_side_lock': momentum_side_lock,
                'is_data_corrupt':   is_data_corrupt,
                'is_readonly':       is_readonly,
                'actions':           actions,
                'target':            target,
                'l0_y':              l0_y,
                'l0_n':              l0_n,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_ORACLE_DATA_PREP] CRITICAL ERROR: {e} | "
                f"current_btc={locals().get('current_btc', 'N/A')}, "
                f"strike={locals().get('strike', 'N/A')}, "
                f"oracle_fv={oracle_fv}, q={q}, "
                f"yes_bid={yes_bid:.4f}, yes_ask={yes_ask:.4f}"
            )
            raise

    def _run_final_sync_and_triage(
        self,
        market_data: dict,
        time_rem_sec: float,
        q: int,
        fv_yes: float,
        active_gate_limit: float,
        is_desperate: bool,
        recovery_tag: str,
        is_readonly: bool,
        target: list,
        m_state: str,
    ) -> dict:
        try:
            # Iron Gate
            self._current_proj_ps = 0.0
            if target:
                mkt_y_ask      = market_data.get('yes_ask', 1.0)
                mkt_n_ask      = market_data.get('no_ask', 1.0)
                hunter_max_gate = getattr(self.config, 'hunter_max_gate', 1.05)

                for _lvl in list(target):
                    current_ask_other = mkt_n_ask if _lvl.side == 'YES' else mkt_y_ask
                    marginal_ps       = _lvl.price + current_ask_other

                    is_capitulating = (getattr(self, '_consensus_confirmed', False) or
                                    self._last_intent == "CAPITULATION")
                    _curr_side_avg  = (
                        self.position.yes_cost / max(1, self.position.total_yes)
                        if _lvl.side == 'YES' else
                        self.position.no_cost / max(1, self.position.total_no)
                    )
                    is_healing = (_lvl.price < _curr_side_avg) and (_curr_side_avg > 0)

                    if marginal_ps > active_gate_limit and not is_capitulating and not is_healing:
                        is_desperate_hedge = (
                            (q > 5  and _lvl.side == 'NO'  and marginal_ps <= hunter_max_gate) or
                            (q < -5 and _lvl.side == 'YES' and marginal_ps <= hunter_max_gate)
                        )
                        if not is_desperate_hedge:
                            target.remove(_lvl)
                            self._current_proj_ps = max(self._current_proj_ps, marginal_ps)
                            if time.time() - getattr(self, '_last_iron_gate_log', 0) > 1.0:
                                logging.getLogger('gabalog.grid_strategy').warning(
                                    f"🚧 [IRON_GATE] Marginal VETO {_lvl.side}: "
                                    f"{marginal_ps:.3f} > Limit (Gate:{active_gate_limit:.3f})"
                                )
                                self._last_iron_gate_log = time.time()

            # Churn Guard
            if hasattr(self, '_last_recycle_ts') and (time.time() - self._last_recycle_ts < 30.0):
                target = [lvl for lvl in target if lvl.side != getattr(self, '_last_recycle_side', '')]
                if time.time() - getattr(self, '_last_churn_log', 0) > 1.0:
                    # [ФИКС СИНТАКСИСА ТУТ]
                    logging.getLogger('gabalog.grid_strategy').info(
                        f"🛡️ [CHURN_GUARD] Блокировка откупа {getattr(self, '_last_recycle_side', '')} (30s cooldown)"
                    )
                    self._last_churn_log = time.time()

            # Timeout
            unified_stress = getattr(self, '_unified_stress_level', 0.0)
            t_limit = (
                getattr(self.config, 'refresh_timeout_panic_sec', 2.5) if unified_stress > 0.70
                else getattr(self.config, 'refresh_timeout_calm_sec', 15.0)
            )

            # Triage: расчёт гниения
            toxic_thr  = getattr(self.config, 'toxic_exit_fv_threshold', 0.04)
            side_for_tox = 'YES' if q > 0 else 'NO'
            fv_side    = fv_yes if side_for_tox == 'YES' else (1.0 - fv_yes)
            avg_side   = (
                self.position.yes_cost / max(1, self.position.total_yes)
                if side_for_tox == 'YES' else
                self.position.no_cost / max(1, self.position.total_no)
            )
            if (avg_side - fv_side) > toxic_thr:
                self._toxic_position_ticks += 1
            else:
                self._toxic_position_ticks = 0

            # Triage Logic
            target = self._apply_triage_logic(market_data, q, time_rem_sec, target)

            # Sync
            is_in_rescue = is_desperate or ("🆘[HEAL" in recovery_tag) or (self._triage_active_side is not None)

            if getattr(self, '_is_at_dead_pole', False) and not is_in_rescue:
                initial_t_len = len(target)
                target  = []
                m_state = "🧱DEAD_ZONE"
                # [WIRETAP]
                if initial_t_len > 0:
                    if time.time() - getattr(self, '_last_deadpole_kill', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(f"🪦 [DEAD_POLE_KILL] Рынок мертв (Dead Zone). Все ордера удалены. | {self._std_ctx()}")
                        self._last_deadpole_kill = time.time()

            t_limit = (
                getattr(self.config, 'refresh_timeout_panic_sec', 2.5) if unified_stress > 0.70
                else getattr(self.config, 'refresh_timeout_calm_sec', 15.0)
            )
            actions = self.grid_manager.sync(target, refresh_timeout=t_limit)

            # Post-Sync: Taker dump
            if (self.config.emergency_dump_enabled and
                    self._triage_active_side and
                    "TAKER_DUMP" in getattr(self, '_triage_decision', '')):
                if time.time() - getattr(self, '_last_dump_ts', 0) > 3.0:
                    side    = self._triage_active_side
                    bid_p   = market_data.get(f'{side.lower()}_bid', 0.0)
                    taker_p = max(0.01, bid_p - self.config.emergency_dump_slippage)
                    sell_qty = max(
                        self.config.grid_lot_size,
                        int(abs(q) * self.config.emergency_dump_sell_pct)
                    )
                    actions.append(OrderAction(
                        action='place', side=f'SELL_{side}',
                        price=round(taker_p, 2), size=sell_qty,
                        is_taker=True, reason="TRIAGE_TAKER_DUMP"
                    ))
                    self._last_dump_ts = time.time()
                    self._bankrupt_sides.add(side)

            # Статистика
            self._total_cancels += sum(1 for a in actions if a.action == 'cancel')

            # ReadOnly Guard — Early Exit
            if is_readonly:
                filtered = [a for a in actions if a.action in ['cancel', 'CANCEL_ALL_NUCLEAR']]
                return {
                    'early_exit': True,
                    'actions':    filtered,
                    'm_state':    m_state,
                }

            return {
                'early_exit': False,
                'actions':    actions,
                't_limit':    t_limit,
                'is_in_rescue': is_in_rescue,
                'm_state':    m_state,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_FINAL_SYNC_AND_TRIAGE] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.4f}, time_rem_sec={time_rem_sec:.1f}, "
                f"is_desperate={is_desperate}, is_readonly={is_readonly}, "
                f"target_len={len(target)}, active_gate_limit={active_gate_limit:.4f}"
            )
            raise

    def _run_grid_orchestrator(
        self,
        fv_yes: float,
        time_rem_sec: float,
        mid_market: float,
        q: int,
        final_lot_y: int,
        final_lot_n: int,
        l0_y: float,
        l0_n: float,
        is_desperate: bool,
        is_warmup: bool,
        is_medical_averaging: bool,
        recovery_tag: str,
        current_suppress_thr: float,
        edge_y: float,
        edge_n: float,
        adaptive_edge: float,
        m_state: str,
    ) -> dict:
        try:
            # Лимиты USD + Shares
            usd_limit        = self.config.deposit * self.config.side_usd_limit_pct
            base_share_limit = getattr(self.config, 'inventory_hard_cap', 25)

            # 2D-Сжатие Капы
            fv_certainty = abs(fv_yes - 0.5) * 2.0
            fade_start   = max(1.0, self.config.endgame_fade_start_sec)
            t_factor     = min(1.0, max(0.0, time_rem_sec / fade_start))

            if t_factor < 1.0 or fv_certainty > 0.80:
                penalty_y = (1.0 - fv_certainty) if fv_yes < 0.5 else 1.0
                penalty_n = (1.0 - fv_certainty) if fv_yes > 0.5 else 1.0
                min_cap   = getattr(self.config, 'hard_cutoff_min', 25)
                dyn_share_limit_y = max(min_cap, int(base_share_limit * t_factor * penalty_y))
                dyn_share_limit_n = max(min_cap, int(base_share_limit * t_factor * penalty_n))
                if time.time() - getattr(self, '_last_fade_log', 0) > 15.0:
                    logger.warning(
                        f"📉 [THE FADE] Эндшпиль! T-Factor: {t_factor:.2f} | Уверенность: {fv_certainty:.2f} | "
                        f"Limit Y:{dyn_share_limit_y} / N:{dyn_share_limit_n} (База:{base_share_limit})"
                    )
                    self._last_fade_log = time.time()
            else:
                dyn_share_limit_y = base_share_limit
                dyn_share_limit_n = base_share_limit
                self._last_fade_log = 0

            # Master Capitulation Switch
            if getattr(self, '_consensus_confirmed', False):
                dyn_share_limit_y = 0
                dyn_share_limit_n = 0
                m_state           = "🏁CAPITULATION"
                max_edge          = getattr(self.config, 'max_adaptive_edge', 0.15)
                edge_y = edge_n   = max_edge
                adaptive_edge     = max_edge

            # Бюджет
            in_flight_cost = (self.position.yes_in_flight + self.position.no_in_flight) * mid_market
            budget_rem = max(0.0, self.config.deposit - (
                self.position.total_cost + self.grid_manager.get_pending_notional() + in_flight_cost
            ))

            now      = time.time()
            is_panic = getattr(self, '_is_panic_frozen', False)

            # Anti-Snipe Early Exit
            if self._pre_pull_ticks_left > 0:
                self._pre_pull_ticks_left -= 1
                cancel_ids = self.grid_manager.cancel_all()
                return {
                    'early_exit': True,
                    'actions': [OrderAction(action='cancel', order_id=oid, reason="ANTI_SNIPE_COOLDOWN")
                                for oid in cancel_ids],
                }

            # Формирование целевой сетки
            target = []

            # [ПАТЧ: Пробрасываем объемы В GridManager до построения любых сеток]
            self.grid_manager.grid_lot_size_y = final_lot_y
            self.grid_manager.grid_lot_size_n = final_lot_n

            if is_warmup:
                target = []

            elif is_medical_averaging:
                side_to_buy       = 'NO' if q > 0 else 'YES'
                safe_market_price = mid_market if side_to_buy == 'YES' else (1.0 - mid_market)
                fv_for_recovery   = fv_yes if side_to_buy == 'YES' else (1.0 - fv_yes)
                safe_price        = min(safe_market_price, fv_for_recovery)
                
                # [FIX] Используем динамический лот, рассчитанный в Recovery Protocol
                # Вместо getattr(self.config, 'avg_tranche_max_size', 5)
                dynamic_size = final_lot_y if side_to_buy == 'YES' else final_lot_n

                target = [GridLevel(
                    side=side_to_buy,
                    price=round(safe_price, 2),
                    size=max(1, dynamic_size), # Гарантируем хотя бы 1 акцию
                    level_idx=0
                )]
                self._log_decision('MEDICAL_TRANCHE',
                    f"🩺 [SILENT_LOCK] Side:{side_to_buy} | Target_P:{safe_price:.3f} | Size:{dynamic_size} | Q:{q}")

            elif is_panic:
                if is_desperate:
                    weak_leg = 'NO' if q > 0 else 'YES'
                    target = self.grid_manager.calculate_target_grid(
                        budget_rem, l0_y, l0_n, weak_leg=weak_leg,
                        imbalance_shares=int(abs(q)),
                        stress_multiplier=getattr(self, '_current_stress_multiplier', 1.0),
                        is_desperate=True
                    )
                    target = [lvl for lvl in target if lvl.side == weak_leg]
                    for lvl in target:
                        if lvl.level_idx == 0:
                            lvl.intent = 'HUNTER'
                    self._log_decision('PANIC_HUNTER',
                        f"☠️ [BUNKER] Panic Active! Hunter only for {weak_leg} Q:{q}")
                else:
                    target = []
                    # [WIRETAP 1]
                    if now - getattr(self, '_last_panic_kill_log', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦 [ORCHESTRATOR_KILL] Бот в панике (Bunker), но не Desperate. Стакан заморожен."
                        )
                        self._last_panic_kill_log = now

            elif self._smooth_stress > current_suppress_thr:
                is_healing  = "🆘[HEAL" in recovery_tag
                
                # Читаем единый порог спасения (фоллбэк на YAML: 15)
                hedge_thr = getattr(self, '_dynamic_hunter_thr', getattr(self.config, 'hunter_imb_threshold', 15))

                # Разрешаем байпас только если проснулся Лекарь или пробит единый порог Охотника
                if (is_healing or abs(q) >= hedge_thr) and target:
                    target = [lvl for lvl in target if
                            (q > 0 and lvl.side == 'NO') or (q < 0 and lvl.side == 'YES')]
                    if target and (now - getattr(self, '_last_suppress_log', 0) > 15.0):
                        logger.warning(f"🚑 [HEDGE_BYPASS] Stress:{self._smooth_stress:.2f}. Reducing Q:{q}")
                        self._last_suppress_log = now
                else:
                    target = []
                    if now - getattr(self, '_last_suppress_log', 0) > 15.0:
                        logger.info(f"🐢 [SUPPRESS] Quoting paused. Stress:{self._smooth_stress:.2f}")
                        self._last_suppress_log = now

            else:
                target = self.grid_manager.calculate_target_grid(
                    budget_remaining=budget_rem, l0_yes_price=l0_y, l0_no_price=l0_n,
                    weak_leg=('NO' if q > 0 else 'YES' if q < 0 else ''),
                    imbalance_shares=int(abs(q)),
                    stress_multiplier=getattr(self, '_current_stress_multiplier', 1.0),
                    is_desperate=is_desperate
                )

                # [WIRETAP 2]
                if len(target) == 0 and budget_rem > 0:
                    if now - getattr(self, '_last_gridmgr_kill_log', 0.0) > 1.0:
                        # Диагноз причины нулевой цены
                        _kill_reasons = []
                        if l0_y <= 0.001:
                            _kill_reasons.append(f"Y=0(PP:{getattr(self,'_is_pingpong',False)}"
                                f"|Knife:{getattr(self,'_is_falling_knife',False)}"
                                f"|Tox:{getattr(self,'_is_flow_toxic',False)})")
                        if l0_n <= 0.001:
                            _kill_reasons.append(f"N=0(PP:{getattr(self,'_is_pingpong',False)}"
                                f"|Knife:{getattr(self,'_is_falling_knife',False)}"
                                f"|Tox:{getattr(self,'_is_flow_toxic',False)})")
                        if not _kill_reasons:
                            _kill_reasons.append(f"BothNonZero(Y:{l0_y:.3f},N:{l0_n:.3f})")
                        _kill_reason_str = " | ".join(_kill_reasons)
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦 [GRID_MGR_KILL] Reason:{_kill_reason_str} | Бюджет:{budget_rem:.2f} | {self._std_ctx()}"
                        )
                        self._last_gridmgr_kill_log = now

                _hunter_side = getattr(self, '_last_hunter_side', None)

                if _hunter_side:
                    for lvl in target:
                        if lvl.side == _hunter_side and lvl.level_idx == 0:
                            lvl.intent = 'HUNTER'

                if self.config.survivor_lock_enabled:
                    recently_dumped = (time.time() - getattr(self, '_last_dump_ts', 0) < 30.0)
                    if recently_dumped:
                        initial_surv_len = len(target)
                        target_filtered = []
                        for lvl in target:
                            is_hedging = (lvl.side == 'YES' and q < 0) or (lvl.side == 'NO' and q > 0)
                            if lvl.side in self._bankrupt_sides and not is_hedging:
                                continue
                            target_filtered.append(lvl)
                        target = target_filtered

                        # [WIRETAP 3]
                        if initial_surv_len > 0 and len(target) == 0:
                            if now - getattr(self, '_last_surv_kill_log', 0.0) > 1.0:
                                logging.getLogger('gabalog.grid_strategy').warning(
                                    f"🪦 [ORCHESTRATOR_KILL] Survivor Lock вырезал все ордера. Bankrupt sides: {getattr(self, '_bankrupt_sides', [])}"
                                )
                                self._last_surv_kill_log = now

            return {
                'early_exit':        False,
                'target':            target,
                'dyn_share_limit_y': dyn_share_limit_y,
                'dyn_share_limit_n': dyn_share_limit_n,
                'budget_rem':        budget_rem,
                'usd_limit':         usd_limit,
                't_factor':          t_factor,
                'fv_certainty':      fv_certainty,
                'edge_y':            edge_y,
                'edge_n':            edge_n,
                'adaptive_edge':     adaptive_edge,
                'm_state':           m_state,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_GRID_ORCHESTRATOR] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.4f}, time_rem_sec={time_rem_sec:.1f}, "
                f"is_desperate={is_desperate}, is_warmup={is_warmup}, "
                f"is_medical_averaging={is_medical_averaging}, "
                f"smooth_stress={getattr(self, '_smooth_stress', 'N/A')}"
            )
            raise

    def _run_hard_veto(
        self,
        fv_yes: float,
        mid_market: float,
        recovery_tag: str,
        q: int,
        target: list,
        is_desperate: bool = False,
    ) -> dict:
        try:
            initial_target_len = len(target)
            veto_thr = getattr(self.config, 'oracle_blindness_thr', getattr(self.config, 'blindness_floor', 0.095))
            oracle_diff = (fv_yes - mid_market)
            now = time.time()
            hedge_thr = getattr(self, '_dynamic_hunter_thr', getattr(self.config, 'hunter_imb_threshold', 15))

            # --- [DUAL-CORE VETO: ЗАЩИТА ОТ ТОРПЕДЫ] ---
            defense_state = getattr(self, '_defense_state', {})
            if defense_state.get('action') == 'VETO':
                target = []
                if now - getattr(self, '_last_dualcore_veto_log', 0) > 5.0:
                    momentum = defense_state.get('momentum', 0)
                    logger.error(f"🚨 [DUAL-CORE VETO] ТОРПЕДА! Моментум: {momentum:.3f} CVD/s | Заморозка стакана")
                    self._last_dualcore_veto_log = now

                return {
                    'target': target,
                    'veto_thr': veto_thr,
                    'oracle_diff': oracle_diff,
                    'is_bunker': True,
                }

            # === [POST-TORPEDO COOLDOWN 2026-05-13] ====================
            # After exit from TORPEDO/RECOVERY, suppress quoting for a
            # cooldown window. The orderbook is still re-stabilizing and
            # immediate re-entry catches adverse fills. _last_torpedo_exit_ts
            # is set in on_trade's regime FSM when transitioning out of
            # TORPEDO/RECOVERY → NEUTRAL.
            # Override: hedge/recovery legs are immune (we must be able to
            # unwind even mid-cooldown).
            cooldown_sec = getattr(self.config, 'post_torpedo_cooldown_sec', 15.0)
            last_exit = getattr(self, '_last_torpedo_exit_ts', 0.0)
            time_since_torpedo = now - last_exit
            in_cooldown = last_exit > 0.0 and time_since_torpedo < cooldown_sec
            is_recovering = is_desperate or bool(recovery_tag)
            if in_cooldown and not is_recovering and abs(q) <= hedge_thr:
                target = []
                if now - getattr(self, '_last_post_torpedo_log', 0.0) > 5.0:
                    logger.warning(
                        f"⏸️ [POST_TORPEDO] Cooldown {time_since_torpedo:.0f}s/"
                        f"{cooldown_sec:.0f}s — стакан восстанавливается"
                    )
                    self._last_post_torpedo_log = now
                return {
                    'target': target,
                    'veto_thr': veto_thr,
                    'oracle_diff': oracle_diff,
                    'is_bunker': True,
                }

            # Защита YES
            if oracle_diff < -veto_thr:
                is_healing_y = is_desperate or ("_Y" in recovery_tag) or ("YES" in recovery_tag)
                if (q <= -hedge_thr) or is_healing_y:
                    if now - getattr(self, '_last_veto_override_log_y', 0) > 3.0:
                        logger.warning(f"🚑 [VETO_OVERRIDE] Пропуск YES для балансировки (Q:{q})")
                        self._last_veto_override_log_y = now
                else:
                    target = [lvl for lvl in target if lvl.side != 'YES']
                    if not getattr(self, '_veto_yes_active', False):
                        if now - getattr(self, '_last_veto_log_y', 0) > 3.0:
                            logger.error(f"🛡️ [VETO] HARD LOCK YES | Рынок ({mid_market:.3f}) > Оракула ({fv_yes:.3f})")
                            self._last_veto_log_y = now
                        self._veto_yes_active = True
            else:
                self._veto_yes_active = False

            # Защита NO
            if oracle_diff > veto_thr:
                is_healing_n = is_desperate or ("_N" in recovery_tag) or ("NO" in recovery_tag)
                if (q >= hedge_thr) or is_healing_n:
                    if now - getattr(self, '_last_veto_override_log_n', 0) > 3.0:
                        logger.warning(f"🚑 [VETO_OVERRIDE] Пропуск NO для балансировки (Q:{q})")
                        self._last_veto_override_log_n = now
                else:
                    target = [lvl for lvl in target if lvl.side != 'NO']
                    if not getattr(self, '_veto_no_active', False):
                        if now - getattr(self, '_last_veto_log_n', 0) > 3.0:
                            logger.error(f"🛡️ [VETO] HARD LOCK NO | Рынок ({1.0-mid_market:.3f}) > Оракула ({1.0-fv_yes:.3f})")
                            self._last_veto_log_n = now
                        self._veto_no_active = True
            else:
                self._veto_no_active = False

            is_bunker = getattr(self, '_is_panic_frozen', False)

            if initial_target_len > 0 and len(target) == 0:
                if now - getattr(self, '_last_oracle_kill_log', 0.0) > 1.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦 [ORACLE_KILL] Все ордера удалены. Оракул заблокировал обе стороны. Diff: {oracle_diff:.3f}"
                    )
                    self._last_oracle_kill_log = now

            return {
                'target': target,
                'veto_thr': veto_thr,
                'oracle_diff': oracle_diff,
                'is_bunker': is_bunker,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_HARD_VETO] CRITICAL ERROR: {e} | "
                f"fv_yes={fv_yes:.4f}, mid_market={mid_market:.4f}, "
                f"q={q}, target_len={len(target)}, "
                f"oracle_diff={fv_yes - mid_market:.4f}"
            )
            raise

    def _run_hedge_immunity(
        self,
        target: list,
        q: int,
        eval_y_shares: float,
        eval_y_cost: float,
        eval_n_shares: float,
        eval_n_cost: float,
        dyn_share_limit_y: float,
        dyn_share_limit_n: float,
        usd_limit: float,
        MAX_SKEW_DELTA: float,
    ) -> dict:
        try:
            hedge_thr = getattr(self, '_dynamic_hunter_thr', getattr(self.config, 'hunter_imb_threshold', 15))

            vol_blocked_y = (eval_y_shares >= dyn_share_limit_y) or (eval_y_cost >= usd_limit)
            vol_blocked_n = (eval_n_shares >= dyn_share_limit_n) or (eval_n_cost >= usd_limit)

            is_yes_blocked = (vol_blocked_y and not (q < -hedge_thr)) or (q > MAX_SKEW_DELTA)
            is_no_blocked  = (vol_blocked_n and not (q > hedge_thr)) or (q < -MAX_SKEW_DELTA)

            now = time.time()

            # Блокировка YES
            if is_yes_blocked:
                is_rescue_y = (q < -hedge_thr)
                if not is_rescue_y:
                    target = [l for l in target if l.side != 'YES']
                if not getattr(self, '_lock_yes_active', False):
                    if now - getattr(self, '_last_lock_log_y', 0) > 3.0:
                        if q > MAX_SKEW_DELTA:
                            reason_y = f"SKEW_DELTA (Q:{q} > {MAX_SKEW_DELTA})"
                        elif self.position.yes_cost >= usd_limit:
                            reason_y = f"USD_LIMIT (${self.position.yes_cost:.1f})"
                        else:
                            reason_y = f"SIZE_LIMIT ({self.position.yes_shares}sh)"
                        logger.warning(f"🛑 [INVENTORY LOCK] ENTER YES | Причина: {reason_y}")
                        self._last_lock_log_y = now
                    self._lock_yes_active = True
            else:
                if getattr(self, '_lock_yes_active', False):
                    logger.info("🔓 [INVENTORY LOCK] EXIT YES | Лимиты в норме")
                    self._lock_yes_active = False

            # Блокировка NO
            if is_no_blocked:
                is_rescue_n = (q > hedge_thr)
                if not is_rescue_n:
                    target = [l for l in target if l.side != 'NO']
                if not getattr(self, '_lock_no_active', False):
                    if now - getattr(self, '_last_lock_log_n', 0) > 3.0:
                        if q < -MAX_SKEW_DELTA:
                            reason_n = f"SKEW_DELTA (Q:{q} < -{MAX_SKEW_DELTA})"
                        elif self.position.no_cost >= usd_limit:
                            reason_n = f"USD_LIMIT (${self.position.no_cost:.1f})"
                        else:
                            reason_n = f"SIZE_LIMIT ({self.position.no_shares}sh)"
                        logger.warning(f"🛑 [INVENTORY LOCK] ENTER NO | Причина: {reason_n}")
                        self._last_lock_log_n = now
                    self._lock_no_active = True
            else:
                if getattr(self, '_lock_no_active', False):
                    logger.info("🔓 [INVENTORY LOCK] EXIT NO | Лимиты в норме")
                    self._lock_no_active = False

            return {
                'target':        target,
                'is_yes_blocked': is_yes_blocked,
                'is_no_blocked':  is_no_blocked,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_HEDGE_IMMUNITY] CRITICAL ERROR: {e} | "
                f"q={q}, target_len={len(target)}, "
                f"eval_y_shares={eval_y_shares:.1f}, eval_n_shares={eval_n_shares:.1f}, "
                f"dyn_share_limit_y={dyn_share_limit_y:.1f}, dyn_share_limit_n={dyn_share_limit_n:.1f}, "
                f"usd_limit={usd_limit:.2f}, MAX_SKEW_DELTA={MAX_SKEW_DELTA}"
            )
            raise

    def _run_grid_pruning(
        self,
        q: int,
        target: list,
        now: float,
        momentum_side_lock: str,
    ) -> dict:
        try:
            _abs_q     = abs(q)
            _heavy_side = 'YES' if q > 0 else 'NO'

            initial_target_len = len(target)

            current_hc  = getattr(self, '_dynamic_hard_cutoff', 350)

            # Уровень 1: убираем L2+ при 50% лимита
            if _abs_q >= int(current_hc * 0.5):
                target = [lvl for lvl in target if not (lvl.side == _heavy_side and lvl.level_idx >= 2)]

            # Уровень 2: оставляем только L0 при 80% лимита
            if _abs_q >= int(current_hc * 0.8):
                target = [lvl for lvl in target if not (lvl.side == _heavy_side and lvl.level_idx >= 1)]

            # Уровень 3: полная блокировка на 100% лимита
            if _abs_q >= current_hc:
                target = [lvl for lvl in target if lvl.side != _heavy_side]
                if now - getattr(self, '_last_disc_log', 0) > 20.0:
                    logger.warning(f"🛡️ [DISCIPLINE] Full Lock {_heavy_side} at Q:{q}/{current_hc}. Capacity reached.")
                    self._last_disc_log = now

            # Направленная блокировка по импульсу BTC
            if momentum_side_lock:
                target = [lvl for lvl in target if lvl.side != momentum_side_lock]

            # Emergency dump / recycling фильтр
            if getattr(self, '_emergency_dump_fired', False) or getattr(self, '_recycling_sell_active', False):
                hv_side = 'YES' if q > 0 else 'NO'
                hv_cost = self.position.yes_cost if hv_side == 'YES' else self.position.no_cost
                hv_sh   = self.position.yes_shares if hv_side == 'YES' else self.position.no_shares
                avg     = hv_cost / max(1, hv_sh)
                target  = [lvl for lvl in target if not (lvl.side == hv_side and lvl.price > (avg - 0.005))]

            if initial_target_len > 0 and len(target) == 0:
                if now - getattr(self, '_last_pruning_kill_log', 0.0) > 1.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦 [PRUNING_KILL] Уборщик стер все котировки. Q:{q}/{current_hc} | ImpLock:{momentum_side_lock} | Dump:{getattr(self, '_emergency_dump_fired', False)}"
                    )
                    self._last_pruning_kill_log = now

            return {
                'target':      target,
                '_abs_q':      _abs_q,
                '_heavy_side': _heavy_side,
                'current_hc':  current_hc,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_GRID_PRUNING] CRITICAL ERROR: {e} | "
                f"q={q}, target_len={len(target)}, "
                f"momentum_side_lock={momentum_side_lock}, "
                f"current_hc={getattr(self, '_dynamic_hard_cutoff', 'N/A')}"
            )
            raise

    def _apply_smart_gc(
        self,
        oracle_fv: float,
        q: int,
        recovery_tag: str,
        yes_bid: float,
        no_bid: float,
        l0_y: float,
        l0_n: float,
    ) -> dict:
        try:
            dist_base = getattr(self.config, 'garbage_dist_base', 0.08)
            dist_thr  = dist_base * (2.5 if abs(oracle_fv - 0.5) > 0.25 else 1.0)

            hedge_thr     = getattr(self.config, 'hunter_imb_threshold', 20)
            saving_leg    = 'YES' if q < -hedge_thr else 'NO' if q > hedge_thr else None
            in_rescue_mode = (
                (abs(q) > hedge_thr) or
                getattr(self, 'is_medical_averaging', False) or
                ("🆘[HEAL" in recovery_tag)
            )

            MAX_PREMIUM = getattr(self.config, 'toxic_max_premium', 0.06)

            # СТАЛО:
            # [П3 v2.5] Балансирующая нога получает иммунитет в RESTORE_BALANCE
            # При Oracle lag в TORPEDO FV-based bid стоит ниже рынка — GC убивал его
            # В maker-only stale bid не опасен: заполняется только если рынок сам придёт
            _is_restore = (getattr(self, '_intent_mode', 'BALANCED') == 'RESTORE_BALANCE')

            # [v2.6] SPLIT IMMUNITY: два независимых флага для двух разных угроз
            # has_immunity → TOXIC_CAP: защита от реальной переплаты выше FV+premium
            #                Строгий: только rescue/restore режимы. Без изменений.
            # gc_immune    → GARBAGE: защита от stale oracle lag на закрывающей ноге
            #                Мягкий: любая нога идущая против перекоса получает иммунитет.
            #                В maker-only stale bid не опасен — заполнится только если
            #                рынок сам придёт. Убивать через GC нет смысла.

            # YES
            yes_has_immunity = (in_rescue_mode and saving_leg == 'YES') or \
                            (_is_restore and q < 0)
            yes_gc_immune    = yes_has_immunity or (q <= 0)  # [v2.6] Q=0: нет риска → иммунитет
            is_toxic_y = (l0_y > oracle_fv + MAX_PREMIUM)

            if is_toxic_y and not yes_has_immunity:
                safe_limit_y = oracle_fv + MAX_PREMIUM
                self._log_decision('TOXIC_CAP_Y',
                    f"☢️ [TOXIC_CAP] YES {l0_y:.3f} > FV. Capped to {safe_limit_y:.3f}")
                l0_y = safe_limit_y

            if not yes_gc_immune and (yes_bid > 0 and l0_y > 0 and (yes_bid - l0_y) > dist_thr):
                self._log_decision('GARBAGE_Y', f"🧹 [GARBAGE] YES too far. Cleaning.")
                l0_y = 0.0

            # NO
            no_has_immunity = (in_rescue_mode and saving_leg == 'NO') or \
                            (_is_restore and q > 0)
            no_gc_immune    = no_has_immunity or (q >= 0)  # [v2.6] Q=0: нет риска → иммунитет
            is_toxic_n = (l0_n > (1.0 - oracle_fv) + MAX_PREMIUM)

            if is_toxic_n and not no_has_immunity:
                safe_limit_n = (1.0 - oracle_fv) + MAX_PREMIUM
                self._log_decision('TOXIC_CAP_N',
                    f"☢️ [TOXIC_CAP] NO {l0_n:.3f} > FV. Capped to {safe_limit_n:.3f}")
                l0_n = safe_limit_n

            if not no_gc_immune and (no_bid > 0 and l0_n > 0 and (no_bid - l0_n) > dist_thr):
                self._log_decision('GARBAGE_N', f"🧹 [GARBAGE] NO too far. Cleaning.")
                l0_n = 0.0

            return {
                'l0_y':        l0_y,
                'l0_n':        l0_n,
                'dist_thr':    dist_thr,
                'in_rescue_mode': in_rescue_mode,
                'saving_leg':  saving_leg,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[APPLY_SMART_GC] CRITICAL ERROR: {e} | "
                f"l0_y={l0_y:.4f}, l0_n={l0_n:.4f}, "
                f"oracle_fv={oracle_fv:.4f}, q={q}, "
                f"yes_bid={yes_bid:.4f}, no_bid={no_bid:.4f}"
            )
            raise

    def _apply_maq_filter(
        self,
        t_kelly: float,
        fv_yes: float,
        recovery_tag: str,
        l0_y: float,
        l0_n: float,
        TICK_SIZE: float,
        open_q: int = 0,
        current_btc: float = 0.0,
        strike: float = 0.0,
        time_rem: float = 900.0,
    ) -> dict:
        try:
            # Theta-MAQ
            MAQ_BASE    = getattr(self.config, 'MAQ_BASE', 0.06)
            dynamic_maq = MAQ_BASE * (0.25 + 0.75 * t_kelly)

            trend_thr = getattr(self.config, 'maq_trend_threshold', 0.30)
            trend_maq = getattr(self.config, 'maq_trend_value', 0.025)

            if abs(fv_yes - 0.50) > trend_thr:
                dynamic_maq = trend_maq
                if time.time() - getattr(self, '_last_maq_shift_log', 0) > 60.0:
                    logger.info(f"📉 [MAQ_SHIFT] Порог снижен до {dynamic_maq} (Тренд активен)")
                    self._last_maq_shift_log = time.time()

            # [GAMMA DISCOUNT] Снижаем MAQ в зоне высокой Gamma
            elif (strike > 1000 and current_btc > 1000 and time_rem > 180.0):
                dist_to_strike = abs(current_btc - strike)
                if dist_to_strike < 150.0:
                    trust = getattr(self, '_current_oracle_weight', 1.0)
                    smooth_stress = getattr(self, '_smooth_stress', 0.0)
                    _regime = getattr(self, '_market_regime', 'NEUTRAL')
                    if trust > 0.5 and smooth_stress < 0.3 and _regime not in ('TORPEDO', 'RECOVERY'):
                        # ПАТЧ: Выносим хардкод 0.5 в конфиг
                        min_disc = getattr(self.config, 'gamma_maq_min_discount', 0.5)
                        gamma_discount = min_disc + ((1.0 - min_disc) * (dist_to_strike / 150.0))
                        dynamic_maq = dynamic_maq * gamma_discount
                        if time.time() - getattr(self, '_last_gamma_maq_log', 0) > 30.0:
                            logger.info(
                                f"🎯 [GAMMA_MAQ] Dist:${dist_to_strike:.0f} | "
                                f"Discount:{gamma_discount:.2f} | "
                                f"MAQ:{dynamic_maq:.4f} | T:{time_rem:.0f}s"
                            )
                            self._last_gamma_maq_log = time.time()

            # Healer VIP — иммунитет от MAQ фильтра
            is_healing_now = ("🆘[HEAL" in recovery_tag) or \
                             (getattr(self, '_intent_mode', 'BALANCED') == 'RESTORE_BALANCE')
            eff_maq = 0.001 if is_healing_now else dynamic_maq

            # [!] АСИММЕТРИЯ ДЛЯ ПРИВЛЕЧЕНИЯ ХЕДЖА
            # Читаем порог из конфига. Фолбэк: 50% от порога Охотника.
            default_fallback = int(getattr(self.config, 'hunter_imb_threshold', 20) * 0.5)
            hedge_thr = int(getattr(self.config, 'maq_asym_hedge_threshold', default_fallback))

            maq_y = 0.0 if (open_q < -hedge_thr) else eff_maq  # Много NO -> берем YES дешево
            maq_n = 0.0 if (open_q > hedge_thr)  else eff_maq  # Много YES -> берем NO дешево

            # Фильтрация YES
            if 0.0 < l0_y < maq_y:
                if time.time() - getattr(self, '_last_maq_log_y', 0) > 3.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦 [MAQ_KILL] YES ордер удален (цена {l0_y:.3f} < лимита {maq_y:.3f})"
                    )
                    self._last_maq_log_y = time.time()
                l0_y = 0.0

            # Фильтрация NO
            if 0.0 < l0_n < maq_n:
                if time.time() - getattr(self, '_last_maq_log_n', 0) > 3.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦 [MAQ_KILL] NO ордер удален (цена {l0_n:.3f} < лимита {maq_n:.3f})"
                    )
                    self._last_maq_log_n = time.time()
                l0_n = 0.0

            log_maq = eff_maq

            # Финальное округление
            l0_y = round(l0_y / TICK_SIZE) * TICK_SIZE
            l0_n = round(l0_n / TICK_SIZE) * TICK_SIZE

            return {
                'l0_y':        l0_y,
                'l0_n':        l0_n,
                'dynamic_maq': dynamic_maq,
                'eff_maq':     eff_maq,
                'log_maq':     log_maq,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[APPLY_MAQ_FILTER] CRITICAL ERROR: {e} | "
                f"l0_y={l0_y:.4f}, l0_n={l0_n:.4f}, "
                f"fv_yes={fv_yes:.4f}, t_kelly={t_kelly:.3f}, "
                f"recovery_tag={recovery_tag}"
            )
            raise

    def _apply_bbo_clamp(
        self,
        fv_yes: float,
        edge_y: float,
        edge_n: float,
        p_yes: float,
        eff_delta: float,
        l0_y: float,
        l0_n: float,
        yes_ask: float,
        yes_bid: float,
        no_ask: float,
        no_bid: float,
        TICK_SIZE: float,
    ) -> dict:
        try:
            # MATH_XRAY лог (раз в 3 секунд)
            if time.time() - getattr(self, '_last_xray_log', 0) > 3.0: # <--- 0.1s
                logging.getLogger('gabalog.grid_strategy').info(
                    f"🧮 [MATH_XRAY] FV:{fv_yes:.3f} | "
                    f"Edge_Y:-{edge_y:.3f} | Edge_N:-{edge_n:.3f} | "
                    f"Skew_Force:{p_yes:+.3f} | "
                    f"Stress_Mult:x{self._current_stress_multiplier:.2f}(Δ{eff_delta:.3f}) | "
                    f"RESULT_L0:{l0_y:.3f}"
                )
                self._last_xray_log = time.time()

            # BBO Clamp
            clip_y_tag, clip_n_tag = "", ""
            empty_premium = getattr(self.config, 'empty_book_premium', 0.10)
            now = time.time()

            safe_ask_y = yes_ask if yes_ask > 0.0 else min(1.00, fv_yes + empty_premium)
            safe_ask_n = no_ask  if no_ask  > 0.0 else min(1.00, (1.0 - fv_yes) + empty_premium)

            # === UPPER CLAMP: don't cross the spread ===
            if l0_y >= safe_ask_y:
                orig_y = l0_y
                l0_y = safe_ask_y - TICK_SIZE
                clip_y_tag = "✂️"
                if l0_y <= 0.01:
                    if now - getattr(self, '_last_clamp_kill_y', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦 [CLAMP_KILL] YES ордер раздавлен стаканом: Расчетная {orig_y:.3f} уперлась в Ask {safe_ask_y:.3f} -> Итог {l0_y:.3f}"
                        )
                        self._last_clamp_kill_y = now

            if l0_n >= safe_ask_n:
                orig_n = l0_n
                l0_n = safe_ask_n - TICK_SIZE
                clip_n_tag = "✂️"
                if l0_n <= 0.01:
                    if now - getattr(self, '_last_clamp_kill_n', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦 [CLAMP_KILL] NO ордер раздавлен стаканом: Расчетная {orig_n:.3f} уперлась в Ask {safe_ask_n:.3f} -> Итог {l0_n:.3f}"
                        )
                        self._last_clamp_kill_n = now

            # === LOWER CLAMP: pull-up to BBO ONLY on closing leg ===
            # 2026-05-13 (rev 2 — Variant B). Initial revision pulled BOTH
            # legs up to BBO and that destroyed the "edge below FV" intent
            # for opening legs (realized_ps went 1.03 → 1.07). The actual
            # need is asymmetric:
            #
            #   • Opening leg (grows the position): keep the original
            #     behavior — sit deeper in queue, collect edge when filled.
            #     Adverse selection here is fine because every fill builds
            #     our pair-lock cheap.
            #   • Closing leg (reduces position imbalance): pull up to BBO
            #     bid (queue top) so the pair actually locks. The bleed in
            #     forensics came from never closing — quotes stuck deep in
            #     queue while market drifts away → realized_ps > 1.0.
            #
            # Side mapping (per existing convention in
            # _compute_spread_and_shield): when q > 0 (heavy YES), the NO
            # leg is the one we need to fill to close → NO is closing.
            # When q < 0 (heavy NO), YES is closing. When |q| is small,
            # neither leg is "closing" — both are opening, keep old.
            bbo_max_spread = getattr(self.config, 'bbo_max_spread', 0.06)
            _open_q = getattr(self, '_last_open_q', 0)
            _hedge_thr = getattr(self, '_dynamic_hunter_thr',
                                 getattr(self.config, 'hunter_imb_threshold', 5))
            _yes_is_closing = _open_q < -_hedge_thr   # heavy NO ⇒ buying YES closes
            _no_is_closing  = _open_q > _hedge_thr    # heavy YES ⇒ buying NO closes

            # Wide-spread withdraw applies to BOTH legs always (toxic book
            # protection — independent of closing/opening).
            if yes_bid > 0.0 and l0_y > 0.0:
                _yspread = (safe_ask_y - yes_bid) if safe_ask_y > yes_bid else 0.0
                if _yspread > bbo_max_spread:
                    l0_y = 0.0
                    clip_y_tag += "🚫WIDE"
                elif _yes_is_closing and l0_y < yes_bid:
                    l0_y = yes_bid
                    clip_y_tag += "⬆️BBO_CLOSE"

            if no_bid > 0.0 and l0_n > 0.0:
                _nspread = (safe_ask_n - no_bid) if safe_ask_n > no_bid else 0.0
                if _nspread > bbo_max_spread:
                    l0_n = 0.0
                    clip_n_tag += "🚫WIDE"
                elif _no_is_closing and l0_n < no_bid:
                    l0_n = no_bid
                    clip_n_tag += "⬆️BBO_CLOSE"

            l0_y = max(0.0, l0_y)
            l0_n = max(0.0, l0_n)

            return {
                'l0_y':      l0_y,
                'l0_n':      l0_n,
                'clip_y_tag': clip_y_tag,
                'clip_n_tag': clip_n_tag,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[APPLY_BBO_CLAMP] CRITICAL ERROR: {e} | "
                f"l0_y={l0_y:.4f}, l0_n={l0_n:.4f}, "
                f"yes_ask={yes_ask:.4f}, no_ask={no_ask:.4f}, fv_yes={fv_yes:.4f}"
            )
            raise

    def _apply_profit_gate_sanitizer(
        self,
        q: int,
        is_desperate: bool,
        final_lot_y: int,
        final_lot_n: int,
        recovery_tag: str,
        l0_y: float,
        l0_n: float,
        is_flow_toxic: bool = False,
    ) -> dict:
        try:            
            # Базу берем из динамического стейта, а не из YAML
            base_gate      = getattr(self, '_tick_base_gate', getattr(self.config, 'profit_gate_ps_max', 0.985))
            veto_panic_gate = getattr(self.config, 'veto_panic_gate', 1.050)
            hedge_thr = getattr(self, '_dynamic_hunter_thr',
                getattr(self.config, 'hunter_imb_threshold', 20))
            hunter_scale   = getattr(self.config, 'hunter_escalation_shares', 10.0)

            # [ПАТЧ 1] Дышащий гейт: плавно расширяем базу, если растет хвост
            if abs(q) > 5:
                base_gate += min(0.015, (abs(q) - 5) * 0.0015)

            # Динамический лимит VETO с ЖЕСТКИМ КЛАМПОМ
            if is_desperate and abs(q) > 0:
                imb_ratio   = max(0.0, min(1.0, (abs(q) - hedge_thr) / hunter_scale))
                calculated_max = base_gate + (veto_panic_gate - base_gate) * imb_ratio
                max_gate_val = min(veto_panic_gate, calculated_max) # Запрещаем пробивать VETO
                
                if time.time() - getattr(self, '_last_salvage_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🚑 [SALVAGE MODE] Лимит VETO разблокирован: {max_gate_val:.3f} | Q:{q}"
                    )
                    self._last_salvage_log = time.time()
            else:
                max_gate_val = base_gate

            # Динамический градиентный иммунитет
            is_immune = abs(q) > hedge_thr

            # [FLOW TOXIC BYPASS] Healer заблокирован потоком — Hunter получает расширенный gate
            if is_flow_toxic and not is_immune:
                max_gate_val = min(veto_panic_gate, max_gate_val + 0.015)
                is_immune = True  

            # 1. Сначала определяем лимиты Гейта (допустимую стоимость ПАРЫ)
            gate_y = max_gate_val
            gate_n = max_gate_val

            if is_immune:
                # Охотник имеет право собирать пару за 1.00
                if q < 0: gate_y = max(max_gate_val, 1.00)
                if q > 0: gate_n = max(max_gate_val, 1.00)
            elif "🆘" in recovery_tag:
                rescue_limit = getattr(self.config, 'rescue_overpay_limit', 1.01)
                # Лекарь получает лимит спасения (например, 1.01)
                if q < 0: gate_y = max(max_gate_val, rescue_limit)
                if q > 0: gate_n = max(max_gate_val, rescue_limit)

            # 2. И ТОЛЬКО ТЕПЕРЬ вычисляем цену 1 токена через Бухгалтера
            # [HEDGE BYPASS] Hunter-нога обходит avg_cost ограничение
            if is_immune and q < 0:
                safe_y = gate_y  # Hunter покупает YES по рынку без бухгалтера
            else:
                safe_y = self._calculate_max_safe_price('YES', final_lot_y, gate_y)
            if is_immune and q > 0:
                safe_n = gate_n  # Hunter покупает NO по рынку без бухгалтера
            else:
                safe_n = self._calculate_max_safe_price('NO',  final_lot_n, gate_n)

            label_y = "H" if q < 0 else "M"
            label_n = "H" if q > 0 else "M"

            if l0_y > safe_y:
                if l0_y > 0.01:
                    if safe_y <= 0.01:
                         logging.getLogger('gabalog.grid_strategy').warning(f"🪦 [GATE_KILL] YES ордер убит (цена сброшена с {l0_y:.3f} в 0.0). Причина: Бухгалтер (Gate:{gate_y:.3f})")
                    else:
                        self._log_decision('GLOBAL_VETO_Y',
                            f"🛡️ [VETO_{label_y}] YES cut: {l0_y:.3f} -> {safe_y:.3f} | "
                            f"Gate:{gate_y:.3f} | Q:{q} | Desp:{is_desperate} | Tag:{recovery_tag[:12]}")
                l0_y = safe_y if safe_y > 0.01 else 0.0

            if l0_n > safe_n:
                if l0_n > 0.01:
                    if safe_n <= 0.01:
                         logging.getLogger('gabalog.grid_strategy').warning(f"🪦 [GATE_KILL] NO ордер убит (цена сброшена с {l0_n:.3f} в 0.0). Причина: Бухгалтер (Gate:{gate_n:.3f})")
                    else:
                        self._log_decision('GLOBAL_VETO_N',
                            f"🛡️ [VETO_{label_n}] NO cut: {l0_n:.3f} -> {safe_n:.3f} | "
                            f"Gate:{gate_n:.3f} | Q:{q} | Desp:{is_desperate} | Tag:{recovery_tag[:12]}")
                l0_n = safe_n if safe_n > 0.01 else 0.0

            return {
                'l0_y':        l0_y,
                'l0_n':        l0_n,
                'max_gate_val': max_gate_val,
                'safe_y':      safe_y,
                'safe_n':      safe_n,
                'label_y':     label_y,
                'label_n':     label_n,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[APPLY_PROFIT_GATE_SANITIZER] CRITICAL ERROR: {e} | "
                f"q={q}, is_desperate={is_desperate}, "
                f"l0_y={l0_y:.4f}, l0_n={l0_n:.4f}, "
                f"final_lot_y={final_lot_y}, final_lot_n={final_lot_n}"
            )
            raise

    def _run_toxic_recovery_protocol(
        self,
        active_gate_limit: float,
        market_data: dict,
        q: int,
        fv_yes: float,
        y_avg: float,
        n_avg: float,
        is_deadlocked: bool,
        _weak_side: str,
        edge_y: float,
        edge_n: float,
        hunter_gate: float,
        _probe_safe: float,
        final_lot_y: int,
        final_lot_n: int,
        p_yes: float,
        p_no: float,
        recovery_tag: str,
        yes_ask: float,
        no_ask: float,
        TICK_SIZE: float,
        is_active_y: bool, # <--- ДОБАВИТЬ ЭТО
        is_active_n: bool, # <--- ДОБАВИТЬ ЭТО
    ) -> dict:
        try:
            inv_ps_limit = active_gate_limit
            toxic_thr  = getattr(self.config, 'toxic_exit_fv_threshold', 0.04)
            
            # [ПАТЧ] Берем умный транш (половина перекоса), который мы считали в lot_sizing
            avg_tranche = getattr(self, '_dynamic_avg_tranche_max_size', getattr(self.config, 'avg_tranche_max_size', 5))
            disc_cents = getattr(self.config, 'recovery_discount_cents', 0.005)

            mkt_y_ask = market_data.get('yes_ask', 0.5)
            mkt_n_ask = market_data.get('no_ask', 0.5)

            # Дефолты для L0 стандартных цен
            l0_y_std = None
            l0_n_std = None

            if abs(q) == 0:
                self._bankrupt_sides.clear()

            # [v2.7 P3] Конфигурируемый порог TIME_HEAL для будущих гипотез
            _stuck_thr = getattr(self.config, 'time_heal_stuck_threshold_sec', 30.0)
            _stuck_q_min = getattr(self.config, 'time_heal_q_min', 15)
            
            for _side in ['YES', 'NO']:
                # [ПАТЧ: УВАЖЕНИЕ К МЬЮТЕКСУ]
                _is_allowed = is_active_y if _side == 'YES' else is_active_n
                
                # [v2.7 P3] TIME_HEAL Escape Hatch (порог 30с — 3.3% от 900с рынка)
                # Хардкод временно — вынесем в config когда определим оптимум данными
                _time_since_fill_pre = time.time() - getattr(self, '_last_fill_ts', time.time())
                _is_stuck_pre = (abs(q) > 15) and (_time_since_fill_pre > 30.0)
                _correct_side_stuck = (
                    (_side == 'YES' and q > 0) or
                    (_side == 'NO' and q < 0)
                )
                
                if not _is_allowed and not (_is_stuck_pre and _correct_side_stuck):
                    continue

                if getattr(self.config, 'survivor_lock_enabled', True) and _side in self._bankrupt_sides:

                    # --- ВСТАВЛЯЕМ ЖУЧОК СЮДА ---
                    if is_deadlocked:
                        now_ts = time.time()
                        if now_ts - getattr(self, '_last_quarantine_wiretap', 0) > 15.0:
                            logging.getLogger('gabalog.grid_strategy').warning(
                                f"🪦🔒🆘 [QUARANTINE_STUCK] {_side} заблокирована в карантине при Deadlock! "
                                f"Q: {q} | BankruptSides: {list(self._bankrupt_sides)}"
                            )
                            self._last_quarantine_wiretap = now_ts
                    # ----------------------------

                    if is_deadlocked and _side == _weak_side:
                        self._log_decision('SURVIVOR_LOCK_OVERRIDE',
                            f"⚠️ [SURVIVAL_LOCK_OVERRIDE] {_side} quarantine lifted — DEADLOCK rescue")
                    else:
                        self._log_decision('SURVIVOR_LOCK',
                            f"🚫 [SURVIVAL_LOCK] {_side} in quarantine...")
                        continue

                # [v2.10 P7] Возврат разумного порога: 380 событий из 3393 на |Q|≤2 — 
                # Лекарь работал бессмысленно (микро-перекосы должны разруливаться через Standard).
                # Окно теперь Q ∈ [6..11] — 6 значений, достаточно с учётом частичных филлов.
                _is_heavy = (q > 5 and _side == 'YES') or (q < -5 and _side == 'NO')
                if not _is_heavy:
                    continue

                _death_line = getattr(self.config, 'knife_protection_cents', 0.15)
                _u_loss = (y_avg - fv_yes) if _side == 'YES' else (n_avg - (1.0 - fv_yes))
                if _u_loss > _death_line:
                    # [WIRETAP 1] Исправленный синтаксис
                    _last_log_attr = f'_last_triage_log_{_side}'
                    if time.time() - getattr(self, _last_log_attr, 0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦💀 [TRIAGE_DEATH] Спасение {_side} невозможно. Loss:{_u_loss:.3f} > Limit:{_death_line:.3f}"
                        )
                        setattr(self, _last_log_attr, time.time())
                    self._log_decision('TRIAGE', f"Loss too high: {_u_loss:.3f}")
                    continue

                # [FIX] Не усредняем проигрывающую ногу у полюса
                _fv_confirms_loss = (
                    (_side == 'YES' and fv_yes < 0.15) or
                    (_side == 'NO' and fv_yes > 0.85)
                )
                if _fv_confirms_loss:
                    self._log_decision('TRIAGE_POLE',
                        f"⚫ [POLE_BLOCK] {_side} blocked — FV:{fv_yes:.3f}")
                    continue

                if _side == 'YES':
                    _avg       = self.position.yes_cost / max(1, self.position.total_yes)
                    _other_ask = mkt_n_ask
                    _fv_side   = fv_yes
                else:
                    _avg       = self.position.no_cost / max(1, self.position.total_no)
                    _other_ask = mkt_y_ask
                    _fv_side   = (1.0 - fv_yes)

                gate_locked  = (_avg + _other_ask) > inv_ps_limit
                unreal_loss  = _avg - _fv_side
                time_since_fill = time.time() - getattr(self, '_last_fill_ts', time.time())
                is_stuck_time   = (abs(q) > 15) and (time_since_fill > 30.0)

                # [v17.2] ACTIVE_MIRROR_AVERAGING (ОТПАТЧЕНО ОТ "ПАДАЮЩИХ НОЖЕЙ")
                side_mkt_bid = market_data.get('yes_bid' if _side == 'YES' else 'no_bid', 0.0)
                # [PATCH] CVD-торпеда: Mirror не усредняется против направленного потока
                _cvd_mirror  = getattr(self, '_cvd_signal_last', 0.0)
                _def_state   = getattr(self, '_defense_state', {})
                _momentum    = _def_state.get('momentum', 0.0)
                btc_vel      = getattr(self, '_last_btc_velocity', 0.0)
                vel_thr      = getattr(self.config, 'btc_vel_stress_threshold', 40.0)

                # Torpedo требует подтверждения через momentum ИЛИ BTC velocity
                _torpedo_confirmed = (_momentum < -0.15) or (btc_vel > vel_thr * 0.6)

                _hunter_thr_m = getattr(self, '_dynamic_hunter_thr', 15)
                _q_ratio_m = min(1.0, abs(q) / max(1, _hunter_thr_m))
                _mirror_cvd_thr = 0.30 + (_q_ratio_m * 0.40)  # Q=0→0.30, Q=thr→0.70

                _torpedo_vs_yes  = (q > 0 and _cvd_mirror < -_mirror_cvd_thr)
                _torpedo_vs_no   = (q < 0 and _cvd_mirror > _mirror_cvd_thr)
                _cvd_blocks_mirror = (_torpedo_vs_yes or _torpedo_vs_no) and _torpedo_confirmed

                 # [BLOCK_CTX]
                if _cvd_blocks_mirror:
                    _mir_reason = f"CVD:{_cvd_mirror:+.3f}|mom:{_momentum:.3f}|btc_vel:{btc_vel:.1f}"
                else:
                    _mir_reason = f"CVD:{_cvd_mirror:+.3f} — проход разрешён"
                self._log_block_state('MIRROR_CVD', _cvd_blocks_mirror, _mir_reason)

                mirror_min_improvement = getattr(self.config, 'mirror_min_improvement', 0.04)
                is_real_mirror_trap = gate_locked and (_u_loss < 0.025) and not _cvd_blocks_mirror

                if is_real_mirror_trap and side_mkt_bid > 0 and side_mkt_bid < (_avg - mirror_min_improvement):
                    # [v2.7 P2] Bug fix: bid + TICK пересекал orderbook (нарушение политики best_bid)
                    # Ставим НА best_bid (join очереди) — биржа примет, мы в первом эшелоне
                    healer_price = round(side_mkt_bid, 2)
                    # [PATCH] avg_tranche *= 2 убран — стандартный размер транша, без удвоения
                    
                    if _side == 'YES':
                        l0_y_std    = healer_price
                        final_lot_y = max(final_lot_y, avg_tranche)
                        p_no = 0.0  # <--- [ФИКС] УБИВАЕМ ВСТРЕЧНУЮ НОГУ, ЧТОБЫ НЕ БИЛ VETO!
                    else:
                        l0_n_std    = healer_price
                        final_lot_n = max(final_lot_n, avg_tranche)
                        p_yes = 0.0 # <--- [ФИКС] УБИВАЕМ ВСТРЕЧНУЮ НОГУ!

                    recovery_tag += f"🌀[HEAL_MIRROR_{_side}]"
                    
                    # [WIRETAP 2A]
                    _side_bid = market_data.get('yes_bid' if _side == 'YES' else 'no_bid', 0.0)
                    if healer_price > 0 and _side_bid > 0 and (_side_bid - healer_price) > 0.05:
                        logging.getLogger('gabalog.grid_strategy').warning(f"🪦 [HEALER_GAP_KILL] {_side} Mirror {healer_price:.3f} будет убит GC (Bid:{_side_bid:.3f})")

                    self._log_decision('MIRROR_RECOVERY', f"🌀 Зеркало {_side} активно по {healer_price:.3f}")
                    continue

                if gate_locked and (unreal_loss >= toxic_thr or is_stuck_time):
                    if _side == 'YES':
                        p_yes = 0.0
                    else:
                        p_no = 0.0

                    if is_stuck_time and unreal_loss < toxic_thr:
                        # [v2.7 P3] Sync — старт от 30с, разгон 60с до полного TIME_HEAL
                        stuck_progress = min(1.0, (time_since_fill - 30.0) / 60.0)

                        _bid = market_data.get('yes_bid', _fv_side) if _side == 'YES' \
                            else market_data.get('no_bid', 1.0 - _fv_side)
                        _market_floor = max(0.01, _bid - TICK_SIZE)
                        _healer_start = _fv_side - 0.02
                        healer_price = round(
                            _healer_start - (_healer_start - _market_floor) * stuck_progress, 2)
                        healer_price = max(_market_floor, healer_price)
                        recovery_tag += f"⏳[TIME_HEAL_{_side}:{stuck_progress:.1f}]"
                    else:
                        recovery_price     = _avg - disc_cents
                        # [v2.6] Привязка к рынку, не к FV
                        # safe_bid = fv_side - edge давал цену на 15-20ц ниже рынка → GC убивал
                        _market_bid_side   = market_data.get(
                            'yes_bid' if _side == 'YES' else 'no_bid', _fv_side
                        )
                        # [HEALER-AT-BBO 2026-05-13] Healer conversion was 3-5%
                        # because price = bid - tick puts us 1 tick BELOW best
                        # bid (deep queue). Same root cause as the regular
                        # quoting bleed. Move healer onto best_bid (queue top)
                        # so toxic positions actually unwind. The
                        # _avg - TICK_SIZE invariant below preserves "buy lower
                        # than current avg" required for averaging-down.
                        safe_bid           = _market_bid_side  # was: bid - TICK_SIZE
                        # Aggressive escape: position stuck > 60s — allow
                        # crossing 1 tick into the spread (mini-taker). Saves
                        # the 5-15% loss of holding to resolution.
                        _aggressive_window = getattr(
                            self.config, 'healer_aggressive_after_sec', 60.0
                        )
                        if time_since_fill > _aggressive_window:
                            _ask_side = yes_ask if _side == 'YES' else no_ask
                            if _ask_side > 0:
                                safe_bid = min(
                                    _market_bid_side + TICK_SIZE,
                                    _ask_side - TICK_SIZE,
                                )
                                recovery_tag += f"🚨[HEAL_AGGRESSIVE_{_side}]"

                        if is_deadlocked and _side == _weak_side:
                            _ask_side = yes_ask if _side == 'YES' else no_ask
                            _healer_ceiling = min(_ask_side - TICK_SIZE, _probe_safe)
                            healer_price = round(min(recovery_price, _healer_ceiling), 2)
                            self._log_decision('HEALER_DESPERATE_OVERRIDE',
                                f"🕸️ [DEADLOCK_HEAL] {_side} сеть по {healer_price:.3f} "
                                f"(probe_safe:{_probe_safe:.3f} | recovery:{recovery_price:.3f})")
                        else:
                            healer_price = round(min(recovery_price, safe_bid), 2)
                            # [v2.6] Гарантия усреднения вниз и валидности цены
                            healer_price = min(healer_price, _avg - TICK_SIZE)
                            healer_price = max(healer_price, 0.01)

                    if _side == 'YES':
                        l0_y_std    = healer_price
                        # [ПАТЧ] Заменяем min на max. Лекарь диктует свой объем!
                        final_lot_y = max(final_lot_y, avg_tranche)
                    else:
                        l0_n_std    = healer_price
                        # [ПАТЧ] Заменяем min на max.
                        final_lot_n = max(final_lot_n, avg_tranche)

                    recovery_tag += f"🆘[HEAL_{_side}]"

                    # [WIRETAP 2B]
                    _side_bid = market_data.get('yes_bid' if _side == 'YES' else 'no_bid', 0.0)
                    if healer_price > 0 and _side_bid > 0 and (_side_bid - healer_price) > 0.05:
                         logging.getLogger('gabalog.grid_strategy').warning(f"🪦 [HEALER_GAP_KILL] {_side} Toxic {healer_price:.3f} будет убит GC (Bid:{_side_bid:.3f})")

                    if time.time() - getattr(self, '_last_toxic_recovery_log', 0) > 3.0: 
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🚑 [TOXIC_RECOVERY] {_side} активен! "
                            f"Avg:{_avg:.3f} -> Healer:{healer_price:.3f} | Q:{q}"
                        )
                        self._last_toxic_recovery_log = time.time()

            return {
                'p_yes':       p_yes,
                'p_no':        p_no,
                'l0_y_std':    l0_y_std,
                'l0_n_std':    l0_n_std,
                'final_lot_y': final_lot_y,
                'final_lot_n': final_lot_n,
                'recovery_tag': recovery_tag,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[TOXIC_RECOVERY_PROTOCOL] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.4f}, y_avg={y_avg:.4f}, n_avg={n_avg:.4f}, "
                f"is_deadlocked={is_deadlocked}, active_gate_limit={active_gate_limit:.4f}"
            )
            raise

    def _compute_vector_pricing_and_hunter(
        self,
        fv_yes: float,
        edge_y: float,
        edge_n: float,
        p_yes: float,
        p_no: float,
        time_rem_sec: float,
        q: int,
        yes_ask: float,
        yes_bid: float,
        no_ask: float,
        no_bid: float,
        TICK_SIZE: float,
        is_desperate: bool,
        price_rec_y: float,
        price_rec_n: float,
        recovery_tag: str,
        is_toxic_bag: bool,
        effective_scale: float,
        l0_y_std: float,
        l0_n_std: float,
        is_flow_toxic: bool = False,
    ) -> dict:
        try:
            # 8.2 Vector Pricing & CVD Skewing
            # --- [DUAL-CORE: УПРАВЛЯЮЩИЙ КОНТУР СМЕЩЕНИЯ] ---
            cvd_skew_y = 0.0
            cvd_skew_n = 0.0
            
            defense_state = getattr(self, '_defense_state', {})
            skew_intensity_cents = defense_state.get('price_skew_cents', 0.0)
            
            # Контур защиты передает точное значение смещения в центах
            if skew_intensity_cents > 0.0:
                if fv_yes > 0.5:
                    # Оракул за YES, но рынок бьет в NO. Ухудшаем NO, улучшаем YES.
                    cvd_skew_n = -skew_intensity_cents  
                    cvd_skew_y = +(skew_intensity_cents * 0.5) 
                else:
                    # Оракул за NO, но рынок бьет в YES. Ухудшаем YES, улучшаем NO.
                    cvd_skew_y = -skew_intensity_cents
                    cvd_skew_n = +(skew_intensity_cents * 0.5)
            # ---------------------------------------------------

            # Перезаписываем стандартные L0 с учетом CVD смещения
            if not l0_y_std:
                # FV - спред - инвентарное давление(p) + CVD смещение
                l0_y_std = fv_yes - edge_y - p_yes + cvd_skew_y
            if not l0_n_std:
                l0_n_std = (1.0 - fv_yes) - edge_n - p_no + cvd_skew_n

            # В функции _compute_vector_pricing_and_hunter, СРАЗУ после строки 3812:
            if not hasattr(self, '_last_pricing_trace_ts'):
                self._last_pricing_trace_ts = 0
            if time.time() - self._last_pricing_trace_ts > 3.0:
                logger.info(
                    f"🔬 [PRICING_TRACE] FV:{fv_yes:.4f} | "
                    f"edge_y:{edge_y:.4f} edge_n:{edge_n:.4f} | "
                    f"p_y:{p_yes:.4f} p_n:{p_no:.4f} | "
                    f"cvd_y:{cvd_skew_y:.4f} cvd_n:{cvd_skew_n:.4f} | "
                    f"l0_y:{l0_y_std:.4f} l0_n:{l0_n_std:.4f} | "
                    f"bbo_y:{yes_bid:.3f}-{yes_ask:.3f} bbo_n:{no_bid:.3f}-{no_ask:.3f} | "
                    f"q:{q}"
                )
                self._last_pricing_trace_ts = time.time()

            # 8.3 Hunter Logic
            l0_y_hunter, l0_n_hunter = 0.0, 0.0
            hunter_gate = getattr(self.config, 'profit_gate_ps_max', 0.985)

            try:
                _hunter_thr_base = self.config.hunter_imb_threshold
                # [TORPEDO EXCEPTION] При экстремальном CVD + Streak снижаем порог вдвое
                _cvd_torpedo_extreme = (
                    abs(getattr(self, '_cvd_signal_last', 0.0)) > 0.80 and
                    getattr(self, '_cvd_toxic_streak', 0) > 15
                )
                if _cvd_torpedo_extreme:
                    _hunter_thr_base = max(5, _hunter_thr_base // 2)
                imb_threshold    = max(5, _hunter_thr_base)

                # [BLOCK_CTX] Hunter state
                _hunter_sleeping = (abs(q) > 0 and abs(q) < imb_threshold and not is_desperate)
                if _hunter_sleeping:
                    _hunt_reason = f"Q:{q} < thr:{imb_threshold} | Desp:False | T:{time_rem_sec:.0f}s"
                else:
                    _hunt_reason = f"Q:{q} >= thr:{imb_threshold} | Desp:{is_desperate} | T:{time_rem_sec:.0f}s"
                self._log_block_state('HUNTER_SLEEP', _hunter_sleeping, _hunt_reason)

                # Расчет давления для градиента (Linear Pressure)
                hc_limit = getattr(self, '_dynamic_hard_cutoff', 35)
                pressure = min(1.0, abs(q) / max(1, hc_limit))
                
                if time_rem_sec > self.config.endgame_hunter_buffer_sec:
                    max_gate = getattr(self.config, 'hunter_max_gate', 1.03) 
                    survival_start = effective_scale * 1.5
                    survival_max   = effective_scale * 3.0
                    profit_buffer  = max(0.0, self.position.realized_ctf_pnl / 400.0)
                    
                    tick_base = getattr(self, '_tick_hunter_gate', getattr(self.config, 'profit_gate_ps_max', 0.985))
                    current_base = min(tick_base + profit_buffer, 0.995)

                    # 1. ФАКТОР ВРЕМЕНИ (Тот самый Q_Danger)
                    time_since_fill = time.time() - getattr(self, '_last_fill_ts', time.time())
                    # Паника начинается после 45 секунд ожидания и достигает пика через 2 минуты
                    stuck_time_ratio = min(1.0, max(0.0, (time_since_fill - 45.0) / 120.0))

                    if abs(q) <= survival_start and stuck_time_ratio == 0:
                        hunter_gate = current_base
                        combined_panic = 0.0
                    else:
                        panic_range   = max(1.0, survival_max - survival_start)
                        q_panic_ratio = min(1.0, max(0.0, (abs(q) - survival_start) / panic_range))
                        
                        # 2. НЕЛИНЕЙНАЯ СУММА ПАНИКИ (Время бьет экспоненциально)
                        combined_panic = min(1.0, q_panic_ratio + (stuck_time_ratio ** 1.5))
                        
                        market_stress = max(0.0, getattr(self, '_current_stress_multiplier', 1.0) - 1.0)
                        
                        calculated_gate = current_base + (combined_panic * (max_gate - current_base)) + (market_stress * 0.01)
                        hunter_gate = min(max_gate, calculated_gate)

                    if hunter_gate > 1.00:
                        recovery_tag += f"🆘[PANIC_GATE:{hunter_gate:.3f}|T:{stuck_time_ratio:.2f}]"

                    # Триггер агрессии: desperate, паника, или токсичный поток при минимальном Q
                    _min_q_flow = max(5, imb_threshold // 2)
                    is_aggressive_hunter = is_desperate or (combined_panic > 0.5) or \
                                        (is_flow_toxic and abs(q) >= _min_q_flow)

                    # --- [HUNTER_LOCKED_PS_GUARD v3.4.2] ---
                    # Защита замка от агрессивного Hunter'а: если существующий замок уже
                    # за red line (inv_ps >= 1.01 при tick=0.01), Hunter теряет emergency
                    # gate bypass и переходит на стандартный safe_price через _calculate_max_safe_price.
                    # Логика: Hunter с emergency_gate=1.012 на замке 1.01 → дорогой fill
                    # ломает n_avg/y_avg и углубляет замок до 1.05+. Лучше остановить
                    # эскалацию, дать Лекарю работать, дождаться mirror opportunity.
                    # Closing legs не блокируются — Hunter всё равно ставит ордер,
                    # просто по нормальной цене.
                    if is_aggressive_hunter:
                        _existing_locked_ps = (
                            (self.position.yes_cost / max(1, self.position.total_yes)) +
                            (self.position.no_cost / max(1, self.position.total_no))
                        ) if (self.position.total_yes > 0 and self.position.total_no > 0) else 0.0

                        _hunter_locked_guard = getattr(self.config, 'hunter_locked_ps_guard', 1.005)
                        if _existing_locked_ps > _hunter_locked_guard:
                            is_aggressive_hunter = False
                            if time.time() - getattr(self, '_last_hunter_lock_guard_log', 0) > 3.0:
                                logging.getLogger('gabalog.grid_strategy').warning(
                                    f"🛑 [HUNTER_LOCK_GUARD] Aggressive bypass отключён | "
                                    f"ExistingLockPS:{_existing_locked_ps:.3f} > Guard:{_hunter_locked_guard:.3f} | "
                                    f"Q:{q} | Hunter переходит на стандартный safe_price"
                                )
                                self._last_hunter_lock_guard_log = time.time()

                    # А. Охота за YES
                    if q < -imb_threshold:
                        # [HEDGE BYPASS 2] Aggressive hunter bypasses avg_cost cap
                        safe_price_y = hunter_gate if is_aggressive_hunter else self._calculate_max_safe_price('YES', self.config.grid_lot_size, hunter_gate, is_hunter=True)
                        if safe_price_y > 0.01:
                            spread_y = yes_ask - yes_bid
                            if is_aggressive_hunter:
                                # Паника: впиваемся в Аск, сила укуса зависит от общей паники
                                target_price_y = yes_ask - (TICK_SIZE * (1.0 - max(pressure, combined_panic)))
                                target_price_y = max(yes_bid, target_price_y)
                            else:
                                _min_pen = getattr(self.config, 'hunter_min_penetration', 0.25)
                                target_price_y = yes_bid + max(TICK_SIZE, spread_y * max(_min_pen, 0.4 * pressure))

                            if is_aggressive_hunter and target_price_y > safe_price_y:
                                max_panic_price = fv_yes + (max_gate - 1.0)
                                if target_price_y <= max_panic_price:
                                    l0_y_hunter = target_price_y
                                    self._log_decision('HUNTER_TEETH_Y', f"🩸 [TEETH] Сталкер YES! Panic:{combined_panic:.2f} | Tgt:{target_price_y:.3f}")
                                else:
                                    l0_y_hunter = safe_price_y
                                    self._log_decision('HUNTER_SQUASH_Y', f"🦷 [SQUASH] Сталкер YES срезан до {safe_price_y:.3f}")
                            else:
                                l0_y_hunter = min(target_price_y, safe_price_y)

                    # Б. Охота за NO (Абсолютно зеркальная логика)
                    elif q > imb_threshold:
                        # [HEDGE BYPASS 2] Aggressive hunter bypasses avg_cost cap
                        safe_price_n = hunter_gate if is_aggressive_hunter else self._calculate_max_safe_price('NO', self.config.grid_lot_size, hunter_gate, is_hunter=True)
                        if safe_price_n > 0.01:
                            spread_n = no_ask - no_bid
                            if is_aggressive_hunter:
                                target_price_n = no_ask - (TICK_SIZE * (1.0 - max(pressure, combined_panic)))
                                target_price_n = max(no_bid, target_price_n)
                            else:
                                _min_pen = getattr(self.config, 'hunter_min_penetration', 0.25)
                                target_price_n = no_bid + max(TICK_SIZE, spread_n * max(_min_pen, 0.4 * pressure))

                            if is_aggressive_hunter and target_price_n > safe_price_n:
                                max_panic_price = (1.0 - fv_yes) + (max_gate - 1.0)
                                if target_price_n <= max_panic_price:
                                    l0_n_hunter = target_price_n
                                    self._log_decision('HUNTER_TEETH_N', f"🩸 [TEETH] Сталкер NO! Panic:{combined_panic:.2f} | Tgt:{target_price_n:.3f}")
                                else:
                                    l0_n_hunter = safe_price_n
                                    self._log_decision('HUNTER_SQUASH_N', f"🦷 [SQUASH] Сталкер NO срезан до {safe_price_n:.3f}")
                            else:
                                l0_n_hunter = min(target_price_n, safe_price_n)

                            self._log_decision('HUNTER_NO', f"🧠 HUNTER | NO | P:{pressure:.2f} | Gate:{hunter_gate:.3f} | Target:{l0_n_hunter:.3f}")
                            self._last_hunter_side = 'NO'
                else:
                    if self._last_decision in ['HUNTER_Y', 'HUNTER_NO']:
                        self._log_decision('HUNTER_OFF', "🧠 [DECISION] HUNTER | Действие: Отключение Hunter | Причина: Эндшпиль (T-180s)")
                        self._last_decision = 'NORMAL'
                        self._last_hunter_side = None

            except Exception as e:
                logging.getLogger('gabalog.grid_strategy').error(
                    f"❌ [HUNTER_CRASH] Охотник разбился: {str(e)}", exc_info=True)
                self._log_decision('HUNTER_CRASH', f"❌ Ошибка: {str(e)}")

            # [PING-PONG FV GUARD] Блокируем контртрендовую ногу при Q≈0
            # в TORPEDO/RECOVERY при экстремальном FV (abs(FV-0.5) > 0.20)
            # Hunter спит при Q<=3, Healer тоже — единственный источник цены l0_std
            if getattr(self, '_is_pingpong', False):
                if fv_yes > 0.70:    # тренд YES → NO контртрендовый → блокируем
                    l0_n_std = 0.0
                elif fv_yes < 0.30:  # тренд NO → YES контртрендовый → блокируем
                    l0_y_std = 0.0
                if time.time() - getattr(self, '_last_pingpong_log', 0) > 2.0:
                    _blocked = 'NO' if fv_yes > 0.70 else 'YES' if fv_yes < 0.30 else '—'
                    logger.info(f"🏓 [PINGPONG_GUARD] Q:{q} FV:{fv_yes:.3f} Regime:{getattr(self,'_market_regime','?')} → blocked:{_blocked}")
                    self._last_pingpong_log = time.time()

            # 3. Финальный арбитраж
            boost     = getattr(self, '_emergency_hunter_boost', 0.0)
            if is_desperate:
                price_cap = min(0.998, 0.995 + boost)
            elif is_flow_toxic and is_aggressive_hunter:
                price_cap = min(0.998, hunter_gate + boost)
            elif l0_y_hunter > 0 or l0_n_hunter > 0:
                # [П1 v2.5] Hunter активен в BALANCED — gate вместо хардкода 0.95
                # hunter_gate = 0.990 в норме, до 1.012 при панике — корректный потолок
                price_cap = min(0.998, hunter_gate + boost)
            else:
                price_cap = min(0.998, 0.95 + boost)
            l0_y = min(price_cap, max(l0_y_std, price_rec_y, l0_y_hunter))
            l0_n = min(price_cap, max(l0_n_std, price_rec_n, l0_n_hunter))

            # [WIRETAP 1] Аудит победы в ценообразовании
            if time.time() - getattr(self, '_last_arb_log', 0) > 1.0:
                for s, l0_val, std, rec, hunt in [('YES', l0_y, l0_y_std, price_rec_y, l0_y_hunter), 
                                                   ('NO', l0_n, l0_n_std, price_rec_n, l0_n_hunter)]:
                    winner = "STD"
                    if l0_val == rec: winner = "RECOVERY"
                    if l0_val == hunt: winner = "HUNTER"
                    if l0_val >= price_cap: winner = "CAP"
                    
                    if winner != "STD" and l0_val > 0:
                        logging.getLogger('gabalog.grid_strategy').info(f"🪦🏆 [PRICE_WINNER] {s} выиграл {winner} ({l0_val:.3f}). База была: {std:.3f} | {self._std_ctx()}")
                self._last_arb_log = time.time()

            # 4. PS Limit
            if is_desperate:
                ps_limit = min(0.998, 0.995 + boost)
            elif getattr(self, '_unified_stress_level', 0.0) > 0.75: # Замена Defcon
                ps_limit = 0.990
            else:
                raw_gate = getattr(self, '_tick_base_gate',
                            getattr(self.config, 'profit_gate_ps_max', 0.985))

                ps_limit = min(raw_gate, 0.995) if abs(q) > 10 and not is_toxic_bag else raw_gate

            # 5. PS_SQUASH (Асимметричное выдавливание v2)
            current_ps_sum = l0_y + l0_n
            if current_ps_sum > ps_limit:
                now = time.time()
                
                # Определяем, кто сейчас спасает инвентарь
                is_rescue_y = (l0_y_hunter > 0) or (price_rec_y > 0)
                is_rescue_n = (l0_n_hunter > 0) or (price_rec_n > 0)
                
                if is_desperate:
                    # Старая логика глухой обороны
                    if q > 0:
                        l0_y = max(0.0, ps_limit - l0_n)
                    elif q < 0:
                        l0_n = max(0.0, ps_limit - l0_y)
                    if now - getattr(self, '_last_ps_squash_log', 0) > 4.0:
                        logger.warning(f"⚖️ [PS_SQUASH] DESPERATE SQUEEZE | Capped heavy leg at {max(l0_y, l0_n):.3f}")
                        self._last_ps_squash_log = now

                elif is_rescue_y and not is_rescue_n:
                    # Охотник/Лекарь за YES — срезаем только пассивного Мейкера (NO)
                    l0_n = max(0.0, ps_limit - l0_y)
                    if now - getattr(self, '_last_ps_squash_log', 0) > 4.0:
                        logger.warning(f"⚖️ [PS_SQUASH] ASYM_Y | Спасаем YES ({l0_y:.3f}), Мейкер NO выдавлен до {l0_n:.3f}")
                        self._last_ps_squash_log = now

                elif is_rescue_n and not is_rescue_y:
                    # Охотник/Лекарь за NO — срезаем только пассивного Мейкера (YES)
                    l0_y = max(0.0, ps_limit - l0_n)
                    if now - getattr(self, '_last_ps_squash_log', 0) > 4.0:
                        logger.warning(f"⚖️ [PS_SQUASH] ASYM_N | Спасаем NO ({l0_n:.3f}), Мейкер YES выдавлен до {l0_y:.3f}")
                        self._last_ps_squash_log = now

                else:
                    # Обычный рыночный шум (Охотник спит) — мягкое пропорциональное сжатие обеих ног
                    reduction_ratio = ps_limit / current_ps_sum
                    if now - getattr(self, '_last_ps_squash_log', 0) > 4.0:
                        cut_pct = (1 - reduction_ratio) * 100
                        logger.warning(f"⚖️ [PS_SQUASH] SOFT PRESS | {current_ps_sum:.3f} > {ps_limit} | -{cut_pct:.1f}%")
                        self._last_ps_squash_log = now
                    l0_y = l0_y * reduction_ratio
                    l0_n = l0_n * reduction_ratio
                    
                # --- ВОТ СЮДА ВСТАВЛЯЕМ ЖУЧОК №2 (В КОНЕЦ БЛОКА SQUASH) ---
                for s, val, bid in [('YES', l0_y, yes_bid), ('NO', l0_n, no_bid)]:
                    if val > 0 and bid > 0 and (bid - val) > 0.05:
                        _sq_attr = f'_last_sq_death_{s}'
                        if now - getattr(self, _sq_attr, 0) > 1.0:
                            logging.getLogger('gabalog.grid_strategy').warning(
                                f"🪦⚖️💀 [SQUEEZE_DEATH] {s} выдавлен до {val:.3f}. GC убьет этот ордер (Bid:{bid:.3f})"
                            )
                            setattr(self, _sq_attr, now)
                # --------------------------------------------------------

            return {
                'l0_y':        l0_y,
                'l0_n':        l0_n,
                'l0_y_std':    l0_y_std,
                'l0_n_std':    l0_n_std,
                'hunter_gate': hunter_gate,
                'ps_limit':    ps_limit,
                'recovery_tag': recovery_tag,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[VECTOR_PRICING_AND_HUNTER] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.4f}, time_rem_sec={time_rem_sec:.1f}, "
                f"is_desperate={is_desperate}, edge_y={edge_y:.4f}, edge_n={edge_n:.4f}"
            )
            raise

    def _compute_healer(self, q: int, mid_market: float, yes_ask: float, yes_bid: float, TICK_SIZE: float, fv_yes: float = 0.5) -> dict:
        try:
            shadow = self._compute_shadow_accounting(q)
            y_avg = shadow.get('y_avg_price', 0.0)
            n_avg = shadow.get('n_avg_price', 0.0)
            
            # Если q (чистый риск) равен нулю — лечить нечего
            if shadow.get('open_q', 0) == 0:
                inv_ps = 1.00
            else:
                # ВЫЧИСЛЯЕМ NO_ASK: если лучший бид YES это 0.55, 
                # значит кто-то готов продать NO за 1.0 - 0.55 = 0.45
                derived_no_ask = round(1.0 - yes_bid, 3) if yes_bid > 0 else 0.99

                open_q_val = shadow.get('open_q', 0)
                if open_q_val > 0:
                    inv_ps = y_avg + derived_no_ask
                elif open_q_val < 0:
                    inv_ps = n_avg + yes_ask
                else:
                    inv_ps = 1.00

            is_toxic_bag = False
            recovery_tag = ""
            price_rec_y = 0.0
            price_rec_n = 0.0
            is_recovery_active_y = False
            is_recovery_active_n = False

            # Нечего лечить если нет открытой позиции
            if shadow.get('open_q', 0) == 0:
                return {
                    'y_avg': y_avg, 'n_avg': n_avg, 'inv_ps': 1.0,
                    'is_toxic_bag': False, 'recovery_tag': '',
                    'price_rec_y': 0.0, 'price_rec_n': 0.0,
                    'is_recovery_active_y': False, 'is_recovery_active_n': False,
                    'is_flow_toxic': getattr(self, '_is_flow_toxic', False),
                }

            toxic_threshold = getattr(self.config, 'recovery_inv_ps_threshold', 0.99)
            _discount_base = getattr(self.config, 'recovery_discount_cents', 0.050)
            fv_distance    = abs(fv_yes - 0.5) * 2.0
            healer_mult    = 1.0 + fv_distance * 2.0
            # [v2.6] Hard cap 0.030: стресс+FAR давал до 10c — нереалистично для 15м рынка
            discount_cents = min(_discount_base * healer_mult, 0.030)

            _intent = getattr(self, '_intent_mode', 'BALANCED')
            _il     = getattr(self, '_intent_load', 0.0)
            if _intent == 'RESTORE_BALANCE':
                toxic_threshold = max(0.95, toxic_threshold - (_il * 0.04))
                # [v2.6] floor 0.30→0.35: минимум 1 тик (0.01) дисконта при любом InvL
                # При InvL=1.0: 3.0c × 0.35 = 1.05c → 1 тик ✓. floor<0.33 → discount<1 тика → 0
                discount_cents  = discount_cents * max(0.35, 1.0 - _il)

            # 6.2 Knife Protection — читаем из _compute_intent_mode
            is_falling_knife = getattr(self, '_is_falling_knife', False)
            is_flow_toxic    = getattr(self, '_is_flow_toxic', False)
            is_bunker        = getattr(self, '_is_panic_frozen', False)

            # Телеметрия ошейника (для парсера — сохраняем лог)
            cvd_signal = getattr(self, '_cvd_signal_last', 0.0)
            self._log_block_state(
                'HEALER_CVD', is_flow_toxic,
                f"IntentMode:{getattr(self,'_intent_mode','?')} | CVD:{cvd_signal:+.3f} | Q:{q}"
            )

            # Замени блок расчета условий на этот:
            mirror_opportunity = False
            # Используем ту же переменную, что и для триггера, чтобы не было "зазора"
            trigger_gap = 0.02 # Начинаем усреднять уже при разнице в 2 цента

            if q > 0 and mid_market < (y_avg - trigger_gap) and q >= 3:
                mirror_opportunity = True
            if q < 0 and (1.0 - mid_market) < (n_avg - trigger_gap) and q <= -3:
                mirror_opportunity = True

            # [v2.7 P6] Sync с порогом активации (TICK_SIZE).
            # Раньше зазор 0 < diff < TICK создавал ложный CAUSE_A
            # (Лекарь срабатывал как переоценённая нога, но активация падала PRICE_NOT_CHEAP_ENOUGH)
            if open_q_val > 0:
                _our_leg_overpriced = (y_avg - mid_market) > TICK_SIZE
            elif open_q_val < 0:
                _our_leg_overpriced = (n_avg - (1.0 - mid_market)) > TICK_SIZE
            else:
                _our_leg_overpriced = False

            # [v2.10 P8] CLOSING LEG CHECK — асимметрия пары
            # Состояние А (правильное): моя YES стала дорогой, рынок откатил → NO_bid вырос → усреднение полезно
            # Состояние B (катастрофа): моя YES стала дорогой потому что рынок ушёл в DIR → NO_bid тоже упал → усреднение топит позицию
            # Различие: смотрим что closing leg тоже доступна (её bid не упал ниже её n_avg)
            # Если closing leg недоступна (рынок против всей пары) → НЕ усредняем, ждём
            _closing_leg_available = True
            if open_q_val > 0:
                # У нас YES, closing = NO. NO_bid выводим из yes_ask: no_bid = 1 - yes_ask
                derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01
                # Если n_avg существует (мы покупали NO раньше), сравниваем с её средней
                # Если n_avg = 0 (никогда не покупали NO), используем mid как baseline
                _no_baseline = n_avg if n_avg > 0 else (1.0 - mid_market)
                # Closing доступна если её bid не упал больше чем на TICK от baseline
                _closing_leg_available = derived_no_bid >= (_no_baseline - TICK_SIZE)
            elif open_q_val < 0:
                # У нас NO, closing = YES. YES_bid доступен напрямую
                _y_baseline = y_avg if y_avg > 0 else mid_market
                _closing_leg_available = yes_bid >= (_y_baseline - TICK_SIZE)

            _inv_ps_trigger = (inv_ps > toxic_threshold) and _our_leg_overpriced and _closing_leg_available

            if (_inv_ps_trigger or mirror_opportunity) and not is_bunker and not is_flow_toxic:
                is_toxic_bag = True

                if q > 0 and mid_market < (y_avg - TICK_SIZE):
                    _hl_cap = getattr(self.config, 'healer_max_overpay', 0.030)
                    # [v2.7 P1] Привязка к bid (политика: потолок = best_bid)
                    # mid + 0.001 ставило в спред — биржа отклоняла или мы переплачивали
                    price_rec_y = max(0.01, min(yes_bid - TICK_SIZE, y_avg - TICK_SIZE, fv_yes + _hl_cap))
                    is_recovery_active_y = True
                    recovery_tag = "🩺[AVG_Y]"
                    if self._last_decision != 'RECOVERY_Y':
                        self._log_decision('RECOVERY_Y', f"🧠 [DECISION] RECOVERY | YES Avg: ${y_avg:.3f} | Market: ${mid_market:.3f}")
                        self._last_decision = 'RECOVERY_Y'
                elif q < 0 and ((1.0 - mid_market) < (n_avg - TICK_SIZE)):
                    derived_no_bid = round(1.0 - yes_ask, 3) if yes_ask > 0 else 0.01
                    _hl_cap = getattr(self.config, 'healer_max_overpay', 0.030)
                    # [v2.7 P1] Привязка к bid (no_bid = 1 - yes_ask)
                    price_rec_n = max(0.01, min(derived_no_bid - TICK_SIZE, n_avg - TICK_SIZE, (1.0 - fv_yes) + _hl_cap))
                    is_recovery_active_n = True
                    recovery_tag = "🩺[AVG_N]"
                    if self._last_decision != 'RECOVERY_N':
                        self._log_decision('RECOVERY_N', f"🧠 [DECISION] RECOVERY | NO Avg: ${n_avg:.3f} | Market: ${1-mid_market:.3f}")
                        self._last_decision = 'RECOVERY_N'
                else:
                    if getattr(self, '_last_decision', '') in ['RECOVERY_Y', 'RECOVERY_N']:
                        self._log_decision('RECOVERY_PAUSE', f"🧠 [DECISION] Пауза усреднения | Цена невыгодна, PS:{inv_ps:.3f}")
                        self._last_decision = 'RECOVERY_PAUSE'
            else:
                if getattr(self, '_last_decision', '') in ['RECOVERY_Y', 'RECOVERY_N', 'RECOVERY_PAUSE'] and not is_bunker:
                    reason_str = "Падающий нож" if is_falling_knife else "Инвентарь вылечен"
                    self._log_decision('NORMAL', f"🧠 [DECISION] RECOVERY | Возврат к штрафам Q | Причина: {reason_str}")
                    self._last_decision = 'NORMAL'

            # [WIRETAP] Аудит блокировок Лекаря
            now = time.time()
            if (inv_ps > toxic_threshold or mirror_opportunity) and not is_recovery_active_y and not is_recovery_active_n:
                if now - getattr(self, '_last_healer_fail_log', 0) > 1.0:
                    fail_reason = ""
                    if is_falling_knife: fail_reason = "FALLING_KNIFE"
                    elif is_bunker: fail_reason = "BUNKER_ACTIVE"
                    elif is_flow_toxic: fail_reason = f"FLOW_TOXIC({cvd_signal:+.2f})"
                    elif not _our_leg_overpriced:
                        fail_reason = "CAUSE_B_HUNTER_ZONE"  # наша нога не переоценена — Hunter
                    else:
                        fail_reason = "PRICE_NOT_CHEAP_ENOUGH"
                    
                    if fail_reason:
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦🩺 [HEALER_FAIL] Лекарь вызван, но заблокирован. Причина: {fail_reason} | PS:{inv_ps:.3f} | {self._std_ctx()}"
                        )
                        self._last_healer_fail_log = now

            return {
                'y_avg':               y_avg,
                'n_avg':               n_avg,
                'inv_ps':              inv_ps,
                'is_toxic_bag':        is_toxic_bag,
                'recovery_tag':        recovery_tag,
                'price_rec_y':         price_rec_y,
                'price_rec_n':         price_rec_n,
                'is_recovery_active_y': is_recovery_active_y,
                'is_recovery_active_n': is_recovery_active_n,
                'is_flow_toxic':       is_flow_toxic,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_HEALER] CRITICAL ERROR: {e} | "
                f"q={q}, mid_market={mid_market:.4f}, "
                f"yes_shares={self.position.yes_shares}, no_shares={self.position.no_shares}, "
                f"inv_ps={inv_ps if 'inv_ps' in dir() else 'N/A'}"
            )
            raise

    def _compute_pair_state(self, q: int) -> dict:
        """
        [v2.10 PAIR_STATE] FSM async-aware pricing.
        
        Состояния:
            BALANCED — Q=0 ИЛИ time_since_fill > 15s ИЛИ |Q|<=5 (нормальный мейкер режим)
            FRESH    — time_since_fill < 15s AND Q≠0 AND last_fill_increased_q (только что filled opening leg)
            STUCK    — time_since_fill > 15s AND |Q| > 5 (зона Лекаря и Hunter)
        
        Сохраняет:
            self._pair_state    — текущее состояние ('BALANCED'/'FRESH'/'STUCK')
            self._closing_side  — какая нога должна закрывать перекос ('YES'/'NO'/None)
        """
        try:
            time_since_fill = time.time() - getattr(self, '_last_fill_ts', time.time())
            last_increased  = getattr(self, '_last_fill_increased_q', False)
            
            if q == 0:
                state = 'BALANCED'
                closing_side = None
            elif time_since_fill < 15.0 and last_increased and q != 0:
                state = 'FRESH'
                closing_side = 'NO' if q > 0 else 'YES'
            elif time_since_fill >= 15.0 and abs(q) > 5:
                state = 'STUCK'
                closing_side = 'NO' if q > 0 else 'YES'
            else:
                # |Q|<=5 в первые 15s после неincreasing fill, или после closing fill
                state = 'BALANCED'
                closing_side = None
            
            self._pair_state   = state
            self._closing_side = closing_side
            
            # Логирование переходов FSM
            _prev = getattr(self, '_pair_state_logged', None)
            if state != _prev:
                logger.info(
                    f"⚖️ [PAIR_STATE] {_prev}→{state} | "
                    f"FillAge:{time_since_fill:.1f}s | "
                    f"LastFillSide:{getattr(self,'_last_fill_side','?')} | "
                    f"LastIncQ:{last_increased} | Closing:{closing_side} | "
                    f"{self._std_ctx()}"
                )
                self._pair_state_logged = state
            
            return {'pair_state': state, 'closing_side': closing_side}
        
        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"🪦❌ [PAIR_STATE_CRASH] {str(e)}", exc_info=True
            )
            self._pair_state   = 'BALANCED'
            self._closing_side = None
            return {'pair_state': 'BALANCED', 'closing_side': None}

    def _armor_edge_contribution(self, stress: float, t_rem: float, total_dur: float) -> float:
        """Защита входа — экспоненциальная по стрессу, усиливается в эндшпиле."""
        armor_base = stress ** 2
        t_factor = 1.0 + max(0.0, (1.0 - t_rem / max(1.0, total_dur)) * 2.0)
        return min(0.04, armor_base * t_factor * 0.04)

    def _gravity_edge_contribution(self, open_q: int, cap: int, stress: float) -> float:
        """Давление закрытия — сигмоида, только на закрывающую сторону."""
        q_ratio = abs(open_q) / max(1, cap)
        k = 10.0
        sigmoid = 1.0 / (1.0 + math.exp(-k * (q_ratio - 0.5)))
        stress_boost = 1.0 + stress * 1.5
        return min(0.03, sigmoid * stress_boost * 0.03)

    def _toxicity_multiplier(self, btc_vel: float, vel_threshold: float, open_q: int, cap: int) -> float:
        """Экспоненциальный множитель брони при экстремальной токсичности."""
        q_ratio = abs(open_q) / max(1, cap)
        vel_ratio = btc_vel / max(0.1, vel_threshold)
        if vel_ratio > 1.0 and q_ratio > 0.5:
            toxicity = math.exp((vel_ratio - 1.0) * q_ratio) - 1.0
            return min(3.0, 1.0 + toxicity)
        return 1.0

    def _compute_final_edge(
        self,
        base_edge: float,
        stress: float,
        btc_vel: float,
        vel_threshold: float,
        open_q: int,
        cap: int,
        t_rem: float,
        total_dur: float,
        side_is_closing: bool,
        edge_min: float = 0.003,
    ) -> float:
        """
        Финальный edge — асимметричная сборка Armor + Gravity.
        Закрывающая сторона: броня гасится при росте Q, Gravity давит вниз.
        Открывающая сторона: броня усиливается токсичностью.
        """
        armor = self._armor_edge_contribution(stress, t_rem, total_dur)

        if side_is_closing:
            # Броня гасится пропорционально Q — при Q=cap броня=0
            armor_dampener = max(0.0, 1.0 - (abs(open_q) / max(1, cap)))
            gravity = self._gravity_edge_contribution(open_q, cap, stress)
            final_edge = base_edge + (armor * armor_dampener) - gravity
        else:
            # Броня усиливается токсичностью на открывающей стороне
            tox_mult = self._toxicity_multiplier(btc_vel, vel_threshold, open_q, cap)
            final_edge = base_edge + (armor * tox_mult)

        return max(edge_min, final_edge)

    def _compute_auto_armor(
        self, market_data: dict, oracle_fv: float, mid_market: float,
        yes_ask: float, yes_bid: float, no_ask: float, no_bid: float,
        time_passed: float, t_f: float, open_q: int,
    ) -> dict:
        try:
            # 1. Читаем настройки из конфига (с фолбэками)
            w_oracle = getattr(self.config, 'stress_oracle_weight', 0.70)
            w_btc    = getattr(self.config, 'stress_btc_vel_weight', 0.30)
            gap_thr  = getattr(self.config, 'stress_oracle_gap_thr', 0.30)
            vel_thr  = getattr(self.config, 'btc_vel_stress_threshold', 60.0)

            # 2. ЕДИНЫЙ АРБИТР СТРЕССА (Unified Stress Arbiter)
            # Считаем компоненты
            _oracle_diff = abs(oracle_fv - mid_market)
            oracle_stress = min(1.0, _oracle_diff / gap_thr)

            btc_vel = getattr(self, '_last_btc_velocity', 0.0)
            btc_vel_stress = min(1.0, btc_vel / max(0.1, vel_thr))

            # Итоговый расчет на основе весов из конфига
            self._unified_stress_level = (oracle_stress * w_oracle) + (btc_vel_stress * w_btc)
            
            # 3. Asymmetric EMA (Сглаживание)
            # Используем коэффициент 0.40 для роста и 0.08 для затухания
            prev_smooth = getattr(self, '_smooth_stress', 0.0)
            alpha = 0.40 if self._unified_stress_level > prev_smooth else 0.08
            smooth_stress = (alpha * self._unified_stress_level) + ((1.0 - alpha) * prev_smooth)
            self._smooth_stress = smooth_stress

           # 4. Непрерывный штраф стресса (Таймер со старта рынка)
            if time_passed < 45.0:
                p_stress_mult = 0.5
            elif time_passed < 120.0:
                fade_factor = (time_passed - 45.0) / 75.0
                p_stress_mult = 0.5 + (1.0 - 0.5) * fade_factor
            else:
                p_stress_mult = 1.0

            # 5. Lerp параметров
            dyn_oracle_min_weight = 0.20 - (0.15 * smooth_stress)

            raw_scale = getattr(self.config, 'inventory_scale_shares', 14.0)
            cfg_scale = float(raw_scale)
            dyn_inv_scale_raw = cfg_scale - ((cfg_scale * 0.6) * smooth_stress)

            # 6. Физика дедбенда
            cap = getattr(self.config, 'open_q_sensitivity_cap', 60)
            _fv_now = getattr(self, 'current_fv', 0.5)
            _fv_fear = max(0.25, 1.0 - (abs(_fv_now - 0.5) * 2.0) ** 2)
            inv_load = min(1.0, abs(open_q) / max(1, cap))

            cfg_deadband = getattr(self.config, 'base_deadband', 3.0)
            deadband_market_base = (cfg_deadband * t_f) * (1.0 - smooth_stress)
            dyn_base_deadband = deadband_market_base * (1.0 - (inv_load ** 2)) * _fv_fear
            if inv_load > 0.80:
                dyn_base_deadband = 0.0
            if abs(_fv_now - 0.5) > 0.25:
                _now_ts = time.time()
                if _now_ts - getattr(self, '_last_fv_fear_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🎯 [FV_FEAR] InvLoad:{inv_load:.2f} | Deadband*Fear | FV:{_fv_now:.3f} | Fear:{_fv_fear:.2f}"
                    )
                    self._last_fv_fear_log = _now_ts

            cfg_deadband = getattr(self.config, 'base_deadband', 3.0)
            deadband_market_base = (cfg_deadband * t_f) * (1.0 - smooth_stress)
            dyn_base_deadband = deadband_market_base * (1.0 - (inv_load ** 2))
            if inv_load > 0.80:
                dyn_base_deadband = 0.0

            # 7. Q-Guard
            prev_scale = getattr(self, '_prev_dyn_scale', dyn_inv_scale_raw)
            dyn_inv_scale = max(dyn_inv_scale_raw, prev_scale * 0.85)
            floor_scale = getattr(self.config, 'grid_lot_size', 5.0)
            dyn_inv_scale = max(float(floor_scale), dyn_inv_scale)
            self._prev_dyn_scale = dyn_inv_scale

            # 8. Телеметрия (Очищена от VPIN)
            now = time.time()
            if time.time() - getattr(self, '_last_armor_log', 0) > 2: # <--- 0.1s
                logger.info(
                    f"🛡️ [AUTO-ARMOR] Stress:{self._unified_stress_level:.2f} (W_Or:{w_oracle} W_Btc:{w_btc}) | "
                    f"Gap_S:{oracle_stress:.2f} BTC_V_S:{btc_vel_stress:.2f} "
                    f"Sc:{dyn_inv_scale:.1f} InvL:{inv_load:.2f}"
                )
                self._last_armor_log = time.time()

            self._current_stress_multiplier = 1.0 + smooth_stress

            if dyn_base_deadband == 0.0 and abs(open_q) > 5:
                _now = time.time()
                if _now - getattr(self, '_last_shock_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦🛡️🆘 [ARMOR_SHOCK] Защитная зона обнулена! Q:{open_q} | "
                        f"Stress: {smooth_stress:.2f} | InvLoad: {inv_load:.2f} | "
                        f"Scale: {dyn_inv_scale:.1f}"
                    )
                    self._last_shock_log = _now

            return {
                'smooth_stress': smooth_stress,
                'p_stress_mult':        p_stress_mult,
                'dyn_oracle_min_weight': dyn_oracle_min_weight,
                'dyn_base_deadband':    dyn_base_deadband,
                'dyn_inv_scale':        dyn_inv_scale,
                'inv_load':             inv_load,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_AUTO_ARMOR] CRITICAL ERROR: {e} | "
                f"oracle_fv={oracle_fv:.4f}, mid_market={mid_market:.4f}, "
                f"time_passed={time_passed:.1f}, t_f={t_f:.3f}, "
            )
            raise

    def _compute_intent_mode(
        self,
        inv_load: float,
        smooth_stress: float,
        mid_market: float,
    ) -> dict:
        try:
            _regime   = getattr(self, '_market_regime', 'NEUTRAL')
            _cvd      = getattr(self, '_cvd_signal_last', 0.0)
            _btc_vel  = getattr(self, '_last_btc_velocity', 0.0)
            _vel_thr  = getattr(self.config, 'btc_vel_stress_threshold', 40.0)
            _momentum = getattr(self, '_defense_state', {}).get('momentum', 0.0)
            q         = getattr(self, '_last_open_q', 0)

            # Цены из позиции (аналогично shadow_accounting)
            y_avg = self.position.yes_cost / max(1, self.position.total_yes) \
                    if self.position.total_yes > 0 else 0.0
            n_avg = self.position.no_cost / max(1, self.position.total_no) \
                    if self.position.total_no > 0 else 0.0

            # --- Сигнал 1: Flow Toxicity ---
            _hunter_thr     = getattr(self, '_dynamic_hunter_thr', 15)
            _q_ratio        = min(1.0, abs(q) / max(1, _hunter_thr))
            _cvd_strong_thr = 0.50 + (_q_ratio * 0.40)
            _cvd_medium_thr = 0.30 + (_q_ratio * 0.20)
            _torpedo_signal = (_regime in ('TORPEDO', 'RECOVERY')) or \
                    (_momentum < -0.15) or (_btc_vel > _vel_thr * 0.6)

            _momentum_thr = getattr(self.config, 'regime_torpedo_momentum_thr', 0.20)
            _momentum_confirmed = abs(_momentum) > _momentum_thr and _btc_vel > _vel_thr * 0.6

            is_flow_toxic = (
                (q > 0 and _cvd < -_cvd_strong_thr and _momentum_confirmed) or
                (q < 0 and _cvd > _cvd_strong_thr and _momentum_confirmed) or
                (q > 0 and _cvd > _cvd_medium_thr and _torpedo_signal and _momentum_confirmed) or
                (q < 0 and _cvd < -_cvd_medium_thr and _torpedo_signal and _momentum_confirmed)
            )

            # --- Сигнал 2: Falling Knife с FSM guard ---
            _knife_active = (_regime in ('TORPEDO', 'DIR')) or \
                            (_btc_vel > _vel_thr * 0.5)
            is_falling_knife = False
            if _knife_active:
                knife_cents = getattr(self.config, 'knife_protection_cents', 0.25)
                if q > 0 and (y_avg - mid_market) > knife_cents:
                    is_falling_knife = True
                if q < 0 and (n_avg - (1.0 - mid_market)) > knife_cents:
                    is_falling_knife = True

            # --- Сигнал 3: Ping-Pong FV Guard ---
            # Блокирует контртрендовую ногу при входе из пустой позиции
            # в TORPEDO/RECOVERY при экстремальном FV
            _fv_now  = getattr(self, 'current_fv', 0.5)
            _fv_dist = abs(_fv_now - 0.5)
            is_pingpong = (
                abs(q) <= 3
                and _regime in ('TORPEDO', 'RECOVERY')
                and _fv_dist > 0.20
            )

            # --- Режим ---
            _dir_mode = getattr(self.config, 'dir_regime_mode', 'OPTIMIZE_PRICE')
            if inv_load < 0.30 and _regime == 'NEUTRAL' and not is_flow_toxic:
                mode = 'OPTIMIZE_PRICE'
            elif inv_load < 0.30 and _regime == 'DIR' and not is_flow_toxic:
                mode = _dir_mode  # OPTIMIZE_PRICE / BALANCED / RESTORE_BALANCE
            elif inv_load > 0.70 or is_flow_toxic or \
                 (is_falling_knife and _regime in ('TORPEDO', 'DIR')):
                mode = 'RESTORE_BALANCE'
            else:
                mode = 'BALANCED'

            # --- Единая точка правды ---
            self._intent_mode      = mode
            self._intent_load      = inv_load
            self._is_flow_toxic    = is_flow_toxic
            self._is_falling_knife = is_falling_knife
            self._is_pingpong      = is_pingpong

            _prev_mode = getattr(self, '_intent_mode_logged', None)
            if mode != _prev_mode:
                _ticks_in_prev = getattr(self, '_intent_mode_ticks', 0)
                logger.info(f"🧭 [INTENT_MODE] New:{mode} | Prev:{_prev_mode}({_ticks_in_prev}t) | "
                    f"InvL:{inv_load:.2f} | FlowTox:{is_flow_toxic} | "
                    f"Knife:{is_falling_knife} | PingPong:{is_pingpong} | Regime:{_regime}")
                self._intent_mode_logged = mode
                self._intent_mode_ticks = 0
            else:
                self._intent_mode_ticks = getattr(self, '_intent_mode_ticks', 0) + 1
            return {'intent_mode': mode, 'intent_load': inv_load}

        except Exception:
            self._intent_mode      = 'BALANCED'
            self._intent_load      = inv_load
            self._is_flow_toxic    = False
            self._is_falling_knife = False
            self._is_pingpong      = False
            raise

    def _compute_spread_and_shield(
        self,
        time_rem_sec: float,
        market_data: dict,
        yes_ask: float,
        yes_bid: float,
        q: int,
        eff_delta: float,
        fv_yes: float,
        t_f: float,
        hc_limit: float,
    ) -> dict:
        try:
            # 5.1 Базовые настройки
            base_lot = getattr(self.config, 'grid_lot_size', 5)

            # Параболический Fade
            fade_start = max(1.0, self.config.endgame_fade_start_sec)
            t_factor = (min(1.0, time_rem_sec / fade_start) ** 2) if time_rem_sec <= fade_start else 1.0

            # Vega-Aware Scale
            vol_ratio      = market_data.get('vol_ratio', 1.0)
            safe_vol_ratio = min(self.config.max_vol_ratio, vol_ratio)
            min_stable_scale = max(20.0, hc_limit * 0.5)
            effective_scale  = min_stable_scale * (1.0 / safe_vol_ratio)

            # 5.3 Адаптивный спред
            current_mkt_spread = yes_ask - yes_bid if (yes_ask > 0 and yes_bid > 0) else 0.5
            spread_penalty = max(0, (current_mkt_spread - 0.05) / 2.0)
            gamma_mult = 1.0 + (self.config.gamma_aggression / max(120.0, time_rem_sec))

            v_pen_y = 0.0
            v_pen_n = 0.0
            m_bias_y = max(0.0, -eff_delta * 0.5)
            m_bias_n = max(0.0,  eff_delta * 0.5)

            base_edge  = getattr(self.config, 'target_edge', getattr(self.config, 'edge_min', 0.015))
            asym_power = base_edge
            edge_y_base = base_edge + ((1.0 - fv_yes) * asym_power)
            edge_n_base = base_edge + (fv_yes * asym_power)

            stress_y = (spread_penalty + m_bias_y) * gamma_mult * safe_vol_ratio
            stress_n = (spread_penalty + m_bias_n) * gamma_mult * safe_vol_ratio

            # Иммунитет спасающей ноги
            hedge_thr = getattr(self, '_dynamic_hunter_thr', 15)
            if q < -hedge_thr:
                stress_y = 0.0
            elif q > hedge_thr:
                stress_n = 0.0

            # [v2.10 PAIR_STATE Рычаг 3] Расширенный immunity для closing leg в FRESH
            # При |Q|<hedge_thr но FRESH — closing leg всё равно получает иммунитет
            # (мы ХОТИМ filling closing ноги, edge не должен отпугивать)
            _pair_state   = getattr(self, '_pair_state', 'BALANCED')
            _closing_side = getattr(self, '_closing_side', None)
            if _pair_state == 'FRESH':
                if _closing_side == 'YES':
                    stress_y = 0.0
                elif _closing_side == 'NO':
                    stress_n = 0.0

            edge_y_base_final = edge_y_base + stress_y
            edge_n_base_final = edge_n_base + stress_n

            # [AUTO-ARMOR v2] Асимметричная сборка через _compute_final_edge
            stress      = getattr(self, '_smooth_stress', 0.0)
            btc_vel     = getattr(self, '_last_btc_velocity', 0.0)
            vel_thr     = getattr(self.config, 'btc_vel_stress_threshold', 40.0)
            open_q      = getattr(self, '_last_open_q', q)
            cap         = getattr(self.config, 'open_q_sensitivity_cap', 60)
            total_dur   = float(self.config.market_duration_sec)
            edge_min_v  = getattr(self.config, 'edge_min', 0.003)

            # YES closing = уменьшает перекос если q > 0
            yes_is_closing = q > hedge_thr
            no_is_closing  = q < -hedge_thr

            edge_y = self._compute_final_edge(
                base_edge=edge_y_base_final,
                stress=stress,
                btc_vel=btc_vel,
                vel_threshold=vel_thr,
                open_q=open_q,
                cap=cap,
                t_rem=time_rem_sec,
                total_dur=total_dur,
                side_is_closing=yes_is_closing,
                edge_min=edge_min_v,
            )
            edge_n = self._compute_final_edge(
                base_edge=edge_n_base_final,
                stress=stress,
                btc_vel=btc_vel,
                vel_threshold=vel_thr,
                open_q=open_q,
                cap=cap,
                t_rem=time_rem_sec,
                total_dur=total_dur,
                side_is_closing=no_is_closing,
                edge_min=edge_min_v,
            )

            # Momentum Crossfire — теперь только по btc_velocity
            current_btc_delta = abs(market_data.get('btc_delta', 0.0))
            if current_btc_delta >= 0.020 or btc_vel > 15.0:
                if not yes_is_closing: edge_y *= 1.5
                if not no_is_closing:  edge_n *= 1.5
                if time.time() - getattr(self, '_last_momentum_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🌊 [CROSSFIRE] BTC_V:{btc_vel:.1f}$/s | Спред x1.5 (кроме хеджа)"
                    )
                    self._last_momentum_log = time.time()

            # Финальный зажим
            dist_base        = getattr(self.config, 'garbage_dist_base', 0.08)
            max_allowed_spread = dist_base * 0.85
            max_adaptive     = getattr(self.config, 'max_adaptive_edge', 0.12)
            edge_y = min(edge_y, max_allowed_spread, max_adaptive)
            edge_n = min(edge_n, max_allowed_spread, max_adaptive)
            adaptive_edge = max(edge_y, edge_n)

            if gamma_mult > 1.5 or safe_vol_ratio > 2.5:
                if time.time() - getattr(self, '_last_vega_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').debug(
                        f"🌪️ [VEGA_SPREAD] Edge_Y: {edge_y:.3f} | Edge_N: {edge_n:.3f} | GammaX: {gamma_mult:.2f}"
                    )
                    self._last_vega_log = time.time()

            self.last_effective_scale = effective_scale
            self.last_adaptive_edge   = adaptive_edge

            # 5.0 Динамический демпфер (Shield)
            hard_cap     = getattr(self.config, 'inventory_hard_cap', 200)
            depo_limit   = self.config.deposit
            share_util   = abs(q) / hard_cap if hard_cap > 0 else 0
            usd_util     = self.position.active_total_cost / depo_limit if depo_limit > 0 else 0
            critical_util = max(share_util, usd_util)

            heavy_leg  = 'YES' if q > 0 else 'NO' if q < 0 else None
            base_thr   = getattr(self.config, 'shield_threshold', 0.75)
            dynamic_thr = max(0.35, (base_thr - 0.20) * (0.4 + 0.6 * t_f))
            self._live_shield_thr = dynamic_thr
            self._risk_dampener   = 1.0
            self._hedge_boost     = 1.0

            if critical_util > dynamic_thr:
                pressure = max(0.0, min(1.0, (critical_util - dynamic_thr) / max(0.001, (1.0 - dynamic_thr))))
                self._risk_dampener = 1.0 - (pressure * getattr(self.config, 'shield_scale_cutoff', 0.60))
                self._hedge_boost   = 1.0 + (pressure * 1.5)
                self._log_decision('SHIELD_ASYM', f"🛡️ [SHIELD] Active! Util:{critical_util:.2f} | Risk:{self._risk_dampener:.2f} | Hedge:{self._hedge_boost:.2f}")

                now_ts = time.time()
                if now_ts - getattr(self, '_last_shield_wiretap', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦🛡️🔗 [SHIELD_ENGAGE] Защита активна! Util: {critical_util:.2f} > Thr: {dynamic_thr:.2f} | "
                        f"Dampener (Risk): {self._risk_dampener:.2f} | Boost (Hedge): {self._hedge_boost:.2f} | {self._std_ctx()}"
                    )
                    self._last_shield_wiretap = now_ts

            return {
                'base_lot':       base_lot,
                't_factor':       t_factor,
                'effective_scale': effective_scale,
                'adaptive_edge':  adaptive_edge,
                'edge_y':         edge_y,
                'edge_n':         edge_n,
                'heavy_leg':      heavy_leg,
                'critical_util':  critical_util,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_SPREAD_AND_SHIELD] CRITICAL ERROR: {e} | "
                f"time_rem_sec={time_rem_sec:.1f}, q={q}, fv_yes={fv_yes:.4f}, "
                f"hc_limit={hc_limit:.1f}, t_f={t_f:.3f}, eff_delta={eff_delta:.4f}"
            )
            raise

    def _run_oracle_pipeline(
        self,
        tick_start_time: float,
        eff_delta: float,
        oracle_fv: float,
        mid_market: float,
        time_rem_sec: float,
        strike: float,
        current_btc: float,
        current_vol_ratio: float,
        q: int,
        time_passed: float,
    ) -> dict:
        try:
            now = tick_start_time
            vol_ratio = current_vol_ratio

            # 7.0 Подготовка сигналов
            btc_is_moving  = abs(eff_delta) >= self.config.oracle_drift_threshold
            price_breakout = abs(eff_delta) >= self.config.oracle_panic_threshold
            recovery_rate  = getattr(self.config, 'oracle_recovery_rate', 0.05)

            # 7.1 Adaptive Trust Engine
            base_thr   = getattr(self.config, 'oracle_blindness_thr', getattr(self.config, 'blindness_floor', 0.095))
            oracle_diff = abs(oracle_fv - mid_market)

            time_ratio  = max(0.0, time_rem_sec / self.config.market_duration_sec)
            time_bonus  = 0.10 * time_ratio

            raw_gap        = (mid_market - oracle_fv)
            confirmed_trend = (eff_delta > 0 and raw_gap > 0) or (eff_delta < 0 and raw_gap < 0)
            trend_mult     = 2.0 if confirmed_trend else 1.0
            # Порог слепоты теперь зависит только от времени и тренда
            smart_blind_thr = (base_thr + time_bonus) * trend_mult

            if confirmed_trend and abs(raw_gap) > base_thr:
                self._log_decision('MOMENTUM_LOCK', f"🌊 [MOMENTUM] Trend confirmed (ΔBTC:{eff_delta:.4f}). VETO expanded to {smart_blind_thr:.3f}")

            diagnosis     = "NORMAL"
            target_weight = 1.0

            if not getattr(self, '_is_official_strike', False):
                diagnosis     = "AWAITING_STRIKE"
                target_weight = 0.0
            elif oracle_diff > smart_blind_thr:
                if price_breakout:
                    diagnosis     = "MOMENTUM_GAP"
                    target_weight = 0.40
                elif not btc_is_moving:
                    diagnosis     = "STRIKE_DRIFT"
                    target_weight = max(0.40, getattr(self.config, 'oracle_min_weight', 0.20))
                else:
                    diagnosis     = "VETO_ZONE"
                    target_weight = getattr(self.config, 'oracle_min_weight', 0.20)
            else:
                diagnosis     = "NORMAL"
                target_weight = 1.0

            # 7.2 Эндшпиль
            if time_rem_sec < 120:
                target_weight *= (time_rem_sec / 120.0)
                if diagnosis == "NORMAL":
                    diagnosis = "ENDGAME_CONVERGENCE"

            # 7.3 Плавная гильотина
            curr_weight = getattr(self, '_current_oracle_weight', 1.0)
            
            # Читаем старое состояние ДО того, как начнем его менять
            was_official    = getattr(self, '_last_strike_official_state', False)
            is_now_official = getattr(self, '_is_official_strike', False)

            if (not was_official) and is_now_official and strike > 1000:
                base_vol_allowance = 150.0
                dynamic_threshold  = max(200.0, base_vol_allowance * current_vol_ratio)

                if abs(strike - current_btc) > dynamic_threshold:
                    new_weight = 0.5
                    diagnosis  = "STRIKE_DRIFT"
                    logger.error(f"🚨 [SANITY_FAIL] Отклонение ${abs(strike - current_btc):.0f} > Порога ${dynamic_threshold:.0f} (Vol:{current_vol_ratio:.2f})")
                else:
                    new_weight = 1.0
                    self._current_oracle_weight = 1.0
                    diagnosis  = "NORMAL"
                    logger.critical("🎯 [FAST_AWAKEN] Официальный страйк подтвержден и адекватен. 100% доверие.")

                self._smooth_stress = 0.0
                # ВАЖНО: Мы НЕ перезаписываем self._last_strike_official_state здесь,
                # оставляем это для блока Purge ниже!

            elif not is_now_official:
                new_weight = 0.85
                diagnosis  = "BINANCE_OPEN"

            else:
                if target_weight < curr_weight:
                    new_weight = target_weight
                else:
                    new_weight = min(target_weight, curr_weight + recovery_rate)

            # Strike Sync Purge — Early Exit
            if is_now_official and not was_official:
                # 1. Вот теперь официально фиксируем смену состояния
                self._last_strike_official_state = True
                
                # 2. [ПАТЧ: СБРОС ПАМЯТИ ОРАКУЛА ПРИ ПРЫЖКЕ СТРАЙКА]
                # Используем hasattr, чтобы код не упал, если очередь еще не создана
                if hasattr(self, '_price_history'):
                    self._price_history.clear()
                    logger.info("🧹 [MEMORY_WIPE] История цен сброшена. Убиваем призраков eff_delta.")
                
                # 3. Оригинальная логика Nuclear Reset
                purge_q_threshold = getattr(self.config, 'grid_lot_size', 5) * 3

                if abs(q) >= purge_q_threshold or (time_passed > 60.0):
                    logger.critical(f"🎯 [STRIKE_SYNC_PURGE] Strike verified. Skew {q} > {purge_q_threshold}. Nuclear Reset.")
                    return {
                        'early_exit': True,
                        'actions':    [OrderAction(action='CANCEL_ALL_NUCLEAR', reason="STRIKE_SYNC_PURGE")],
                    }
                else:
                    logger.info(f"🎯 [STRIKE_SYNC_SILENT] Strike verified. Skew {q} is safe. Continuous mode.")

            self._last_oracle_weight = new_weight
            self._last_diagnosis     = diagnosis

            m_state = f"{diagnosis} (W:{new_weight:.2f})"

            # 7.4 Авто-калибровка страйка
            time_passed     = self.config.market_duration_sec - time_rem_sec
            strike_is_accurate = (oracle_diff < 0.03)
            can_calibrate   = not getattr(self, '_is_official_strike', False)

            if can_calibrate and (20 < time_passed < 240) and diagnosis == "STRIKE_DRIFT" and not strike_is_accurate:
                implied_stk = self._calculate_implied_strike(current_btc, mid_market, time_rem_sec, current_vol_ratio)

                if implied_stk and abs(implied_stk - strike) > 12.0:
                    if time.time() - getattr(self, '_last_strike_fix_ts', 0) > 45.0:
                        logger.warning(f"🎯 [STRIKE_FIX] Разрыв подтвержден! Калибровка: ${strike:.0f} -> ${implied_stk:.0f}")

                        if hasattr(self.config.shared_btc_strike, 'value'):
                            self.config.shared_btc_strike.value = float(implied_stk)

                        strike = implied_stk
                        self._last_strike_fix_ts = time.time()

                        oracle_fv = self.oracle_engine.calculate_fv(
                            current_btc, strike, time_rem_sec,
                            self.config.market_duration_sec, vol_ratio=current_vol_ratio
                        )
                        fv_yes = oracle_fv

            # 7.3 Sigmoid Blending
            k_steepness  = self.config.oracle_sigmoid_steepness
            sigmoid_w    = 1.0 / (1.0 + math.exp(-k_steepness * (new_weight - 0.5)))
            fv_effective = (oracle_fv * sigmoid_w) + (mid_market * (1.0 - sigmoid_w))

            oracle_fv      = fv_effective
            fv_yes         = fv_effective
            self.current_fv = fv_effective

            self._last_tick_ts   = now

            # Если вес оракула упал ниже 30%, значит мы торгуем "вслепую" по рынку
            if new_weight < 0.30:
                _now_ts = time.time()
                if _now_ts - getattr(self, '_last_blind_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦👁️‍🗨️ [ORACLE_BLIND] Оракул подавлен! Вес: {new_weight:.2f} | "
                        f"Диагноз: {diagnosis} | Diff: {oracle_diff:.4f} | Thr: {smart_blind_thr:.3f}"
                    )
                    self._last_blind_log = _now_ts

            return {
                'early_exit':   False,
                'new_weight':   new_weight,
                'diagnosis':    diagnosis,
                'fv_yes':       fv_yes,
                'oracle_fv':    oracle_fv,
                'fv_effective': fv_effective,
                'm_state':      m_state,
                'time_passed':  time_passed,
                'strike':       strike,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[RUN_ORACLE_PIPELINE] CRITICAL ERROR: {e} | "
                f"oracle_fv={oracle_fv:.4f}, mid_market={mid_market:.4f}, "
                f"time_rem_sec={time_rem_sec:.1f}, q={q}, "
                f"eff_delta={eff_delta:.4f}, strike={strike:.0f}"
            )
            raise

    def _compute_velocity(self, tick_start_time: float, fv_yes: float, current_btc: float = 0.0) -> float:
        try:
            vel_memory = getattr(self.config, 'velocity_memory_sec', 8.0)

            # --- 1. КОНТУР ОРАКУЛА (Расчет изменения вероятности FV) ---
            if getattr(self, '_history_wiped_for_strike', False) or not hasattr(self, '_price_history') or isinstance(self._price_history, list):
                self._price_history = deque()
                self._history_wiped_for_strike = False

            self._price_history.append((tick_start_time, fv_yes))

            while self._price_history and (tick_start_time - self._price_history[0][0] > vel_memory):
                self._price_history.popleft()

            eff_delta = 0.0
            if len(self._price_history) > 1 and (tick_start_time - self._price_history[0][0]) >= vel_memory * 0.5:
                eff_delta = fv_yes - self._price_history[0][1]

            self._last_effective_delta = eff_delta # Сохраняем для Оракула

            # --- 2. КОНТУР БРОНИ (Чистая скорость BTC в $/sec) ---
            if not hasattr(self, '_btc_history') or isinstance(self._btc_history, list):
                self._btc_history = deque()
                
            self._btc_history.append((tick_start_time, current_btc))
            
            while self._btc_history and (tick_start_time - self._btc_history[0][0] > vel_memory):
                self._btc_history.popleft()

            btc_vel_usd = 0.0
            if len(self._btc_history) > 1 and current_btc > 1000:
                time_window = max(0.1, tick_start_time - self._btc_history[0][0])
                # Считаем абсолютное изменение в долларах, деленное на секунды
                btc_vel_usd = abs(current_btc - self._btc_history[0][1]) / time_window  
                
            self._last_btc_velocity = btc_vel_usd # Сохраняем для Auto Armor

            # --- ЖУЧОК [VELOCITY_STALE] ---
            # Если окно заполнено меньше чем на 50%, логируем "холодный старт"
            _p_len = len(self._price_history)
            if _p_len < 3:
                now_ts = time.time()
                if now_ts - getattr(self, '_last_vel_warmup_log', 0) > 10.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🪦⏳ [VELOCITY_WARMUP] Сбор данных... Окно: {_p_len} тиков. "
                        f"Расчеты eff_delta и btc_vel могут быть неточными. | {self._std_ctx()}"
                    )
                    self._last_vel_warmup_log = now_ts
            # ------------------------------

            return eff_delta # Возвращаем eff_delta для старых вызовов

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_VELOCITY] CRITICAL ERROR: {e} | "
                f"tick_start_time={tick_start_time}, fv_yes={fv_yes:.4f}"
            )
            raise

    @staticmethod
    def _get_k_alpha_dynamic(a_val: float, a_min: float, a_max: float,
                            k_min: float, current_k_max: float) -> float:
        progress = max(0.0, min(1.0, (a_val - a_min) / max(0.0001, a_max - a_min)))
        return k_min + progress * (current_k_max - k_min)

    def _compute_lot_sizing(
        self,
        time_rem_sec: float,
        api_latency: int,
        fv_yes: float,
        mid_market: float,
        q: int,
        hc_limit: int,
        is_desperate: bool,
        is_deadlocked: bool,
        recovery_tag: str,
        eff_delta: float = 0.0,
    ) -> dict:
        try:
            base_lot = self.config.grid_lot_size

            # 1. Инвентарная коррекция
            total_sh  = self.position.yes_shares + self.position.no_shares
            imb_ratio = (self.position.yes_shares - self.position.no_shares) / max(1, total_sh)
            _il = getattr(self, '_intent_load', 0.0)
            _q_corr_floor = max(0.1, 0.5 - (_il * 0.4))  # 0.5→0.1 по мере роста inv_load
            q_corr_y  = max(_q_corr_floor, 1.0 - imb_ratio * 2.0)
            q_corr_n  = max(_q_corr_floor, 1.0 + imb_ratio * 2.0)

            # 2. Alpha (Oracle Discount)
            alpha_y = fv_yes - mid_market
            alpha_n = (1.0 - fv_yes) - (1.0 - mid_market)

            # 3. Kelly Decay
            
            # Берем точку начала эндшпиля (обычно 240-300 сек)
            fade_start = getattr(self.config, 'endgame_fade_start_sec', 300.0)
            
            # Степенная функция (power = 1.5). 
            # Пока времени больше fade_start, t_kelly = 1.0 (максимальная жадность).
            # Как только время падает ниже 300с, жадность начинает стремительно рушиться.
            # На 150с она будет ~0.35, а на 45с упадет до ~0.05.
            t_kelly = min(1.0, (time_rem_sec / fade_start) ** 1.5)
            k_min = getattr(self.config, 'lot_k_min', 1.0)
            current_k_max = k_min + (getattr(self.config, 'lot_k_max', 3.0) - k_min) * t_kelly

            k_y = self._get_k_alpha_dynamic(alpha_y, self.config.alpha_ramp_min, self.config.alpha_ramp_max, k_min, current_k_max)
            k_n = self._get_k_alpha_dynamic(alpha_n, self.config.alpha_ramp_min, self.config.alpha_ramp_max, k_min, current_k_max)

            # 4. Latency Guard
            if api_latency > self.config.latency_trust_threshold:
                k_y, k_n = k_min, k_min

            # 4.5 Lot Choking — подавление лота при ловле ножа
            knife_thr  = 0.030   # граница начала подавления
            knife_full = 0.080   # граница полного подавления
            choke_y = max(0.2, 1.0 - max(0.0, (-eff_delta - knife_thr) / (knife_full - knife_thr)) * 0.8)
            choke_n = max(0.2, 1.0 - max(0.0, ( eff_delta - knife_thr) / (knife_full - knife_thr)) * 0.8)

            # --- [DUAL-CORE DEFENSE: СЛОЙ 1 - ИНВЕНТАРНЫЙ SKEW + СЛОЙ 2 - MOMENTUM VETO] ---
            cvd_signal  = getattr(self, '_cvd_signal_last', 0.0)
            cvd_streak  = getattr(self, '_cvd_toxic_streak', 0)
            open_q_abs  = abs(q)

            # Слой 1: ВЕКТОРНЫЙ порог страха (Защита Капитала)
            _hunter_thr_base = getattr(self.config, 'hunter_imb_threshold', 15)
            
            # Определяем цену той ноги, которой у нас СЕЙЧАС больше
            heavy_leg_price = fv_yes if q > 0 else (1.0 - fv_yes)
            
            if heavy_leg_price > 0.5:
                # МЫ НАКОПИЛИ ДОРОГУЮ НОГУ (Капиталоемкий риск)
                # Чем дороже нога, тем жестче мы сужаем порог (вплоть до x0.25 от базы)
                # Если цена 0.90, множитель будет ~0.36 -> паника начнется уже при 5 акциях
                fv_multiplier = max(0.25, 1.0 - ((heavy_leg_price - 0.5) * 2.0) ** 2)
            else:
                # МЫ НАКОПИЛИ ДЕШЕВУЮ НОГУ (Лоторейные билеты)
                # Чем дешевле нога, тем шире мы раздвигаем порог (до x2.0)
                # Если цена 0.10, множитель будет 1.64 -> разрешаем копить до 25 акций
                fv_multiplier = 1.0 + (((0.5 - heavy_leg_price) * 2.0) ** 2)
                
            _hunter_thr = max(5, int(_hunter_thr_base * fv_multiplier))

            # --- [ВЕКТОРНОЕ УДУШЕНИЕ (ПАТЧ АСИММЕТРИИ)] ---
            _avgmax_q   = getattr(self.config, 'cvd_avgmax_q', 35.0)
            
            # Читаем порог как абсолютное положительное число
            _base_thr   = abs(getattr(self.config, 'cvd_skew_activation_threshold', 0.05))
            
            q_excess    = max(0, open_q_abs - _hunter_thr)
            q_ratio     = min(1.0, q_excess / max(1.0, _avgmax_q - _hunter_thr))
            
            # Чем больше инвентаря, тем раньше мы пугаемся (снижаем порог)
            dyn_thr = max(0.01, _base_thr - ((q_ratio ** 1.5) * 0.03)) 

            # Слой 2: momentum VETO (детектор торпеды)
            veto_active = getattr(self, '_cvd_veto_active', False)

            # АКТИВАЦИЯ ПО МОДУЛЮ CVD (Реагируем на тренды в обе стороны)
            abs_cvd = abs(cvd_signal)
            skew_active    = abs_cvd > dyn_thr
            skew_intensity = max(0.0, abs_cvd - dyn_thr)
            skew_pct       = min(1.0, skew_intensity / 0.40)

            if veto_active:
                if time.time() - getattr(self, '_last_veto_sizing_log', 0) > 1.0:
                    logging.getLogger('gabalog.grid_strategy').warning(f"🪦⚓ [VETO_SIZING] Лоты обнулены по сигналу Торпеды (CVD Veto) | {self._std_ctx()}")
                    self._last_veto_sizing_log = time.time()
                choke_y = 0.0
                choke_n = 0.0
            # [v2.6] CVD lot choke убран: на бинарном рынке CVD структурно 0.85+
            # 80-97% тиков уходили в choke × 0.20 — это убивало Cap_Util%
            # Lot sizing управляется: q_corr + knife_choke + is_hedge_only + is_desperate
            # Экстремальная защита (veto) выше остаётся

            # 5. Space Left Filter
            space_y  = max(0, hc_limit - q) if q >= 0 else hc_limit
            space_n  = max(0, hc_limit + q) if q <= 0 else hc_limit

            # 6. Финальная сборка лотов (Асимметрия & Квантование)
            final_lot_y = base_lot
            final_lot_n = base_lot
            
            # Читаем минимальный квант биржи
            MIN_MKT_LOT = 5

            if is_desperate:
                if is_deadlocked:
                    pass
                else:
                    panic_lot = min(int(abs(q)), getattr(self.config, 'max_single_lot', 50))
                    panic_lot = max(MIN_MKT_LOT, int(math.ceil(panic_lot / MIN_MKT_LOT)) * MIN_MKT_LOT)

                    if q > 0:
                        # Перекос YES → закрываем NO крупным лотом, YES минимум
                        final_lot_y = MIN_MKT_LOT
                        if "🆘[HEAL_NO]" not in recovery_tag and "🌀[HEAL_MIRROR_NO]" not in recovery_tag:
                            final_lot_n = max(MIN_MKT_LOT, min(panic_lot, space_n))
                    else:
                        # Перекос NO → закрываем YES крупным лотом, NO минимум
                        final_lot_n = MIN_MKT_LOT
                        if "🆘[HEAL_YES]" not in recovery_tag and "🌀[HEAL_MIRROR_YES]" not in recovery_tag:
                            final_lot_y = max(MIN_MKT_LOT, min(panic_lot, space_y))
            else:
                # [ПАТЧ: Асимметричный Мейкер + HEDGE ONLY + VETO RESPECT]
                _asym_thr       = getattr(self.config, 'asym_cvd_threshold', 0.40)
                _asym_time_gate = getattr(self.config, 'asym_time_gate_sec', 600.0)
                _q_heavy_yes = q > 5   # у нас перевес YES
                _q_heavy_no  = q < -5  # у нас перевес NO
                _asym_active = (abs(cvd_signal) > _asym_thr) and \
                            (time_rem_sec > _asym_time_gate) and \
                            ((_q_heavy_yes and cvd_signal < 0) or (_q_heavy_no and cvd_signal > 0))

                # Вычисляем порог перехода в глухую оборону (70% от динамического лимита)
                _il = getattr(self, '_intent_load', 0.0)
                hedge_only_thr = int(hc_limit * max(0.40, 0.70 - (_il * 0.30)))
                is_hedge_only_y = q > hedge_only_thr  # Запрет на расширение YES
                is_hedge_only_n = q < -hedge_only_thr # Запрет на расширение NO

                # --- ВСТАВЛЯЕМ ЖУЧОК СЮДА ---
                if is_hedge_only_y or is_hedge_only_n:
                    now_ts = time.time()
                    if now_ts - getattr(self, '_last_hedge_lock_log', 0) > 15.0:
                        locked_side = "YES" if is_hedge_only_y else "NO"
                        logging.getLogger('gabalog.grid_strategy').warning(
                            f"🪦🔒 [HEDGE_LOCK] Сторона {locked_side} заблокирована на расширение! "
                            f"Q: {q} | Limit: {hc_limit} | Threshold: {hedge_only_thr}"
                        )
                        self._last_hedge_lock_log = now_ts
                # ----------------------------

                if "🆘[HEAL_YES]" not in recovery_tag and "🌀[HEAL_MIRROR_YES]" not in recovery_tag:
                    # Рассчитываем raw_lot один раз в начале для работы жучка
                    raw_lot_y = int(base_lot * k_y * q_corr_y * choke_y)
                    
                    # [WIRETAP] Ловим затухание лота YES
                    if 0 < raw_lot_y < MIN_MKT_LOT:
                        if time.time() - getattr(self, '_last_min_lot_y_log', 0) > 1.0:
                            logging.getLogger('gabalog.grid_strategy').warning(
                                f"🪦📉 [LOT_DECAY] YES лот {raw_lot_y} → MIN:{MIN_MKT_LOT} | "
                                f"base={base_lot} k={k_y:.2f} qcorr={q_corr_y:.2f} choke={choke_y:.2f} | "
                                f"skew={skew_active} veto={veto_active} | {self._std_ctx()}"
                            )
                            self._last_min_lot_y_log = time.time()
                        raw_lot_y = MIN_MKT_LOT

                    # ТВОЯ ОРИГИНАЛЬНАЯ ЛОГИКА БЕЗ ИЗМЕНЕНИЙ:
                    if raw_lot_y < 1 or is_hedge_only_y or (_asym_active and cvd_signal > 0):
                        final_lot_y = 0
                    elif is_hedge_only_n:
                        recovery_lot = min(int(abs(q)), getattr(self.config, 'max_single_lot', 50))
                        final_lot_y = max(MIN_MKT_LOT, int(math.ceil(recovery_lot / MIN_MKT_LOT)) * MIN_MKT_LOT)
                        final_lot_y = min(final_lot_y, space_y)                    
                    else:
                        final_lot_y = 0 if raw_lot_y < 1 else min(space_y, max(MIN_MKT_LOT, int(round(raw_lot_y / MIN_MKT_LOT)) * MIN_MKT_LOT))

                if "🆘[HEAL_NO]" not in recovery_tag and "🌀[HEAL_MIRROR_NO]" not in recovery_tag:
                    # Рассчитываем raw_lot один раз в начале для работы жучка
                    raw_lot_n = int(base_lot * k_n * q_corr_n * choke_n)

                    # [WIRETAP] Ловим затухание лота NO
                    if 0 < raw_lot_n < MIN_MKT_LOT:
                        if time.time() - getattr(self, '_last_min_lot_n_log', 0) > 1.0:
                            logging.getLogger('gabalog.grid_strategy').warning(
                                f"🪦📉 [LOT_DECAY] NO лот {raw_lot_n} → MIN:{MIN_MKT_LOT} | "
                                f"base={base_lot} k={k_n:.2f} qcorr={q_corr_n:.2f} choke={choke_n:.2f} | "
                                f"skew={skew_active} veto={veto_active} | {self._std_ctx()}"
                            )
                            self._last_min_lot_n_log = time.time()
                        raw_lot_n = MIN_MKT_LOT

                    # ТВОЯ ОРИГИНАЛЬНАЯ ЛОГИКА БЕЗ ИЗМЕНЕНИЙ:
                    if is_hedge_only_n or (_asym_active and cvd_signal < 0):
                        final_lot_n = 0  
                    elif is_hedge_only_y:
                        recovery_lot = min(int(abs(q)), getattr(self.config, 'max_single_lot', 50))
                        final_lot_n = max(MIN_MKT_LOT, int(math.ceil(recovery_lot / MIN_MKT_LOT)) * MIN_MKT_LOT)
                        final_lot_n = min(final_lot_n, space_n)
                    else:
                        final_lot_n = 0 if raw_lot_n < 1 else min(space_n, max(MIN_MKT_LOT, int(round(raw_lot_n / MIN_MKT_LOT)) * MIN_MKT_LOT))

            # === [Q-THROTTLE 2026-05-13, rev 2] ============================
            # Forensics: max_q 5-10 → WR 48% / PnL $+2.67; max_q 10-20 → WR 28%
            # / PnL -$171. To bias position size into the winning bucket the
            # OPENING side must be capped before Q reaches 10. Closing side
            # is NOT touched here — Hunter Lot Override (line 1779) takes
            # over and sizes the closing leg = abs(q) to unwind aggressively.
            # Initial 5/10/15 thresholds were too loose (max_q drifted to 15).
            # Tightened to 3/5/8 to keep observed max_q in 5-10 zone.
            if not is_desperate:
                Q_SOFT_BRAKE = 5
                Q_HARD_BRAKE = 8
                Q_FULL_BLOCK = 12
                _abs_q = abs(q)
                if _abs_q >= Q_FULL_BLOCK:
                    # Block expansion on heavy side completely
                    if q > 0:
                        final_lot_y = 0
                    elif q < 0:
                        final_lot_n = 0
                elif _abs_q >= Q_HARD_BRAKE:
                    if q > 0:
                        final_lot_y = min(final_lot_y, MIN_MKT_LOT)
                    elif q < 0:
                        final_lot_n = min(final_lot_n, MIN_MKT_LOT)
                elif _abs_q >= Q_SOFT_BRAKE:
                    if q > 0:
                        final_lot_y = max(MIN_MKT_LOT, final_lot_y // 2) if final_lot_y > 0 else 0
                    elif q < 0:
                        final_lot_n = max(MIN_MKT_LOT, final_lot_n // 2) if final_lot_n > 0 else 0
                # Quantize to MIN_MKT_LOT
                if final_lot_y > 0:
                    final_lot_y = int(round(final_lot_y / MIN_MKT_LOT)) * MIN_MKT_LOT
                if final_lot_n > 0:
                    final_lot_n = int(round(final_lot_n / MIN_MKT_LOT)) * MIN_MKT_LOT

            # [v2.10 PAIR_STATE Рычаг 1] Lot adjustment в FRESH (финальный override)
            # Применяется ПОСЛЕ всей логики lot sizing (desperate, hedge_only, asym, choke).
            # Closing leg (нога которая закрывает Q): +50% лот для повышения шанса fill
            # Opening leg (нога которая увеличивает Q): throttled до MIN_MKT_LOT (не накапливаем exposure)
            # В desperate режиме pair_state НЕ применяется — там своя приоритезация.
            if not is_desperate:
                _ps_state = getattr(self, '_pair_state', 'BALANCED')
                _ps_close = getattr(self, '_closing_side', None)
                if _ps_state == 'FRESH':
                    if _ps_close == 'YES':
                        # Closing = YES: +50% YES, throttle NO
                        if final_lot_y > 0:
                            _boosted_y = int(final_lot_y * 1.5)
                            # Квантование к MIN_MKT_LOT и зажим в space
                            final_lot_y = min(space_y, max(MIN_MKT_LOT, int(round(_boosted_y / MIN_MKT_LOT)) * MIN_MKT_LOT))
                        if final_lot_n > MIN_MKT_LOT:
                            final_lot_n = MIN_MKT_LOT
                    elif _ps_close == 'NO':
                        # Closing = NO: +50% NO, throttle YES
                        if final_lot_n > 0:
                            _boosted_n = int(final_lot_n * 1.5)
                            final_lot_n = min(space_n, max(MIN_MKT_LOT, int(round(_boosted_n / MIN_MKT_LOT)) * MIN_MKT_LOT))
                        if final_lot_y > MIN_MKT_LOT:
                            final_lot_y = MIN_MKT_LOT

            # 7. Синхронизация Хилера (Лекарь должен бить весомо)
            # Если перекос 30 штук, Лекарь бьет по 15 (выровнено до 5), а не по 5
            raw_healer_lot = max(MIN_MKT_LOT, int(abs(q) * 0.5))
            self._dynamic_avg_tranche_max_size = max(MIN_MKT_LOT, int(round(raw_healer_lot / MIN_MKT_LOT)) * MIN_MKT_LOT)

            return {
                'final_lot_y':  final_lot_y,
                'final_lot_n':  final_lot_n,
                'base_lot':     base_lot,
                'k_y':          k_y,
                'k_n':          k_n,
                'alpha_y':      alpha_y,
                'alpha_n':      alpha_n,
                't_kelly':      t_kelly,
                'current_k_max': current_k_max,
                'space_y':      space_y,
                'space_n':      space_n,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_LOT_SIZING] CRITICAL ERROR: {e} | "
                f"q={q}, time_rem_sec={time_rem_sec:.1f}, api_latency={api_latency}, "
                f"is_desperate={is_desperate}, is_deadlocked={is_deadlocked}, "
                f"fv_yes={fv_yes:.4f}, mid_market={mid_market:.4f}"
            )
            raise

    def _compute_shadow_accounting(self, q: int) -> dict:
        try:
            MAX_SKEW_DELTA = getattr(self.config, 'hard_cutoff_shares', 40)

            # 1. Активные (незахеджированные) ноги
            locked          = self.position.locked_pairs        # min(total_yes, total_no)
            open_yes        = self.position.total_yes - locked  # незахеджированный YES хвост
            open_no         = self.position.total_no  - locked  # незахеджированный NO хвост
            open_q          = open_yes - open_no                # знаковый чистый риск без in_flight
            # active_* оставляем для обратной совместимости с eval_* логикой
            active_y_shares = max(0, open_q)
            active_n_shares = max(0, -open_q)

            y_avg_price = (self.position.yes_cost / max(1, self.position.total_yes)) if self.position.total_yes > 0 else 0.0
            n_avg_price = (self.position.no_cost / max(1, self.position.total_no)) if self.position.total_no > 0 else 0.0

            # 2. Здоровье инвентаря (оставляем для телеметрии)
            inv_ps = y_avg_price + n_avg_price

            # --- ЖУЧОК [SHADOW_TOXIC] ---
            # Ловим момент, когда сумма цен выше 1.01 (гарантированный убыток на замке)
            if inv_ps > 1.01:
                _now = time.time()
                if _now - getattr(self, '_last_toxic_wiretap', 0) > 15.0:
                    logging.getLogger('gabalog.grid_strategy').error(
                        f"☣️🪦 [SHADOW_TOXIC] Инвентарь отравлен! PS: {inv_ps:.4f} | "
                        f"Locked: {locked} | Любое закрытие замка = минус. | {self._std_ctx()}"
                    )
                    self._last_toxic_wiretap = _now
            # ----------------------------

            is_inventory_healthy = inv_ps <= 1.00 and self.position.locked_pairs > 0

            # ПРАВИЛЬНАЯ ЛОГИКА:
            # Мы ВСЕГДА вычитаем стоимость заблокированных пар из общего котла.
            # Замок (Lock) — это завершенный цикл. Его цена (пусть и плохая) больше не должна 
            # "отравлять" расчет средней цены для НОВЫХ открытых позиций (хвоста).
            if self.position.locked_pairs > 0:
                locked_pairs_cost = self.position.locked_pairs * inv_ps
            else:
                locked_pairs_cost = 0.0

            # Теперь open_cost будет показывать ТОЛЬКО те деньги, 
            # которые реально "зависли" в перекосе (open_q).
            open_cost = max(0.0, self.position.total_cost - locked_pairs_cost)

            # 4. Блокировщик видит хвост при здоровом инвентаре
            eval_y_shares = active_y_shares if is_inventory_healthy else self.position.yes_shares
            eval_n_shares = active_n_shares if is_inventory_healthy else self.position.no_shares

            eval_y_cost = eval_y_shares * y_avg_price
            eval_n_cost = eval_n_shares * n_avg_price

            # [SHADOW BOOK v2.0] Телеметрия токсичности замков
            if locked > 0 and time.time() - getattr(self, '_last_shadow_log', 0) > 5.0:
                # СТАЛО:
                # СТАЛО (правильное):
                logger.info(
                    f"🔒 [SHADOW_BOOK] locked={locked} | "
                    f"inv_ps={inv_ps:.4f} | "
                    f"toxic={'YES' if inv_ps > 1.00 else 'NO'} | "
                    f"open_q={open_q} | "
                    f"open_cost={open_cost:.3f} | "
                    f"y_avg={y_avg_price:.4f} | "
                    f"n_avg={n_avg_price:.4f} | "
                    f"y_sh={self.position.total_yes} | "
                    f"n_sh={self.position.total_no}"
                )
                self._last_shadow_log = time.time()

            return {
                'MAX_SKEW_DELTA':       MAX_SKEW_DELTA,
                'active_y_shares':      active_y_shares,
                'active_n_shares':      active_n_shares,
                'y_avg_price':          y_avg_price,
                'n_avg_price':          n_avg_price,
                'is_inventory_healthy': is_inventory_healthy,
                'eval_y_shares':        eval_y_shares,
                'eval_n_shares':        eval_n_shares,
                'eval_y_cost':          eval_y_cost,
                'eval_n_cost':          eval_n_cost,
                # [SHADOW BOOK v2.0] — новые поля
                'open_q':              open_q,
                'locked_pairs_cost':   locked_pairs_cost,
                'open_cost':           open_cost,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[SHADOW_ACCOUNTING] CRITICAL ERROR: {e} | "
                f"q={q}, open_q={open_q if 'open_q' in dir() else 'N/A'}, "
                f"yes_shares={self.position.yes_shares}, no_shares={self.position.no_shares}, "
                f"locked_pairs={self.position.locked_pairs}"
            )
            raise

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
        try:
            # 1. Heavy Leg и Price Factor (без изменений)
            heavy_price = fv_yes if q > 0 else (1.0 - fv_yes) if q < 0 else 0.5
            raw_price_factor = 1.0 - (heavy_price - 0.5)
            price_factor = max(0.85, min(1.15, raw_price_factor))

            # 2. Velocity Guard (без изменений)
            knife_threshold = 0.025
            is_knife_falling = (q >= 5 and eff_delta <= -knife_threshold) or (q <= -5 and eff_delta >= knife_threshold)
            vel_panic = 1.5 if is_knife_falling else 1.0
            if vel_panic > 1.0:
                self._log_decision('VELOCITY_GUARD', f"⚠️ [KNIFE_ALARM] Q:{q} под ударом тренда Δ:{eff_delta:.4f}. Штраф x1.5")

            dynamic_q = abs(q) * price_factor * vel_panic

            p_side = {}
            for _side in ['YES', 'NO']:
                _q_eff = q if _side == 'YES' else -q

                # Если перекоса нет на этой стороне — нет штрафа
                if _q_eff <= 0:
                    p_side[_side] = 0.0
                    continue

                # [ФИКС 1] Инверсия deadband: при падающем ноже зона СУЖАЕТСЯ
                is_weak_leg = (_side == 'YES' and eff_delta < 0) or (_side == 'NO' and eff_delta > 0)
                side_deadband = dyn_base_deadband * (0.5 if is_weak_leg else 1.0)

                # [ФИКС 2] Оживляем мёртвый код асимметрии
                current_side_scale = effective_scale
                if heavy_leg and _side == heavy_leg:
                    current_side_scale *= self._risk_dampener
                else:
                    current_side_scale *= self._hedge_boost

                power = getattr(self.config, 'risk_weight_power', 2.0)

                # [ФИКС 3] Динамическая агрессия — растёт с перекосом, потолок 10.0
                _dyn_inv_scale = getattr(self, '_prev_dyn_scale', 25.0)
                aggression_scale = max(10.0, _dyn_inv_scale - (abs(_q_eff) * 0.5))

                raw_steps = max(0, (_q_eff * price_factor * vel_panic) - side_deadband)
                side_linear_steps = raw_steps / aggression_scale

                # [ФИКС 4] Асимметрия через мягкий множитель + потолок 5 центов
                asym_factor = max(0.5, min(2.0, current_side_scale / max(1.0, effective_scale)))
                raw_penalty = (side_linear_steps ** power) * TICK_SIZE * p_stress_mult

                # [v2.10 PAIR_STATE Рычаг 2] Penalty modulation в FRESH
                # Closing leg получает 0.3x штрафа (агрессивная цена → ближе к bid → выше шанс fill)
                # Opening leg получает 1.5x штрафа (отталкивает от стакана → не накапливаем exposure)
                _pair_state   = getattr(self, '_pair_state', 'BALANCED')
                _closing_side = getattr(self, '_closing_side', None)
                if _pair_state == 'FRESH':
                    if _side == _closing_side:
                        raw_penalty *= 0.3
                    else:
                        raw_penalty *= 1.5

                p_side[_side] = min(0.15, raw_penalty * asym_factor)

                # [WIRETAP] Отложенный смертный приговор (GC Limit Check)
                now = time.time()
                if p_side.get('YES', 0.0) >= 0.05:
                    if now - getattr(self, '_last_poison_y', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(f"🪦☢️ [POISON_MATH] Штраф YES достиг {p_side.get('YES'):.3f} (Гарантированное убийство в GC) | {self._std_ctx()}")
                        self._last_poison_y = now
                        
                if p_side.get('NO', 0.0) >= 0.05:
                    if now - getattr(self, '_last_poison_n', 0.0) > 1.0:
                        logging.getLogger('gabalog.grid_strategy').warning(f"🪦☢️ [POISON_MATH] Штраф NO достиг {p_side.get('NO'):.3f} (Гарантированное убийство в GC) | {self._std_ctx()}")
                        self._last_poison_n = now

            return {
                'p_yes':        p_side.get('YES', 0.0),
                'p_no':         p_side.get('NO', 0.0),
                'dynamic_q':    dynamic_q,
                'vel_panic':    vel_panic,
                'price_factor': price_factor,
                'p_side':       p_side,
            }

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[COMPUTE_ELASTIC_GRAVITY] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.4f}, eff_delta={eff_delta:.4f}, "
                f"dyn_base_deadband={dyn_base_deadband:.3f}, effective_scale={effective_scale:.2f}, "
                f"heavy_leg={heavy_leg}"
            )
            raise

    

    def _run_forensic_telemetry(
        self,
        # --- Market data ---
        yes_bid: float, no_bid: float, yes_ask: float, no_ask: float,
        mid_market: float, current_btc: float, strike: float,
        # --- Pipeline: Oracle ---
        fv_yes: float, oracle_fv: float, new_weight: float, diagnosis: str,
        eff_delta: float, current_vol_ratio: float,
        # --- Pipeline: Pricing ---
        alpha_y: float, alpha_n: float, dynamic_maq: float,
        current_k_max: float, l0_y: float, l0_n: float,
        final_lot_y: int, final_lot_n: int,
        # --- Pipeline: Inventory & Mode ---
        q: int, dynamic_q: float, effective_scale: float,
        p_yes: float, p_no: float, active_gate_limit: float,
        recovery_tag: str, is_desperate: bool, is_warmup: bool,
        # --- Pipeline: System ---
        required_sec: float, current_cfr: float, api_latency: int,
        m_slug: str, t_rem: int, tick_start_time: float,
        # --- Pipeline: Misc ---
        m_state: str, inv_load: float, dyn_is: float,
        target: list, actions: list,
        # --- Telemetry object ---
        tel,
        market_data: dict,
        cvd_skew: float = 0.0,
        streak_skew: int = 0,
        open_q_skew: int = 0,
        space_skew: int = 100,
    ) -> list:
        try:
            # 1. СТАТИЧЕСКИЕ ПАРАМЕТРЫ ДЛЯ ВСЕХ ЛОГОВ (Считаем всегда)
            y_exit_p = yes_bid if yes_bid > 0 else 0.01
            n_exit_p = no_bid if no_bid > 0 else 0.01
            liquid_val = (self.position.total_yes * y_exit_p) + (self.position.total_no * n_exit_p)
            self._last_expected_pnl = liquid_val - self.position.total_cost + self.position.realized_ctf_pnl

            in_flight_cost = (self.position.yes_in_flight + self.position.no_in_flight) * mid_market
            budget_rem = max(0.0, self.config.deposit - (self.position.total_cost + self.grid_manager.get_pending_notional() + in_flight_cost))
            margin_oxygen_pct = int((budget_rem / self.config.deposit) * 100) if self.config.deposit > 0 else 0

            # 2. ИЕРАРХИЯ ИНТЕНТОВ
            intent = "NORMAL"

            has_nuclear = any(getattr(a, 'action', '') == 'CANCEL_ALL_NUCLEAR' for a in actions)
            has_dump = any("TRIAGE_TAKER_DUMP" in str(getattr(a, 'reason', '')) for a in actions)
            has_recovery = "RECOVERY" in getattr(self, '_triage_decision', '')

            is_yellow_recycle = any("ED_YELLOW_MAKER_EXIT" in str(getattr(a, 'reason', '')) for a in actions)
            is_normal_recycle = any("MAKER_RECYCLE" in str(getattr(a, 'reason', '')) for a in actions)

            if has_nuclear:
                intent = "TIME_STOP" if "TIME_STOP" in str(getattr(actions[0], 'reason', '')) else "NUCLEAR_CLEAR"
            elif self._merge_state != 'IDLE':
                intent = "MERGE_LOCK"
            elif has_dump:
                intent = "DUMP_RED_ZONE"
            elif has_recovery:
                intent = "RECOVERY_ZONE"
            elif self._ed_level == 1:
                intent = "PROFIT_SHIELD"
            elif is_yellow_recycle:
                intent = "RECYCLE_YELLOW"
            elif is_normal_recycle:
                intent = "RECYCLE_L0"
            # --- ФИКС ДЛЯ ЗЕРКАЛА ---
            elif "🌀" in recovery_tag or "HEAL_MIRROR" in recovery_tag:
                intent = "HEALER_MIRROR"
            # ------------------------
            elif "🆘[HEAL" in recovery_tag:
                intent = "HEALER"
            elif is_desperate:
                intent = "HUNTER"
            elif getattr(self, '_is_panic_frozen', False):
                intent = "BUNKER"
            elif is_warmup:
                intent = "WARMUP"
            elif getattr(self, '_consensus_confirmed', False):
                intent = "CAPITULATION"

            self._last_intent = intent

            # 3. EXPECTED SLIPPAGE
            self._last_fill_slippage = 0.0
            taker_actions = [a for a in actions if getattr(a, 'is_taker', False)]

            if taker_actions:
                t_act = taker_actions[0]
                side_str = str(t_act.side).upper()

                if "YES" in side_str:
                    ideal_mid = (yes_bid + yes_ask) / 2.0 if (yes_bid > 0 and yes_ask > 0) else t_act.price
                elif "NO" in side_str:
                    ideal_mid = (no_bid + no_ask) / 2.0 if (no_bid > 0 and no_ask > 0) else t_act.price
                else:
                    ideal_mid = t_act.price

                if ideal_mid > 0:
                    self._last_fill_slippage = abs(ideal_mid - t_act.price)

            # 4. ПЕЧАТЬ SKEW (раз в 5 секунд)
            if time.time() - getattr(self, '_last_math_log', 0) > 5.0:
                p_buff = getattr(self, '_current_profit_buffer', 0.0)
                stk_v = 1 if getattr(self, '_is_official_strike', False) else 0

                y_avg_p = self.position.yes_cost / max(1, self.position.total_yes) if self.position.total_yes > 0 else 0.0
                n_avg_p = self.position.no_cost / max(1, self.position.total_no) if self.position.total_no > 0 else 0.0
                y_log = f"{self.position.yes_shares}({self.position.total_yes})+F{self.position.yes_in_flight}"
                n_log = f"{self.position.no_shares}({self.position.total_no})+F{self.position.no_in_flight}"

                s_thr = getattr(self, '_live_shield_thr', 0.75)
                r_x = getattr(self, '_risk_dampener', 1.0)
                h_x = getattr(self, '_hedge_boost', 1.0)

                m_ps_y = (l0_y + market_data.get('no_ask', 0.5)) if l0_y > 0 else 0.0
                m_ps_n = (l0_n + market_data.get('yes_ask', 0.5)) if l0_n > 0 else 0.0
                m_lock = "LOCKED" if market_data.get('merge_in_progress', False) else "OPEN"

                logging.getLogger('gabalog.grid_strategy').info(
                    f"🧮 [SKEW] "
                    f"[MKT] {m_slug} | BTC:{current_btc:.0f} | STK:{strike:.0f}({stk_v}) | T:{t_rem}s | ΔBTC:{eff_delta:.4f} | "
                    f"[SENSE] VegaX:{current_vol_ratio:.2f} | Stress:{self._smooth_stress:.2f}(thr:{s_thr:.2f}) | CVD:{cvd_skew:+.3f} | Streak:{streak_skew} | "
                    f"[ORACLE] FV:{fv_yes:.3f} | Trust:{new_weight:.2f} | Diag:{diagnosis} | Edge:{self.config.target_edge:.3f} | "
                    f"[MATH] Th_MAQ:{dynamic_maq:.3f} | kMax:{current_k_max:.1f} | Quote_Y:{l0_y:.3f}_x{final_lot_y} | Quote_N:{l0_n:.3f}_x{final_lot_n} | "
                    f"[RISK] Q:{q} | OpenQ:{open_q_skew} | R_Q:{dynamic_q:.1f} | Pen_Y:{p_yes:+.3f} | Pen_N:{p_no:+.3f} | Space:{space_skew}% | Pos_Y:{y_log} | Pos_N:{n_log} | Lck:{self.position.locked_pairs} | Shadow:${self.position.active_total_cost:.1f} | Oxy:{margin_oxygen_pct}% | "
                    f"[GATES] Gate:{active_gate_limit:.3f} (Base:{self.config.profit_gate_ps_max:.3f}) | MPS_Y:{m_ps_y:.3f} | MPS_N:{m_ps_n:.3f} | InvPS:{y_avg_p + n_avg_p:.3f} | H_Gate:{self.config.hunter_max_gate:.3f} | "
                    f"[PROFIT] PnL:{self.position.realized_ctf_pnl:+.4f} | Exp_PnL:{self._last_expected_pnl:+.4f} | "
                    f"[EXEC] Intent:{self._last_intent} | Reg:{m_state}{recovery_tag} | Triage:{self._triage_active_side or 'OFF'} | "
                    f"[LIFE] Tox:{self._toxic_position_ticks} | Burst:{self._fills_this_tick} | "
                    f"[SYSTEM] BBO_Y:{yes_bid:.3f}-{yes_ask:.3f} | BBO_N:{no_bid:.3f}-{no_ask:.3f} | RTT:{api_latency}ms | "
                    f"[DEBUG] HC:{getattr(self, '_dynamic_hard_cutoff', 350)} | IS:{dyn_is:.1f} | InvL:{inv_load:.2f} | T_Len:{len(target)}"
                )
                self._last_math_log = time.time()

            # 5. TELEMETRY
            tel.as_delta = p_yes if abs(p_yes) > abs(p_no) else -p_no
            tel.fv = fv_yes
            tel.raw_oracle_fv = oracle_fv
            tel.trust = getattr(self, '_current_oracle_weight', 1.0)
            tel.stk_v = 1 if self._is_official_strike else 0
            tel.penalty = max(abs(p_yes), abs(p_no))
            tel.deadband = float(effective_scale)
            tel.spread = abs(yes_ask - yes_bid) if yes_ask > 0 and yes_bid > 0 else 0.0
            tel.step_reached = 'TICK_END'
            self.last_telemetry = tel

            # --- ИЗМЕНЕННЫЙ ШАГ 1: ПЕЧАТЬ В СЫРОЙ ЛОГ ДЛЯ ПАРСЕРА (MAX DATA) ---
            current_ts = time.time()
            if current_ts - getattr(self, '_last_raw_tel_log', 0) >= 2: # <--- 0.1s
                cvd_val = getattr(self, '_cvd_signal_last', 0.0)
                stress_val = getattr(self, '_smooth_stress', 0.0)
                
                logging.getLogger('gabalog.grid_strategy').info(
                    f"🧬 [TEL_TICK] TS:{current_ts:.1f} | CVD:{cvd_val:.3f} | Q:{q} | "
                    f"FV:{fv_yes:.3f} | Sprd:{tel.spread:.3f} | Pen:{tel.penalty:.3f} | "
                    f"dBTC:{eff_delta:.4f} | Str:{stress_val:.2f}"
                )
                self._last_raw_tel_log = current_ts

            self._regime_history.append({'ts': round(time.time(), 1), 'delta': round(eff_delta, 4)})

            # 6. ТАЙМЕРЫ И ЛАГИ
            if time.time() - getattr(self, '_last_temporal_log', 0) >= 1.0:
                p_ts_obj = getattr(self.config, 'shared_btc_ts', None)
                arrival_ts = p_ts_obj.value if (p_ts_obj and hasattr(p_ts_obj, 'value')) else 0.0
                oracle_data_age_ms = int((time.time() - arrival_ts) * 1000) if arrival_ts > 0 else 999
                logging.getLogger('gabalog.grid_strategy').info(
                    f"⏱️ [TEMPORAL] Oracle_Age:{oracle_data_age_ms}ms | Margin_Oxygen:{margin_oxygen_pct}%"
                )
                self._last_temporal_log = time.time()

            internal_processing_ms = int((time.time() - tick_start_time) * 1000)
            if internal_processing_ms > 100:
                if time.time() - getattr(self, '_last_brain_lag_log', 0) > 5.0:
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"🐢 [BRAIN LAG] Total Processing took {internal_processing_ms}ms"
                    )
                    self._last_brain_lag_log = time.time()

            return actions

        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').error(
                f"[FORENSIC_TELEMETRY] CRITICAL ERROR: {e} | "
                f"q={q}, fv_yes={fv_yes:.3f}, intent={intent if 'intent' in dir() else 'N/A'}, "
                f"actions_len={len(actions)}, t_rem={t_rem}"
            )
            raise

    def _synthesize_master_intent(self, decision: str, recovery_tag: str, l0_y: float, l0_n: float, q: int) -> str:
        # 1. Распознавание активных ролей
        is_hunter_active = 'HUNTER' in decision and 'OFF' not in decision and 'CRASH' not in decision
        is_healer_active = (
            ('🩺' in recovery_tag) or 
            ('🆘' in recovery_tag) or 
            ('🌀' in recovery_tag) or 
            ('RECOVERY' in decision)
        )
        
        # Флаг блокировки
        is_gate_blocked = (l0_y <= 0.01 and q < 0) or (l0_n <= 0.01 and q > 0)

        # --- СЛОЙ БЛОКИРОВОК ---
        if is_hunter_active and is_gate_blocked:
            return 'HUNTER_BLOCKED_BY_GATE'
        if is_healer_active and is_gate_blocked:
            return 'HEALER_BLOCKED_BY_GATE'
        if 'VETO' in decision and is_gate_blocked:
            return 'VETO_BLOCKED'

        # --- СЛОЙ ЭВАКУАЦИИ ---
        if 'TRIAGE' in decision or 'PANIC_HUNTER' in decision:
            return 'EMERGENCY_EXIT'

        # --- СЛОЙ ОХОТНИКА ---
        if 'HUNTER_TEETH' in decision:
            return 'HUNTER_AGGRESSIVE'
        if 'HUNTER' in decision:
            return 'HUNTER_PASSIVE'

        # --- СЛОЙ ЛЕКАРЯ ---
        if 'MEDICAL_TRANCHE' in decision:
            return 'HEALER_MEDICAL'
            
        if '🌀' in recovery_tag or 'MIRROR_RECOVERY' in decision:
            return 'HEALER_MIRROR' # <--- [ФИКС] ТЕПЕРЬ ТАБЛО БУДЕТ ВИДЕТЬ ИМЕННО ЗЕРКАЛО КАК ОТДЕЛЬНЫЙ КЛАСС
            
        if is_healer_active:
            if 'PAUSE' in decision:
                return 'HEALER_PAUSE'
            return 'HEALER_AVG'

        # --- СЛОЙ ЗАЩИТЫ ---
        if 'SHIELD' in decision or 'VELOCITY_GUARD' in decision:
            return 'SHIELD_ACTIVE'

        # --- БАЗОВАЯ РАБОТА ---
        # [WIRETAP] Ловим ситуации, когда есть активность, но интент остался NORMAL
        if (recovery_tag != "" or "HUNTER" in decision or "VETO" in decision):
            now = time.time()
            if now - getattr(self, '_last_intent_leak_log', 0) > 5.0:
                logging.getLogger('gabalog.grid_strategy').warning(
                    f"🕵️‍♂️ [INTENT_FALLTHROUGH] Неопределенный статус! "
                    f"Decision: {decision} | Tag: {recovery_tag} | Q: {q}"
                )
                self._last_intent_leak_log = now

        # --- БАЗОВАЯ РАБОТА ---
        return 'NORMAL'

    def on_trade(self, trade: dict):
        """
        [v9.30] Cyborg Sniper: Собирает сделки, считает VPIN 2.0 
        и МГНОВЕННО сносит сетку при всплеске скорости.
        """    
        
        # 1. Защита от пустого трейда
        size = float(trade.get('size', 0.0))
        if size <= 0:
            return
            
        # [v16.3] ГАРАНТИРОВАННАЯ НОРМАЛИЗАЦИЯ
        side = str(trade.get('side', '')).upper()
        now = time.time()
        self.last_trade_ts = now

        # --- БЛОК 1: ЗАМЕР СКОРОСТИ (VELOCITY TAPE) ---
        self.trade_tape.append((now, size))
        
        # Очищаем старые сделки (вышедшие за окно 60 сек)
        # ИСПРАВЛЕНО: Читаем из self.config, а не из self
        v_window = getattr(self.config, 'vpin_velocity_window_sec', 60.0)
        cutoff_time = now - v_window
        
        while self.trade_tape and self.trade_tape[0][0] < cutoff_time:
            self.trade_tape.popleft()
            
        # Считаем текущую скорость рынка (контракты в секунду)
        if len(self.trade_tape) > 1:
            real_window = now - self.trade_tape[0][0]
            # [v9.56] FLOOR PROTECTION: Окно замера не может быть меньше 0.5 сек.
            effective_window = max(0.5, real_window)
            
            total_tape_vol = sum(s for _, s in self.trade_tape)
            self.current_market_velocity = total_tape_vol / effective_window
        else:
            self.current_market_velocity = 0

        # --- [PHYSICS PULL] ЭКСТРЕННАЯ ОТМЕНА СЕТКИ ---
        # Детекция сквиза строится строго по физике (Скорость BTC и Рассинхрон Оракула)
        btc_vel = getattr(self, '_last_btc_velocity', 0.0)
        vel_thr = getattr(self.config, 'btc_vel_stress_threshold', 40.0)
        
        eff_delta = getattr(self, '_last_effective_delta', 0.0)
        oracle_drift_thr = getattr(self.config, 'oracle_drift_threshold', 0.004)
        _is_oracle_drifting = abs(eff_delta) > oracle_drift_thr

        if btc_vel > vel_thr:
            self._trigger_emergency_pull(
                decision_key="PHYSICS_PULL",
                reason=f"BTC_Speed: {btc_vel:.1f}$/s"
            )

        # ═══════════════════════════════════════════════════════
        # [CVD OBSERVER v1.0] — пассивный сенсор, не влияет на торговлю
        # Oracle-Relative CVD: считаем поток ЗА или ПРОТИВ FV
        # ═══════════════════════════════════════════════════════
        _cvd_fv = getattr(self, '_last_fv_for_cvd', 0.5)  # FV последнего тика

        # Определяем ожидаемую сторону по Oracle
        # Если FV > 0.5 — рынок должен покупать YES (BUY)
        # Если FV < 0.5 — рынок должен покупать NO (SELL)
        _expected_buy = _cvd_fv > 0.5

        # YES покупка при FV < 0.5 — поток ПРОТИВ Oracle (кто-то ставит против тренда)
        # YES покупка при FV > 0.5 — поток С Oracle (покупают то что Oracle рекомендует)
        # NO покупка при FV < 0.5 — поток С Oracle
        # NO покупка при FV > 0.5 — поток ПРОТИВ Oracle

        if side in ['BUY', 'LONG', 'YES']:
            self._cvd_raw += size
            _is_with_oracle = (_cvd_fv >= 0.52)  # YES поток совпадает с Oracle если FV > 0.5
        else:  # NO, SELL
            self._cvd_raw -= size
            _is_with_oracle = (_cvd_fv <= 0.48)   # NO поток совпадает с Oracle если FV < 0.5

        # CVD oracle-relative: поток В СТОРОНУ FV = позитив, ПРОТИВ = негатив
        if _is_with_oracle:
            self._cvd_oracle += size   # поток совпадает с направлением FV — норма
        else:
            self._cvd_oracle -= size   # поток ПРОТИВ FV — потенциальная токсичность

        # [FSM v2.4] Fast window (cvd_fast_window_sec, по умолчанию 6 сек) — для TORPEDO
        self._cvd_tape.append((now, size, _is_with_oracle))
        cvd_window = getattr(self.config, 'cvd_fast_window_sec', 6.0)
        cvd_cutoff = now - cvd_window
        while self._cvd_tape and self._cvd_tape[0][0] < cvd_cutoff:
            old_ts, old_sz, old_with = self._cvd_tape.popleft()
            if old_with:
                self._cvd_window_vol -= old_sz
            else:
                self._cvd_window_vol += old_sz

        # [FSM v2.4] Slow window (cvd_slow_window_sec, по умолчанию 45 сек) — для DIR
        _cvd_slow_window     = getattr(self.config, 'cvd_slow_window_sec', 45.0)
        _cvd_slow_min_trades = getattr(self.config, 'cvd_slow_min_trades', 6)
        self._cvd_slow_tape.append((now, size, _is_with_oracle))
        _slow_cutoff = now - _cvd_slow_window
        while self._cvd_slow_tape and self._cvd_slow_tape[0][0] < _slow_cutoff:
            self._cvd_slow_tape.popleft()
        if len(self._cvd_slow_tape) >= _cvd_slow_min_trades:
            _slow_oracle = sum(sz if w else -sz for _, sz, w in self._cvd_slow_tape)
            _slow_raw    = sum(sz for _, sz, _ in self._cvd_slow_tape)
            self._cvd_slow_signal = max(-1.0, min(1.0, _slow_oracle / max(1.0, _slow_raw)))
        else:
            self._cvd_slow_signal = None  # недостаточно трейдов — невалиден

        # Нормированный сигнал [-1.0 .. +1.0]
        # +1.0 = весь поток идёт В направлении FV (норма, тренд)
        # -1.0 = весь поток идёт ПРОТИВ FV (потенциальный арбитраж)
        # Считаем signal только из скользящего окна, не из глобального накопителя
        _cvd_window_oracle = sum(
            sz if with_oracle else -sz 
            for _, sz, with_oracle in self._cvd_tape
        )
        _cvd_window_raw = sum(sz for _, sz, _ in self._cvd_tape)
        _cvd_signal = _cvd_window_oracle / max(1.0, _cvd_window_raw)
        _cvd_signal = max(-1.0, min(1.0, _cvd_signal))
        self._cvd_fast_signal = _cvd_signal  # [FSM v2.4] fast alias

        # Токсичность: поток сильно против FV + быстрый рынок
        _cvd_toxic_signal = max(0.0, -_cvd_signal)  # только отрицательная часть
        _cvd_velocity_factor = min(1.0, self.current_market_velocity / max(1.0, getattr(self.config, 'vpin_bucket_min', 1200.0) / 60.0))
        _cvd_toxicity = _cvd_toxic_signal * _cvd_velocity_factor

       # Счётчик streak — decay вместо hard reset
        toxic_thr = getattr(self.config, 'cvd_streak_toxic_threshold', 0.5)
        _streak_decay = getattr(self.config, 'streak_decay_rate', 3)
        if _cvd_toxicity > toxic_thr:
            self._cvd_toxic_streak += 1
        else:
            self._cvd_toxic_streak = max(0, self._cvd_toxic_streak - _streak_decay)

        self._cvd_signal_last = _cvd_signal  # [FIX] сохраняем CVD для on_fill и других модулей
        _momentum = 0.0  # инициализация до Torpedo Pull (реальное значение считается в Momentum Veto блоке ниже)
        _torpedo_pull_thr = getattr(self.config, 'torpedo_pull_streak', 25)
        _open_q_now = getattr(self, '_last_open_q', 0)

        if self._cvd_toxic_streak >= _torpedo_pull_thr and abs(_open_q_now) > 0:
            _heavy_side = 'YES' if (_open_q_now > 0 and _cvd_signal < -0.40) else \
                          'NO'  if (_open_q_now < 0 and _cvd_signal > 0.40) else None

            if _heavy_side and hasattr(self, 'grid_manager'):
                _pull_cooldown = getattr(self.config, 'torpedo_pull_cooldown', 15.0)
                _last_pull = getattr(self, '_last_torpedo_pull_ts', 0.0)

                if now - _last_pull > _pull_cooldown:
                    _cancelled = self.grid_manager.cancel_side(_heavy_side)
                    if _cancelled and self.engine:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                loop.create_task(self.engine.batch_cancel(
                                    _cancelled,
                                    reasons={oid: "TORPEDO_SIDE_PULL" for oid in _cancelled}
                                ))
                        except RuntimeError:
                            pass
                    self._last_torpedo_pull_ts = now
                    logger.warning(
                        f"🌊 [TORPEDO_PULL] Отмена {_heavy_side} "
                        f"({len(_cancelled) if _cancelled else 0} ордеров) | "
                        f"Streak:{self._cvd_toxic_streak} | "
                        f"CVD:{_cvd_signal:+.3f} | "
                        f"Momentum:{_momentum:+.3f} | Q:{_open_q_now}"
                    )

        # --- [DUAL-CORE: MOMENTUM VETO расчёт] ---
        _now = time.time()
        self._cvd_history.append((_now, _cvd_signal))
        # Чистим историю старше 10 секунд
        self._cvd_history = [
            (t, v) for t, v in self._cvd_history if _now - t <= 10.0
        ]

        _momentum_window = getattr(self.config, 'cvd_momentum_window', 3.0)
        _veto_thr        = getattr(self.config, 'cvd_momentum_veto_thr', -0.25)
        _veto_cooldown   = getattr(self.config, 'cvd_veto_cooldown', 8.0)
        _hunter_thr      = getattr(self.config, 'hunter_imb_threshold', 15)
        _open_q_now      = getattr(self, '_last_open_q', 0)

        _momentum = 0.0
        for _hist_ts, _hist_val in reversed(self._cvd_history[:-1]):
            if _now - _hist_ts >= _momentum_window - 0.5:
                _dt = max(0.1, _now - _hist_ts)
                _momentum = (_cvd_signal - _hist_val) / _dt
                break

        _cooldown_ok = (_now - self._cvd_veto_ts) > _veto_cooldown
        _q_at_risk   = abs(_open_q_now) >= _hunter_thr

        if _momentum < _veto_thr and _cooldown_ok and _q_at_risk:
            self._cvd_veto_active = True
            self._cvd_veto_ts     = _now
        elif (_now - self._cvd_veto_ts) > _veto_cooldown:
            self._cvd_veto_active = False
        # ------------------------------------------------

        # [MARKET REGIME FSM v2.4]
        _regime_now     = self._market_regime
        _regime_ts      = self._regime_entered_ts
        _time_in_regime = now - _regime_ts

        _torpedo_momentum_thr = getattr(self.config, 'regime_torpedo_momentum_thr', 0.20)
        _dir_slow_thr         = getattr(self.config, 'regime_dir_slow_cvd_thr', 0.35)
        _dir_momentum_max     = getattr(self.config, 'regime_dir_momentum_max', 0.08)
        _dir_min_streak       = getattr(self.config, 'regime_dir_min_streak', 15)
        _torpedo_lock         = getattr(self.config, 'regime_torpedo_lock_sec', 3.0)
        _recovery_timeout = getattr(self.config, 'regime_recovery_timeout_sec', 8.0)
        _abs_momentum         = abs(_momentum)
        _new_regime           = _regime_now

        if _regime_now == 'NEUTRAL':
            if _abs_momentum > _torpedo_momentum_thr or btc_vel > vel_thr * 0.6:
                _new_regime = 'TORPEDO'
            elif (self._cvd_slow_signal is not None and
                  abs(self._cvd_slow_signal) > _dir_slow_thr and
                  _abs_momentum < _dir_momentum_max and
                  self._cvd_toxic_streak > _dir_min_streak):
                _new_regime = 'DIR'

        elif _regime_now == 'DIR':
            if _abs_momentum > _torpedo_momentum_thr or btc_vel > vel_thr * 0.6:
                _new_regime = 'TORPEDO'
            elif (self._cvd_slow_signal is not None and
                  abs(self._cvd_slow_signal) < 0.20 and
                  self._cvd_toxic_streak < 5):
                _new_regime = 'NEUTRAL'

        elif _regime_now == 'TORPEDO':
            if _abs_momentum > _torpedo_momentum_thr or btc_vel > vel_thr * 0.6:
                pass  # остаёмся, lock не сбрасываем
            elif _time_in_regime >= _torpedo_lock and _abs_momentum < 0.10:
                _new_regime = 'RECOVERY'

        elif _regime_now == 'RECOVERY':
            if _abs_momentum > _torpedo_momentum_thr:
                _new_regime = 'TORPEDO'
            elif _abs_momentum < 0.10 and _time_in_regime >= _torpedo_lock:
                _new_regime = 'NEUTRAL'  # импульс закончился
            elif _time_in_regime >= _recovery_timeout:
                _new_regime = 'NEUTRAL'

        if _new_regime != _regime_now:
            # [POST-TORPEDO COOLDOWN 2026-05-13] Mark transition out of
            # TORPEDO/RECOVERY so _run_hard_veto can suppress quoting for a
            # cooldown window. Forensics: 66% of bot-control epochs touched
            # TORPEDO and bled $-148. The bot quickly resumed quoting after
            # regime exit while the book was still unstable.
            if _regime_now in ('TORPEDO', 'RECOVERY') and _new_regime == 'NEUTRAL':
                self._last_torpedo_exit_ts = now
            self._market_regime     = _new_regime
            self._regime_entered_ts = now

        # Логируем раз в 3 секунды для парсера
        if now - self._cvd_last_log_ts > 3:
            logger.info(
                f"📡 [CVD_OBSERVER] "
                f"Signal:{_cvd_signal:+.3f} | "
                f"Toxic:{_cvd_toxicity:.3f} | "
                f"Raw_CVD:{self._cvd_raw:+.1f} | "
                f"Oracle_CVD:{self._cvd_oracle:+.1f} | "
                f"Vol_Vel:{self.current_market_velocity:.1f} | "  # Переименовали, чтобы не путать
                f"Momentum:{_momentum:+.3f} | "                  # ДОБАВИЛИ CVD Моментум
                f"FV:{_cvd_fv:.3f} | "
                f"Stress:{getattr(self, '_smooth_stress', 0.0):.3f} | "
                f"Streak:{self._cvd_toxic_streak} | "
                f"Regime:{self._market_regime} | "
                f"FastCVD:{self._cvd_fast_signal:+.3f} | "
                f"SlowCVD:{f'{self._cvd_slow_signal:+.3f}' if self._cvd_slow_signal is not None else 'N/A'}"
            )
            self._cvd_last_log_ts = now
        # ═══════════════════════════════════════════════════════

        # --- БЛОК 2: ДЫШАЩИЙ ЦИЛИНДР (АДАПТИВНЫЙ РАЗМЕР ВЕДРА) ---
        v_target = getattr(self.config, 'vpin_target_sec', 10.0)
        dynamic_target_vol = self.current_market_velocity * v_target
        
        # Было: target_vol = max(self.vpin_bucket_min, min(dynamic_target_vol, self.vpin_bucket_max))
        v_min = getattr(self, 'vpin_bucket_min', getattr(self.config, 'vpin_bucket_min', 1200.0))
        v_max = getattr(self, 'vpin_bucket_max', getattr(self.config, 'vpin_bucket_max', 2000.0))
        target_vol = max(v_min, min(dynamic_target_vol, v_max))

        # --- БЛОК 3: НАПОЛНЕНИЕ ВЕДРА ---
        self.current_bucket['total_vol'] += size
        # [v16.3] Расширенное определение покупки
        if side in ['BUY', 'LONG', 'YES']:
            self.current_bucket['buy_vol'] += size
            
        current_vol = self.current_bucket['total_vol']
        elapsed_time = now - self.current_bucket['start_ts']
        
        # [DEBUG]: Визуальный контроль наполнения раз в 10 сделок
        # t_total = getattr(self, '_trade_received_count', 0) + 1
        # s elf._trade_received_count = t_total
        # if t_total % 10 == 0:
            # logger.info(f"📊 [VPIN_DEBUG] Feed active. Bucket: {current_vol:.1f}/{target_vol:.1f} | Side: {side}")

        # Условие закрытия: ведро переполнено ИЛИ прошло слишком много времени (защита от застоя)
        vol_reached = current_vol >= target_vol
        time_reached = elapsed_time >= (v_target * 2.0)
        is_significant = current_vol >= (target_vol * 0.2)
        
        # --- БЛОК 4: АНАЛИЗ И ЗАКРЫТИЕ ВЕДРА ---
        if vol_reached or (time_reached and is_significant):
            b_vol = self.current_bucket['buy_vol']
            s_vol = current_vol - b_vol
            b_pct = (b_vol / current_vol * 100) if current_vol > 0 else 50.0
            
            skew_side = "BUY 🟢" if b_pct >= 60 else "SELL 🔴" if b_pct <= 40 else "NEUTRAL ⚪"
            
            logger.info(
                f"🪣 [VPIN BUCKET] Закрыто ({elapsed_time:.1f}s) | "
                f"Target: {target_vol:.1f} | Факт: {current_vol:.1f} | "
                f"Перекос: {skew_side} ({b_pct:.1f}%) | B/S: {b_vol:.1f}/{s_vol:.1f}"
            )
            
            # Сохраняем копию и обнуляем
            self.vpin_buckets.append(self.current_bucket.copy())
            self.current_bucket = {'buy_vol': 0.0, 'total_vol': 0.0, 'start_ts': now}
            
            # --- БЛОК 5: ПЕРЕСЧЕТ ОБЩЕГО МАКРО-VPIN ---
            # Теперь окно памяти (2 или 3) берется из конфига, который обновил on_tick
            memory_window = getattr(self.config, 'vpin_window_buckets', 3)
            
            if len(self.vpin_buckets) < memory_window:
                self.current_vpin = 0.50
            else:
                # Если накопили больше, чем нужно (например, при переходе с 3 на 2 ведра)
                # Отрезаем лишнее, чтобы VPIN стал "быстрее"
                while len(self.vpin_buckets) > memory_window:
                    self.vpin_buckets.popleft()
                
                total_buy = sum(b.get('buy_vol', 0.0) for b in self.vpin_buckets)
                total_macro_vol = sum(b.get('total_vol', 0.0) for b in self.vpin_buckets)
                
                raw_vpin = total_buy / total_macro_vol if total_macro_vol > 0 else 0.50
                
                # Внедряем DECAY (Устаревание памяти)
                time_since_last_bucket = now - (self.vpin_buckets[-1]['start_ts'])
                # [v14.7.5] МОДУЛЬ 8: STICKY VPIN
                # Нам нужно время, чтобы посчитать распад.
                # Берем прогресс раунда t_f (1.0 -> 0.0)
                t_rem_vpin = self.last_telemetry.time_remaining if hasattr(self, 'last_telemetry') else 900.0
                current_t_f = max(0.0, min(1.0, t_rem_vpin / self.config.market_duration_sec))
                
                base_decay = getattr(self.config, 'vpin_decay_sec', 10.0)
                # В конце раунда (t_f -> 0) память о панике вырастает до 60 секунд
                self._vpin_decay_actual = base_decay + (50.0 * (1.0 - current_t_f)) 

                if time_since_last_bucket > self._vpin_decay_actual:
                    decay_factor = min(1.0, (time_since_last_bucket - self._vpin_decay_actual) / 30.0)
                    self.current_vpin = raw_vpin * (1 - decay_factor) + 0.50 * decay_factor
                else:
                    self.current_vpin = raw_vpin
                
                if self.current_vpin >= 0.80 or self.current_vpin <= 0.20:
                    logger.info(f"☢️ [VPIN MM] Пульс: {self.current_vpin:.3f}")

    def _trigger_emergency_pull(self, decision_key: str, reason: str):
        import asyncio
        
        oids = self.grid_manager.cancel_all()
        
        if oids and self.engine:
            # БЕЗОПАСНЫЙ ЗАПУСК: получаем loop или создаем новый, если мы не в loop'е
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.engine.batch_cancel(
                        oids, reasons={oid: f"SNIPER_{decision_key}" for oid in oids}
                    ))
                else:
                    # Если loop не запущен (редко), используем фолбэк
                    asyncio.run_coroutine_threadsafe(self.engine.batch_cancel(oids), loop)
            except RuntimeError:
                # Критический фолбэк для синхронных коллбэков
                pass
            
            self.grid_manager.clear_all()
            logger.warning(f"⚡ [ANTI-SNIPE] Сетка уничтожена! ({len(oids)} шт). Причина: {reason}")


    # ------------------------------------------------------------------
    # Event callbacks
    # ------------------------------------------------------------------

    def record_api_request(self, count: int = 1) -> None:
        """Record API request(s) for rate monitoring."""
        now = time.time()
        self._api_requests_total += count
        self._api_requests_window.append((now, count))
        # Keep only last 60 seconds
        cutoff = now - 60.0
        self._api_requests_window = [(t, c) for t, c in self._api_requests_window if t >= cutoff]

    @property
    def api_requests_per_min(self) -> int:
        """Requests in last 60 seconds."""
        cutoff = time.time() - 60.0
        return sum(c for t, c in self._api_requests_window if t >= cutoff)

    def on_fill(self, fill_data: dict) -> None:
        try:
            """
            [v11.66-PRO] Синхронный учет инвентаря + Полное логирование для Dashboard.
            """
            self._total_fills += 1
            self._last_fill_ts = time.time() # Таймер для Hunter-а
            order_id = fill_data['order_id']
            side = fill_data['side']
            size = int(round(float(fill_data['size'])))
            if size <= 0: return

            # [v2.6] market_id из fill_data — надёжнее чем _c_mkt при старте рынка
            if fill_data.get('market_id'):
                self._c_mkt = fill_data['market_id']

            price = fill_data['price']
            is_taker = fill_data.get('is_taker', False)
            is_sell = fill_data.get('is_sell', False)

            if is_sell:
                # --- БЛОК ПРОДАЖИ (Recycling) ---
                if side == 'YES' and self.position.total_yes > 0:
                    avg = self.position.yes_cost / max(1, self.position.total_yes)
                    self.position.realized_ctf_pnl += (price - avg) * size
                    self.position.yes_shares = max(0, self.position.yes_shares - size)
                    self.position.total_yes = max(0, self.position.total_yes - size)
                    self.position.yes_cost = max(0.0, self.position.yes_cost - avg * size)
                elif side == 'NO' and self.position.total_no > 0:
                    avg = self.position.no_cost / max(1, self.position.total_no)
                    self.position.realized_ctf_pnl += (price - avg) * size
                    self.position.no_shares = max(0, self.position.no_shares - size)
                    self.position.total_no = max(0, self.position.total_no - size)
                    self.position.no_cost = max(0.0, self.position.no_cost - avg * size)
                
                # [!] Генерируем событие продажи для Dashboard
                _pending = self.grid_manager.pending_orders.get(order_id)
                _intent = _pending.intent if _pending else getattr(self, '_last_intent_tag', 'UNKNOWN')
                self._emit_event('sell_fill', side, price, size, intent=_intent)
            else:
                # [v2.6 TOXIC_FILL] Intent из ордера (до on_fill очистит pending)
                _pending_pre = self.grid_manager.pending_orders.get(order_id)
                _intent_pre  = _pending_pre.intent if _pending_pre else getattr(self, '_last_intent_tag', 'UNKNOWN')
                # [v3.3] полная attribution на момент создания
                _regime_at_intent_pre = _pending_pre.regime_at_creation if _pending_pre else '?'
                _fv_at_intent_pre = _pending_pre.fv_at_creation if _pending_pre else 0.5
                _ps_at_intent_pre = _pending_pre.pair_state_at_creation if _pending_pre else '?'
                _im_at_intent_pre = _pending_pre.intent_mode_at_creation if _pending_pre else '?'
                _spr_at_intent_pre = _pending_pre.spread_at_creation if _pending_pre else 0.0
                _fill_age_pre = (time.time() - _pending_pre.timestamp) if _pending_pre else 0.0
                # Снапшот ДО обновления позиции
                _fv_snap    = getattr(self, '_last_fv_for_cvd', 0.5)
                _hc_snap    = getattr(self, '_dynamic_hard_cutoff', 1)
                _y_avg_pre  = self.position.yes_cost / max(1, self.position.total_yes)
                _n_avg_pre  = self.position.no_cost  / max(1, self.position.total_no)
                _q_pre      = self.position.yes_shares - self.position.no_shares
                _ps_pre     = (_y_avg_pre + (1.0 - _fv_snap)) if _q_pre > 0 else \
                              (_n_avg_pre + _fv_snap)          if _q_pre < 0 else 1.0

                if side == 'YES':
                    self.position.yes_shares += size
                    self.position.total_yes += size 
                    self.position.yes_in_flight = max(0, self.position.yes_in_flight - size)
                    self.position.yes_cost += price * size
                else:
                    self.position.no_shares += size
                    self.position.total_no += size
                    self.position.no_in_flight = max(0, self.position.no_in_flight - size)
                    self.position.no_cost += price * size

                # [v2.10 PAIR_STATE] Сохраняем контекст последнего fill для FSM
                # _last_fill_side — какая нога только что filled
                # _last_fill_increased_q — увеличил ли fill exposure (opening) или уменьшил (closing)
                self._last_fill_side = side
                _new_q_post_fill = self.position.yes_shares - self.position.no_shares
                self._last_fill_increased_q = abs(_new_q_post_fill) > abs(_q_pre)

                # [v2.6 TOXIC_FILL] Снапшот ПОСЛЕ — логируем только если PS пробил 1.000
                _y_avg_post = self.position.yes_cost / max(1, self.position.total_yes)
                _n_avg_post = self.position.no_cost  / max(1, self.position.total_no)
                _q_post     = self.position.yes_shares - self.position.no_shares
                _ps_post    = (_y_avg_post + (1.0 - _fv_snap)) if _q_post > 0 else \
                              (_n_avg_post + _fv_snap)           if _q_post < 0 else 1.0

                if _ps_post > 1.000 or _ps_pre > 1.000:
                    if _ps_post < _ps_pre:
                        # Этот fill улучшил ситуацию
                        _tag = "TOXIC_HEAL"
                    elif _ps_post > _ps_pre:
                        # Этот fill углубил токсичность
                        _tag = "TOXIC_ORIGIN"
                    else:
                        # PS не изменился (закрывающая нога, Q уменьшился но avg не изменился)
                        _tag = "TOXIC_FILL"
                    logging.getLogger('gabalog.grid_strategy').warning(
                        f"☣️📊 [{_tag}] "
                        f"Side:{side} {size}@{price:.3f} | "
                        f"PS_before:{_ps_pre:.4f} → PS_after:{_ps_post:.4f} | "
                        f"Y_avg:{_y_avg_pre:.3f}→{_y_avg_post:.3f} "
                        f"N_avg:{_n_avg_pre:.3f}→{_n_avg_post:.3f} | "
                        f"Q:{_q_pre}→{_q_post} | "
                        f"FV:{_fv_snap:.3f} | "
                        f"Intent:{_intent_pre} | "
                        f"Regime:{getattr(self, '_market_regime', '?')} | "
                        f"RegAtIntent:{_regime_at_intent_pre} | "
                        f"PSAtIntent:{_ps_at_intent_pre} | "
                        f"IMAtIntent:{_im_at_intent_pre} | "
                        f"FVAtIntent:{_fv_at_intent_pre:.3f} | "
                        f"SprAtIntent:{_spr_at_intent_pre:.3f} | "
                        f"FillAge:{_fill_age_pre:.1f}s | "
                        f"IntMode:{getattr(self, '_intent_mode', '?')} | "
                        f"InvL:{round(abs(_q_post) / max(1, _hc_snap), 2)} | "
                        f"T:{getattr(self, '_last_t_rem', 0):.0f}s"
                        f"Mkt:{getattr(self, '_c_mkt', '?')} | "
                    )

                # [!] Генерируем событие покупки для Dashboard
                _pending = self.grid_manager.pending_orders.get(order_id)
                _intent = _pending.intent if _pending else getattr(self, '_last_intent_tag', 'UNKNOWN')
                # [v3.3] полная attribution на момент создания (для FILL_CTX лога)
                _regime_at_intent = _pending.regime_at_creation if _pending else '?'
                _fv_at_intent = _pending.fv_at_creation if _pending else 0.5
                _ps_at_intent = _pending.pair_state_at_creation if _pending else '?'
                _im_at_intent = _pending.intent_mode_at_creation if _pending else '?'
                _spr_at_intent = _pending.spread_at_creation if _pending else 0.0
                _fill_age = (time.time() - _pending.timestamp) if _pending else 0.0
                self._emit_event('fill', side, price, size, is_taker=is_taker, intent=_intent)
                # [v3.2] regime_at_intent_creation — корректная атрибуция, в отличие от Regime который текущий
                _regime_at_intent = _pending.regime_at_creation if _pending else '?'

                # [FILL CONTEXT LOG] Расширенный контекст для парсера
                # СТАЛО:
                _fv = getattr(self, '_last_fv_for_cvd', 0.5)
                _stress = getattr(self, '_smooth_stress', 0.0)
                _open_q = getattr(self, '_last_open_q', 0)
                _t_rem = getattr(self, '_last_t_rem', 0.0)
                _gamma = getattr(self, '_last_gamma_dist', 0.0)
                _gamma_mode = 1 if getattr(self, '_last_gamma_maq_active', False) else 0
                # [PATCH] Новые поля контекста
                _cvd = getattr(self, '_cvd_signal_last', 0.0)
                _streak = getattr(self, '_cvd_toxic_streak', 0)
                _hc = getattr(self, '_dynamic_hard_cutoff', 0)
                _inv_load = round(abs(_open_q) / max(1, _hc), 2) if _hc > 0 else 0.0
                _inv_ps = getattr(self, '_last_inv_ps', 0.0)  # нужно сохранять в on_tick
                _pen = getattr(self, '_last_penalty', 0.0)    # нужно сохранять в on_tick
                _space_pct = round((1.0 - abs(_open_q) / max(1, _hc)) * 100) if _hc > 0 else 0
                self._log_block_state(
                    'SPACE_LOW', _space_pct < 15,
                    f"Space:{_space_pct}% | OpenQ:{_open_q} | HC:{_hc} | CVD:{getattr(self,'_cvd_signal_last',0.0):+.3f}"
                )
                # СТАЛО:
                logger.info(
                    f"📊 [FILL_CTX] {side} {size}@{price:.3f} | "
                    f"FV:{_fv:.3f} | T:{_t_rem:.0f}s | "
                    f"Gamma:${_gamma:.0f} | OpenQ:{_open_q} | "
                    f"Stress:{_stress:.2f} | Intent:{_intent} | "
                    f"GMode:{_gamma_mode} | "
                    f"CVD:{_cvd:+.3f} | Streak:{_streak} | Space:{_space_pct}% | "
                    f"InvL:{_inv_load:.2f} | InvPS:{_inv_ps:.3f} | Pen:{_pen:.3f} | "
                    f"IntMode:{getattr(self, '_intent_mode', '?')} | "
                    f"Regime:{getattr(self, '_market_regime', '?')} | "
                    f"RegAtIntent:{_regime_at_intent} | "
                    f"PSAtIntent:{_ps_at_intent} | "
                    f"IMAtIntent:{_im_at_intent} | "
                    f"FVAtIntent:{_fv_at_intent:.3f} | "
                    f"SprAtIntent:{_spr_at_intent:.3f} | "
                    f"FillAge:{_fill_age:.1f}s | "
                    f"FlowTox:{getattr(self, '_is_flow_toxic', False)} | "
                    f"Resist:{getattr(self, '_last_pf_resist', 0.0):.2f} | "
                    f"Mkt:{getattr(self, '_c_mkt', '?')} | "
                    f"Q:{_q_pre}→{_q_post} | "
                    f"Yavg:{_y_avg_pre:.3f}→{_y_avg_post:.3f} | "
                    f"Navg:{_n_avg_pre:.3f}→{_n_avg_post:.3f}"
                )

            self.grid_manager.on_fill(order_id, size, price)

            # --- MULTI-FILL GUARD (BURST PROTECTION) ---
            # Метод on_fill
            self._fills_this_tick += 1
            if self._fills_this_tick > getattr(self.config, 'max_fills_per_tick', 2):
                # Устанавливаем кулдаун на 3 тика (заморозка в on_tick)
                self._pre_pull_ticks_left = 3 
                self._trigger_emergency_pull("BURST_PROTECT", f"Fills per tick: {self._fills_this_tick}")

            
        except Exception as e:
            logging.getLogger('gabalog.grid_strategy').critical(f"💥 [MATH_ERROR] Ошибка в расчете инвентаря: {e}")
            # Мы не рейзим ошибку, чтобы бот не упал, но СНАЙПЕР увидит этот лог
            
        # Статистика Maker-объема
        if not is_taker:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            if today != self._volume_reset_date:
                self._maker_volume_usd = 0.0; self._maker_fills_count = 0; self._volume_reset_date = today
            self._maker_volume_usd += price * size
            self._maker_fills_count += 1

        # Fill at Peak detection: was this fill in the top 10% of recent price range?
        self._total_fills_tracked += 1
        if hasattr(self, '_price_history') and len(self._price_history) >= 3:
            recent_prices = [p for _, p in self._price_history]
            p_min, p_max = min(recent_prices), max(recent_prices)
            p_range = p_max - p_min
            if p_range > 0.005:  # meaningful range (>0.5¢)
                if side == 'YES' and price >= p_min + p_range * 0.90:
                    self._peak_fills += 1
                    self._peak_fill_cost += price * size
                elif side == 'NO' and (1.0 - price) >= (1.0 - p_max) + p_range * 0.90:
                    # NO expensive = YES cheap = bottom 10% of YES range
                    self._peak_fills += 1
                    self._peak_fill_cost += price * size

    def on_market_switch(self, _new_market: dict | None = None) -> None:
        """New market — reset all state."""

        # [v2.6] Сохраняем market_id до первого тика — нужен для TOXIC_FILL логов в on_fill
        if _new_market and isinstance(_new_market, str):
            self._c_mkt = _new_market
        elif _new_market and isinstance(_new_market, dict):
            self._c_mkt = _new_market.get('market', _new_market.get('slug', 'unknown'))

        # Сброс памяти защиты для нового рынка
        if hasattr(self, 'defense_core'):
            self.defense_core.reset()

        self._unified_stress_level = 0.0
        self._last_hunter_side = None    

        self._time_stop_fired = False
        self._last_strike_official_state = False # Гарантируем "слепоту" на старте
        self._current_oracle_weight = 0.7        # Обнуляем вес Оракула
        self._smooth_stress = 0.0                # Чистим память стресса
        self._pending_merge_size = 0
        self._pending_merge_ts = 0.0
        self._pending_merge_side = ""
        self._merge_state = 'IDLE'
        self.oracle_fade_yes = False
        self.oracle_fade_no = False
        self._last_decision = ""
        self._warmup_ended = False
        self._emergency_strike = None
        self.position.reset()

        # Добавить в конец __init__ И в on_market_switch:
        self._consensus_charge = 0.0        # Накопленный "заряд" (сек)
        self._consensus_confirmed = False   # Флаг капитуляции
        self._consensus_peak = 0.5          # Точка экстремума для замера отката
        self._last_consensus_ts = time.time()

        # --- [NEW] VPIN 2.0 RESET (v9.7) ---
        # Очищаем историю ведер и замеры скорости
        self.vpin_buckets.clear()
        self.trade_tape.clear()
        
        # Сбрасываем текущее ведро
        self.current_bucket = {'buy_vol': 0.0, 'total_vol': 0.0, 'start_ts': time.time()}
        
        # Возвращаем нейтральные значения
        self.current_vpin = 0.50
        self.current_market_velocity = 0.0
        
        # Сбрасываем таймер заморозки (на случай если рынок сменился во время фриза)
        self._freeze_until = 0
        # ------------------------------------
        self.last_telemetry = TickTelemetry()

        # [CVD OBSERVER] сброс на новый рынок
        self._cvd_raw = 0.0
        self._cvd_oracle = 0.0
        self._cvd_window_vol = 0.0
        self._cvd_tape = deque()
        self._cvd_last_log_ts = 0.0
        self._last_fv_for_cvd = 0.5
        self._cvd_signal_last  = 0.0
        self._cvd_toxic_streak = 0
        self._cvd_veto_active  = False
        self._cvd_veto_ts      = 0.0
        self._cvd_history      = []

        # [MARKET REGIME FSM v2.4] сброс на новый рынок
        self._market_regime     = 'NEUTRAL'
        self._regime_entered_ts = 0.0
        self._last_torpedo_exit_ts = 0.0
        self._cvd_fast_signal   = 0.0
        self._cvd_slow_signal   = None
        self._cvd_slow_tape     = deque()
        
        # Флаги экстренных действий
        self.recovery_attempts = 0
        self._session_pnl = 0.0
        self._session_peak_pnl = 0.0
        self._drawdown_stopped = False
        self._emergency_dump_fired = False

        # --- [v15] ED TRIAGE MATRIX RESET ---
        self._ed_level = 0
        self._ed_level_enter_ts = 0.0
        self._ed_q_history.clear()
        self._ed_survivor_lock_side = None
        self._ed_yellow_urgency = 0.0
        self._ed_last_maker_sell_ts = 0.0
        self._bankrupt_sides.clear()

        self._recycling_sell_active = False
        self._strike_warn_fired = False    
        self._is_panic_frozen = False 
        # [v14.7-CORE] Триаж-сброс
        self._triage_active_side = None
        self._triage_decision = "NONE"
        self._current_patience = 0
        # --- [NEW STATE TRACKERS] ---
        self._pre_pull_ticks_left = 0      # Заморозка после физического спайка (BTC_Vel / Oracle_Drift)
        self._fills_this_tick = 0          # Контроль залпового снайпинга
        self._toxic_position_ticks = 0     # Таймер гниения инвентаря
        self._is_dumping_in_flight = False # Защита от "Эффекта Гатлинга"
        self._last_dump_time = 0.0         # Кулдаун между ударами по рынку
        self._last_fill_ts = time.time()  # <--- ИНИЦИАЛИЗАЦИЯ ТАЙМЕРА
        # ----------------------------
        # [v14.7 Forensic] State Tracking
        self._last_intent = "NORMAL"
        self._last_expected_pnl = 0.0
        self._order_events.clear()

        # Значения предыдущего тика
        self._smooth_stress = 0.0
        self._prev_dyn_scale = 14.0

        self._last_veto_log_y = 0
        self._last_veto_log_n = 0
        self._last_lock_log_y = 0
        self._last_lock_log_n = 0
        self._last_guard_log = 0
        self._last_brain_lag_log = 0
        
        self._regime_history.clear()
        self._market_tape_log.clear()
        self._last_orderbook = {}
        self.paper_winner = None
        
        # [v11.64-ULTIMATE] Полный сброс всех счетчиков сессии
        self.position.reset()
        self.position.profit_merges_count = 0
        self.position.salvage_merges_count = 0
        self.position.session_merge_volume = 0.0
        
        self.session_stats = {'profit_merges': 0, 'salvage_merges': 0, 'total_volume': 0.0}
        self.grid_manager.clear_all()

        # [v14.6-CORE.1 FIX] Сброс персистентных состояний защиты для новой сессии
        self._bankrupt_sides = set()       # Снятие Survivor Lock карантина
        self._current_proj_ps = 0.0        # Очистка проектора Iron Gate
        self.defcon_risky_side = None      # Снятие блокировки стороны риска
        self._consensus_charge = 0.0       # Сброс заряда капитуляции
        self._consensus_confirmed = False  # Сброс статуса выхода
        self._is_panic_frozen = False      # Разморозка "Бункера"
        self._last_torpedo_pull_ts = 0.0
        self._block_state = {'HEALER_CVD': False, 'MIRROR_CVD': False, 'HUNTER_SLEEP': False, 'SPACE_LOW': False}

        if hasattr(self, '_market_start_time'):
            del self._market_start_time
        self._stable_ticks = 0


    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------

    def _check_risk_stop(self, market_data: dict) -> bool:
        """Check if drawdown or per-market stop triggered."""
        if self._drawdown_stopped:
            return True

        # Per-market P&L stop
        market_pnl = market_data.get('market_pnl', 0.0)
        if self.config.deposit > 0 and market_pnl < 0:
            roi = (market_pnl / self.config.deposit) * 100
            if roi <= self.config.market_pnl_stop_roi:
                self._drawdown_stopped = True
                return True

        return False

    def update_session_pnl(self, pnl: float) -> None:
        """Update session-level P&L for drawdown tracking."""
        self._session_pnl = pnl
        self._session_peak_pnl = max(self._session_peak_pnl, pnl)

        if self._session_peak_pnl > 0:
            dd = ((self._session_peak_pnl - pnl) / self._session_peak_pnl) * 100
            if dd >= self.config.drawdown_pct:
                self._drawdown_stopped = True

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def _check_recovery(self, market_data: dict, tel: TickTelemetry) -> OrderAction | None:
        """Check if recovery taker buy is needed."""
        # --- ВРЕМЕННО ОТКЛЮЧЕНО --- 
        # Taker-ордера бьют по Ask и гарантированно рушат Inv PS.
        # В новой версии Dynamic PS Ceiling мы выравниваем баланс строго
        # лимитками через усреднение, поэтому панические рыночные хеджи отменены.
        return None

    # ------------------------------------------------------------------
    # Regime Cascade (parent ↔ child)
    # ------------------------------------------------------------------

    def _read_parent_regime(self) -> tuple:
        """Read parent regime + delta from shared file. Returns ('FLAT', 0.0) on any failure."""
        import json as _json
        import time as _time

        _FALLBACK = ('FLAT', 0.0)

        # Cache for 2 seconds to avoid IO spam
        cache = getattr(self, '_parent_regime_cache', None)
        now = _time.time()
        if cache and now - cache[2] < 2.0:
            return (cache[0], cache[1])

        try:
            with open(self.config.regime_cascade_file, 'r') as f:
                data = _json.load(f)
            regime = data.get('regime', 'FLAT')
            delta = float(data.get('delta', 0.0))
            ts = data.get('ts', 0)
            # Stale check: ignore if older than 10 seconds
            if now - ts > 10.0:
                self._parent_regime_cache = ('FLAT', 0.0, now)
                return _FALLBACK
            self._parent_regime_cache = (regime, delta, now)
            return (regime, delta)
        except (FileNotFoundError, _json.JSONDecodeError, IOError, ValueError):
            self._parent_regime_cache = ('FLAT', 0.0, now)
            return _FALLBACK

    def _broadcast_regime(self, regime: str, price_delta: float) -> None:
        """Write own regime to shared file for child bots."""
        import json as _json
        import time as _time

        # Throttle: write at most every 1 second
        last_write = getattr(self, '_last_regime_broadcast', 0.0)
        now = _time.time()
        if now - last_write < 1.0:
            return

        try:
            with open(self.config.regime_broadcast_file, 'w') as f:
                _json.dump({'regime': regime, 'delta': round(price_delta, 4), 'ts': now}, f)
            self._last_regime_broadcast = now
        except IOError:
            pass

    # ------------------------------------------------------------------
    # Maker Inventory Recycling
    # ------------------------------------------------------------------

    def _check_recycling_sell(self, market_data: dict) -> OrderAction | None:
        # Max 1 active recycling sell at a time
        if getattr(self, '_recycling_sell_active', False):
            return None

        # --- НОВАЯ СВЯЗКА: UNIFIED STRESS + RECYCLE (Упреждающий сброс) ---
        active_util_threshold = self.config.recycling_utilization_threshold
        active_imb_threshold = self.config.recycling_imbalance_threshold
        
        # Читаем единый арбитр стресса (вместо старого VPIN/Defcon)
        unified_stress = getattr(self, '_unified_stress_level', 0.0)
        stress_panic = unified_stress > 0.70  # Порог шторма

        # Включается ТОЛЬКО во время сильного стресса
        if stress_panic:
            active_util_threshold *= 0.5  
            active_imb_threshold *= 0.4  

        # [ФИКС]: Считаем утилизацию по АКЦИЯМ, а не по доллару, чтобы дешевые ноги не обходили фильтр
        limit = getattr(self, '_dynamic_hard_cutoff', 350)
        share_utilization = 0.0
        if limit > 0:
            y_util = self.position.yes_shares / limit
            n_util = self.position.no_shares / limit
            share_utilization = max(y_util, n_util)
        else:
            # Фолбэк на доллары, если лимит отключен (0)
            share_utilization = self.position.total_cost / self.config.deposit if self.config.deposit > 0 else 0.0

        imb_pct = self.position.imbalance_pct

        # --- ЗАЩИТА 1: Объемный лок (ждем минимальный вес перед ресайклом) ---
        total_shares = self.position.yes_shares + self.position.no_shares
        min_lots = 2 if stress_panic else 4 
        if total_shares < (self.config.grid_lot_size * min_lots):
            return None

        # --- ЗАЩИТА 2: Если перекос критический, оставляем работу для Emergency Dump ---
        if self.config.emergency_dump_enabled and imb_pct >= self.config.emergency_dump_imb_pct:
            return None

        # Сравниваем утилизацию АКЦИЙ с порогом (а не доллары)
        if share_utilization < active_util_threshold and imb_pct < active_imb_threshold:
            return None

        # Determine heavy leg
        yes_s, no_s = self.position.yes_shares, self.position.no_shares
        if yes_s > no_s:
            heavy_side = 'YES'
            excess = yes_s - no_s
            heavy_shares = yes_s
            heavy_cost = self.position.yes_cost
            current_ask = market_data.get('yes_ask', 0)
        elif no_s > yes_s:
            heavy_side = 'NO'
            excess = no_s - yes_s
            heavy_shares = no_s
            heavy_cost = self.position.no_cost
            current_ask = market_data.get('no_ask', 0)
        else:
            return None  # balanced

        # Must have meaningful excess
        if excess < self.config.grid_lot_size:
            return None

        # Calculate sell price: SMART EXIT (Stop-Loss + Trailing Ask)
        if heavy_shares <= 0:
            return None
        avg_cost = heavy_cost / heavy_shares
        
        if current_ask <= 0:
            return None
            
        # --- КРИВАЯ ОТЧАЯНИЯ (Time-Weighted Loss Tolerance) ---
        time_rem = market_data.get('time_remaining_sec', self.config.market_duration_sec)
        time_ratio = max(0.0, time_rem / max(1.0, self.config.market_duration_sec))
        
        # progress идет от 0.0 (старт рынка) до 1.0 (конец рынка)
        progress = 1.0 - time_ratio 
        
        # На старте отдаем максимум 2 цента. В конце готовы слить в минус 35 центов.
        # Возводим progress в 3-ю степень, чтобы паника начиналась экспоненциально в самом конце
        dynamic_max_loss = 0.02 + (0.35 - 0.02) * (progress ** 3)
        
        # Рассчитываем порог
        min_sell_price = avg_cost - dynamic_max_loss
        min_sell_price = max(0.01, min_sell_price) # Не продаем дешевле 1 цента
        
        # Если текущий Ask хуже нашего порога отчаяния - просто ждем отскока.
        # Это защищает нас от выставления зависших лимиток глубоко в стакане.
        if current_ask < min_sell_price:
            
            import time as _time
            # Защита от спама в логах (пишем отказ только раз в 5 секунд)
            if _time.time() - getattr(self, '_last_recycle_skip_log', 0) > 5.0:
                logger.debug(f"💤 [RECYCLE WAIT] {heavy_side}: Ask {current_ask:.3f} < Min {min_sell_price:.3f} (Loss tol: {dynamic_max_loss:.3f})")
                self._last_recycle_skip_log = _time.time()
            return None
            
        # Если Ask вписывается в нашу терпимость к убыткам - бьем лимиткой прямо в него
        sell_price = current_ask
        # ------------------------------------------------------

        # Round to tick
        sell_price = round(sell_price, 2)

        # Don't sell above $0.99
        if sell_price >= 1.0:
            return None

        # Quantity: max 20% of excess, min lot_size
        sell_qty = max(self.config.grid_lot_size, int(excess * self.config.recycling_max_excess_pct))
        sell_qty = min(sell_qty, excess)  # never sell more than excess

        # Mark active
        self._recycling_sell_active = True

        logger.info(
            f"(avg_cost=${avg_cost:.3f}, ask=${current_ask:.3f}) | "
            f"Util={share_utilization*100:.0f}% Имб={imb_pct:.0f}%"
        )

        # Фиксируем сторону и время сброса для Churn Guard
        self._last_recycle_side = heavy_side
        self._last_recycle_ts = time.time()

        return OrderAction(
            action='place',
            side=f'SELL_{heavy_side}',
            price=sell_price,
            size=sell_qty,
            is_taker=False,
            reason="MAKER_RECYCLE",
        )

    # ------------------------------------------------------------------
    # Emergency Inventory Dump
    # ------------------------------------------------------------------

    def _check_emergency_dump(self, market_data: dict) -> OrderAction | None:
        """
        [ОБНОВЛЕНО] Экстренный сброс перекоса по рынку (Taker).
        Бьет в BID (чтобы гарантированно продать).
        Работает циклично, пока перекос не упадет ниже порога.
        """
        if not self.config.emergency_dump_enabled:
            return None

        # --- [NEW] АНТИ-СПАМ ДЛЯ БЛОКЧЕЙНА (Throttling) ---
        now = time.time()
        time_rem = market_data.get('time_remaining_sec', 0)
        # Ждем минимум 3 секунды между маркет-сбросами
        if now - getattr(self, '_last_dump_ts', 0) < 3.0:
            return None 

        # 2. Триггеры: Критический перекос, Сигнал от Оракула (DEFCON 1) или Переполнение (Full House)
        forced_dump = getattr(self, '_emergency_dump_fired', False)
        is_endgame_dump = time_rem < 120 
        q_abs = abs(self.position.q)
        
        # [v14.5-ELASTIC] Динамический порог активации: Safe Level + 2 лота буфера
        safe_floor = getattr(self.config, 'toxic_q_safe', 15)
        lot_size = getattr(self.config, 'grid_lot_size', 5)
        activation_threshold = safe_floor + (2 * lot_size)

        # Запрещаем автоматический дамп на малых объемах (защита PnL от микро-сливов)
        if q_abs < activation_threshold and not forced_dump and not is_endgame_dump:
            return None

        active_imb_threshold = 0.1 if is_endgame_dump else self.config.emergency_dump_imb_pct
        hard_imbalance = self.position.imbalance_pct >= active_imb_threshold
        
        # Заменяем старый Defcon на проверку Единого Стресса (> 0.85 это эквивалент жесткой паники)
        defcon_evacuation = getattr(self, '_unified_stress_level', 0.0) > 0.85
        
        if not (hard_imbalance or defcon_evacuation or forced_dump):
            return None

        # 3. Физика: Surrender Curve (v14-SHADOW)
        # Берем уже рассчитанное в on_tick значение, чтобы не дублировать код
        sell_mult = getattr(self, '_current_dump_mult', 0.5)

        # 4. Анализ инвентаря и выбор ноги
        yes_s, no_s = self.position.yes_shares, self.position.no_shares
        limit = getattr(self, '_dynamic_hard_cutoff', 350)
        slippage = getattr(self.config, 'emergency_dump_slippage', 0.03)

        if yes_s > no_s:
            # ТЯЖЕЛАЯ НОГА: YES
            heavy_side = 'YES'
            excess = yes_s - no_s
            bid_price = market_data.get('yes_bid', 0)
            if bid_price <= 0: return None
            
            # Если пробили Hard Limit — льем всё, что выше него. Иначе — порцию по кривой.
            if limit > 0 and yes_s > limit:
                raw_sell = (yes_s - limit)
            else:
                raw_sell = int(excess * sell_mult)
            
            target_price = max(0.01, bid_price - slippage)
        else:
            # ТЯЖЕЛАЯ НОГА: NO
            heavy_side = 'NO'
            excess = no_s - yes_s
            bid_price = market_data.get('no_bid', 0)
            if bid_price <= 0: return None
            
            if limit > 0 and no_s > limit:
                raw_sell = (no_s - limit)
            else:
                raw_sell = int(excess * sell_mult)
            
            # Для NO используем тот же slippage
            target_price = max(0.01, bid_price - slippage)

        # 5. Финальные проверки объема
        if excess < self.config.grid_lot_size: return None
        
        # Volume Lock: не дампить "пыль", ждем веса хотя бы в 3 лота
        total_shares = yes_s + no_s
        if total_shares < (self.config.grid_lot_size * 3) and not forced_dump:
            return None

        sell_qty = max(self.config.grid_lot_size, raw_sell)
        if sell_qty <= 0: return None

        # 6. Финализация
        self._last_dump_ts = now
        if forced_dump: self._emergency_dump_fired = False
        
        # [v14.6-CORE] Survivor Lock: Помечаем сторону как Банкрот
        self._bankrupt_sides.add(heavy_side)

        log_reason = "FULL_HOUSE" if forced_dump else ("DEFCON" if defcon_evacuation else "IMBALANCE")
        logging.warning(
            f"💥 [EMERGENCY_DUMP] {log_reason} | {heavy_side} excess={excess} → "
            f"selling {sell_qty} (mult:{sell_mult:.2f}) @ bid ${target_price:.3f}"
        )
        
        return OrderAction(
            action='place',
            side=f'SELL_{heavy_side}',  
            price=target_price,
            size=sell_qty,
            is_taker=True,
            reason="EMERGENCY_DUMP",
        )

    def _calculate_max_safe_price(self, side: str, qty: int, max_gate: float, is_hunter: bool = False) -> float:
        q = self.position.q
        ob = getattr(self, '_last_orderbook', {})
        mkt_y_ask = ob.get('yes_ask', 0.5)
        mkt_n_ask = ob.get('no_ask', 0.5)
        
        # --- [v15.1] RISK-DRIVEN PROFIT BUFFER ---
        real_pnl = max(0.0, self.position.realized_ctf_pnl)
        risk_allowance = 0.035 if is_hunter else 0.0
        profit_buffer = min(0.05, (real_pnl / max(1, qty * 2)) + risk_allowance)
        
        # dynamic_gate — это наш "идеальный бакс" (например, 0.99 + буфер)
        dynamic_gate = max_gate + profit_buffer

        # 1. Реальные средние цены из Shadow Book
        y_avg = (self.position.yes_cost / max(1, self.position.total_yes)) if self.position.total_yes > 0 else 0.0
        n_avg = (self.position.no_cost / max(1, self.position.total_no)) if self.position.total_no > 0 else 0.0

        # 2. РАСЧЕТ ЛЮФТА (Чтобы не было паралича)
        # Если рынок ушел далеко, мы разрешаем переплатить сверху бакса, но строго ограниченно
        # Например: разрешаем переплату до 1.02, если инвентарь горит.
        abs_max_pair_cost = getattr(self.config, 'abs_max_pair_cost', 1.02)
        emergency_gate = max(dynamic_gate, abs_max_pair_cost)

        if side == 'YES':
            # КЛЮЧЕВОЙ МОМЕНТ: Какой "якорь" берем для расчета?
            if q < -2: # У нас перекос в NO (нужно купить YES)
                # Если мы уже купили NO дорого, мы ДОЛЖНЫ это учитывать
                # Используем среднюю цену накопленного хвоста NO как базу
                reference_n_price = n_avg if n_avg > 0 else mkt_n_ask
                
                # Если мы Охотник, мы берем emergency_gate (с люфтом), 
                # если NORMAL — строго dynamic_gate.
                gate = emergency_gate if is_hunter else dynamic_gate
                safe_price = gate - reference_n_price
            else:
                # Мы открываем новую позицию (Q >= 0)
                # Тут якорем выступает текущий рынок (ask NO)
                safe_price = dynamic_gate - mkt_n_ask
                
            return max(0.01, round(safe_price, 3))
            
        elif side == 'NO':
            if q > 2: # У нас перекос в YES (нужно купить NO)
                reference_y_price = y_avg if y_avg > 0 else mkt_y_ask
                gate = emergency_gate if is_hunter else dynamic_gate
                safe_price = gate - reference_y_price
            else:
                safe_price = dynamic_gate - mkt_y_ask
                
            return max(0.01, round(safe_price, 3))
            
        return 0.0

    def _log_decision(self, key: str, message: str):
        """[v11.56] Throttled decision logging to prevent flicker spam."""
        now = time.time()
        if now - self._log_cooldowns.get(key, 0) > 5.0:
            logging.getLogger('gabalog.grid_strategy').warning(message)
            self._log_cooldowns[key] = now

    def _std_ctx(self) -> str:
        """Универсальный контекстный суффикс для всех 🪦 логов."""
        return (
            f"Q:{getattr(self, '_last_open_q', 0)} | "
            f"CVD:{getattr(self, '_cvd_signal_last', 0.0):+.3f} | "
            f"Mom:{getattr(self, '_defense_state', {}).get('momentum', 0.0):+.3f} | "
            f"Regime:{getattr(self, '_market_regime', 'UNK')} | "
            f"IntMode:{getattr(self, '_intent_mode', 'UNK')} | "
            f"InvL:{getattr(self, '_intent_load', 0.0):.2f} | "
            f"Stress:{getattr(self, '_smooth_stress', 0.0):.3f} | "
            f"T:{getattr(self, '_last_t_rem', 0.0):.0f}s"
        )

    # СТАЛО (упрощённая версия):
    def _log_block_state(self, key: str, is_blocked: bool, context: str):
        prev = self._block_state.get(key, False)
        if is_blocked == prev:
            return
        # Гистерезис: не переключаем если прошло меньше 3 секунд
        _last_switch = self._block_state.get(f'{key}_ts', 0.0)
        if time.time() - _last_switch < 3.0:
            return
        self._block_state[f'{key}_ts'] = time.time()
        self._block_state[key] = is_blocked
        icon = "🔴" if is_blocked else "🟢"
        action = "LOCK" if is_blocked else "FREE"
        t_rem = getattr(self, '_last_t_rem', 0.0)
        cvd = getattr(self, '_cvd_signal_last', 0.0)
        streak = getattr(self, '_cvd_toxic_streak', 0)
        open_q = getattr(self, '_last_open_q', 0)
        ob = getattr(self, '_last_orderbook', {})
        try:
            shadow = self._compute_shadow_accounting(open_q)
            y_avg = shadow.get('y_avg_price', 0.0)
            n_avg = shadow.get('n_avg_price', 0.0)
            oq = shadow.get('open_q', 0)
            if oq > 0:
                inv_ps = y_avg + (1.0 - ob.get('yes_bid', 0.5))
            elif oq < 0:
                inv_ps = n_avg + ob.get('yes_ask', 0.5)
            else:
                inv_ps = 0.0
        except Exception:
            inv_ps = 0.0
        _regime   = getattr(self, '_market_regime', 'UNKNOWN')
        _intmode  = getattr(self, '_intent_mode', 'UNKNOWN')
        _invl     = getattr(self, '_intent_load', 0.0)
        _momentum = getattr(self, '_defense_state', {}).get('momentum', 0.0)
        logging.getLogger('gabalog.grid_strategy').warning(
            f"{icon} [BLOCK_CTX] {key} → {action} | {context} | "
            f"InvPS:{inv_ps:.3f} | Streak:{streak} | {self._std_ctx()}"
        )

    def get_final_report_text(self, market_slug: str, final_winner: str = "UNKNOWN") -> str:
        """Генерирует финальный отчет [FINAL_MARKET_REPORT] v8.2 Fix"""
        try:
            y_shares = int(self.position.yes_shares)
            n_shares = int(self.position.no_shares)
            tail_cost = float(self.position.total_cost)

            payout = (y_shares * 1.0) if final_winner == "YES" else (n_shares * 1.0) if final_winner == "NO" else 0.0
            tail_pnl = payout - tail_cost

            # Исправленные ключи (соответствуют on_tick)
            p_merges = getattr(self.position, 'profit_merges_count', 0)
            s_merges = getattr(self.position, 'salvage_merges_count', 0)
            merge_pnl = getattr(self.position, 'realized_ctf_pnl', 0.0)
            
            # Общий оборот за сессию (объём слияний + остаток на балансе)
            total_volume = getattr(self.position, 'session_merge_volume', 0.0) + tail_cost  
            
            # Чистый профит = Прибыль от спреда (Merge) + результат хвоста (Tail PnL)
            net_profit = merge_pnl + tail_pnl
            roi_dep = (net_profit / self.config.deposit * 100) if self.config.deposit > 0 else 0.0

            return f"""
        ==================================================
        🏆 [FINAL MARKET REPORT] {market_slug}
        ==================================================
        📌 INVENTORY (Tail):
        - YES : {y_shares} шт | NO : {n_shares} шт
        - Winner : {final_winner} | Tail PnL: ${tail_pnl:+.3f}

        ♻️ CTF CLEARING (MERGE):
        - Merges (Profit/Salvage): {p_merges} / {s_merges}
        - Total Merge PnL : ${merge_pnl:+.4f}

        📈 SUMMARY:
        - Turn Volume : ${total_volume:.3f}
        - NET PROFIT  : ${net_profit:+.4f}
        - ROI/Deposit : {roi_dep:+.3f}%
        ==================================================
            """
        except Exception as e:
            return f"❌ [REPORT ERROR] {e}"
