"""
Grid order manager for market making.

Manages a grid of limit orders on both sides (YES/NO).
Each tick: compare target grid (from AS pricing) with current pending orders,
cancel stale orders and place new ones.

Core principle: When price moves, instantly cancel old orders and shift
them closer to the current market price.

See: docs/STRATEGY_V6_GRID.md section 6.2
"""

from __future__ import annotations

import time


from dataclasses import dataclass, field



# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GridLevel:
    """Target grid level for one side at one price."""
    side: str         # 'YES' | 'NO'
    price: float
    size: int
    level_idx: int    # 0 = closest to reservation
    intent: str = 'NORMAL'  # ← добавить

@dataclass
class PendingOrder:
    """An order currently live on the CLOB."""
    order_id: str
    side: str         # 'YES' | 'NO'
    price: float
    size: int
    timestamp: float = field(default_factory=time.time)
    intent: str = 'NORMAL'  # ← добавить
    regime_at_creation: str = '?'  # [v3.2] regime in moment of intent creation, не fill
    fv_at_creation: float = 0.5  # [v3.3] FV в момент создания (для измерения mispricing magnitude)
    pair_state_at_creation: str = '?'  # [v3.3] BALANCED/FRESH/STUCK на момент создания
    intent_mode_at_creation: str = '?'  # [v3.3] OPTIMIZE/BALANCED/RESTORE на момент создания
    spread_at_creation: float = 0.0  # [v3.3] yes_ask - yes_bid на момент создания (рыночные условия)

@dataclass
class OrderAction:
    """Instruction to cancel or place an order."""
    action: str       # 'cancel' | 'place'
    order_id: str | None = None   # for cancel
    side: str | None = None       # for place: 'YES' | 'NO'
    price: float | None = None    # for place
    size: int | None = None       # for place
    is_taker: bool = False        # for recovery only
    reason: str = ""              # Текст причины
    level_idx: int = 0            # Глубина сетки (L0, L1...)
    intent: str = 'NORMAL'


# ---------------------------------------------------------------------------
# GridManager
# ---------------------------------------------------------------------------

TICK_SIZE = 0.01
MIN_LOT = 5
MIN_NOTIONAL = 1.00


class GridManager:
    """
    Manages the grid of limit orders.

    Each tick:
    1. Receive target prices from AS Pricer
    2. Compare with current pending orders
    3. If order is stale (price moved > threshold) -> mark for cancel
    4. Compute new orders needed at target levels
    5. Return list of OrderAction (cancel/place)
    """

    def __init__(
        self,
        grid_levels: int = 3,
        grid_spacing_ticks: int = 1,
        grid_lot_size: int = 5,
        grid_lot_decay: float = 1.0,
        imbalance_lot_multiplier: float = 1.0,
        stale_threshold_ticks: int = 3, # Теперь это основной порог Down (Retreat)
        chase_threshold_ticks: int = 1, # Теперь это основной порог Up (Chase)
        deep_level_static: bool = True,
        event_callback=None,
        spacing_asym_multiplier: float = 2.5,
        config = None 
    ):
        self.config = config 
        self.grid_levels = grid_levels


        self.grid_spacing_ticks = grid_spacing_ticks
        self.grid_lot_size = grid_lot_size
        self.grid_lot_decay = grid_lot_decay
        self.imbalance_lot_multiplier = imbalance_lot_multiplier
        self.stale_threshold_ticks = stale_threshold_ticks
        self.chase_threshold_ticks = chase_threshold_ticks
        self.deep_level_static = deep_level_static
        self._event_callback = event_callback  
        self.fill_cooldown_sec: float = 0.0  
        self._last_fill_time: dict[str, float] = {'YES': 0.0, 'NO': 0.0}
        self.spacing_asym_multiplier = spacing_asym_multiplier
        
        # Нам больше не нужно хранить _last_effective_spacing для логики, 
        # только для возможной телеметрии.
        self._last_effective_spacing = {'YES': 0.0, 'NO': 0.0} 

        self.pending_orders: dict[str, PendingOrder] = {}
        self.pending_sell_orders: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Sell order tracking (separate from BUY grid)
    # ------------------------------------------------------------------

    def register_sell_order(self, order_id: str, side: str, price: float, size: int) -> None:
        """Track a pending SELL order (recycling). Excluded from sync()."""
        self.pending_sell_orders[order_id] = {
            'side': side, 'price': price, 'size': size, 'placed_at': time.time(),
        }

    def on_sell_fill(self, order_id: str) -> None:
        """Remove filled sell order from tracking."""
        self.pending_sell_orders.pop(order_id, None)

    def cancel_sell_order(self, order_id: str) -> None:
        """Cancel and remove a sell order."""
        self.pending_sell_orders.pop(order_id, None)

    def expire_stale_sells(self, ttl_sec: float = 60.0) -> list[str]:
        """Auto-cancel sell orders older than TTL. Returns cancelled IDs."""
        now = time.time()
        expired = [oid for oid, info in self.pending_sell_orders.items()
                   if now - info['placed_at'] > ttl_sec]
        for oid in expired:
            self.pending_sell_orders.pop(oid)
        return expired

    # ------------------------------------------------------------------
    # Target grid calculation
    # ------------------------------------------------------------------

    def calculate_target_grid(
        self,
        budget_remaining: float,
        l0_yes_price: float,
        l0_no_price: float,
        weak_leg: str = '',
        time_remaining_sec: float = 900.0,
        imbalance_shares: int = 0,
        stress_multiplier: float = 1.0,
        is_desperate: bool = False # [v12.2.1]
    ) -> list[GridLevel]:
       
        # [v12.8-SALVAGE] Якорь для слабой ноги
        self._current_weak_leg = weak_leg if is_desperate else None

        levels: list[GridLevel] = []
        cumulative_cost = 0.0
        # Рассчитываем множитель асимметрии: на цене 0.5 = 1.0; на цене 0.1 = 2.0; на цене 0.9 = 0.6
        # Это расширяет сетку для дешевых (рисковых) и сужает для дорогих (стабильных)
        # [v9.25] DYNAMIC ASYMMETRIC SPACING
        # Используем self.spacing_asym_multiplier из конфига вместо хардкода 2.5
        mult = self.spacing_asym_multiplier
        
        yes_price_mult = 1.0 + (0.5 - l0_yes_price) * mult
        yes_spacing = self.grid_spacing_ticks * TICK_SIZE * max(0.4, yes_price_mult) * stress_multiplier

        no_price_mult = 1.0 + (0.5 - l0_no_price) * mult
        no_spacing = self.grid_spacing_ticks * TICK_SIZE * max(0.4, no_price_mult) * stress_multiplier

        # Сохраняем эффективный шаг для расчета гистерезиса в методе sync()
        self._last_effective_spacing = {'YES': yes_spacing, 'NO': no_spacing}

        for k in range(self.grid_levels):
            # [v9.30] CYBORG L1 PROTECTION
            p_mult = 1.0 if k == 0 else 1.5
            
            yes_price = round(l0_yes_price - (k * yes_spacing * p_mult), 2)
            no_price = round(l0_no_price - (k * no_spacing * p_mult), 2)

            # [v12.7-CONTINUOUS] Asymmetric Sizing
            # Извлекаем динамические лоты, которые стратегия принудительно прописала в self
            lot_y_base = getattr(self, 'grid_lot_size_y', self.grid_lot_size)
            lot_n_base = getattr(self, 'grid_lot_size_n', self.grid_lot_size)

            # Рассчитываем лоты для текущего уровня k (L0, L1, L2)
            if k == 0:
                yes_lot, no_lot = lot_y_base, lot_n_base
            elif k == 1:
                yes_lot, no_lot = lot_y_base + 3, lot_n_base + 3
            else:
                yes_lot, no_lot = int(lot_y_base * 2), int(lot_n_base * 2)

            # [v9.32] УМНЫЙ ЛИМИТ ЛОТА
            MAX_SINGLE_LOT = getattr(self.config, 'max_single_lot', 15) if self.config else 15
            
            # --- [FIX] Удалены строки перетирания yes_lot/no_lot через base_lot ---
            
            # Усиление слабой ноги (Hunter-коррекция объема)
            if weak_leg and imbalance_shares > 0:
            # В режиме отчаяния игнорируем лимит MAX_SINGLE_LOT для быстрого выравнивания
                effective_max_lot = MAX_SINGLE_LOT if not is_desperate else (MAX_SINGLE_LOT * 3)
                if weak_leg == 'YES':
                # Используем yes_lot (уже рассчитанный асимметрично) как базу
                    yes_lot = max(yes_lot, min(imbalance_shares, effective_max_lot))
                elif weak_leg == 'NO':
                # Используем no_lot (уже рассчитанный асимметрично) как базу
                    no_lot = max(no_lot, min(imbalance_shares, effective_max_lot))
            
            # --- КОРРИДОР БЕЗОПАСНОСТИ (Cyber-Shield Compatible) ---
            if yes_price < 0.03: yes_lot = 0
            if no_price < 0.03: no_lot = 0

            # Потолок раздвинут для эффективного Hunter-а
            if yes_price > 0.998: yes_lot = 0
            if no_price > 0.998: no_lot = 0

            if yes_price < 0.01 or no_price < 0.01: continue

            # [FIXED] Пересчет лота только если покупка разрешена защитой
            # Определяем тяжёлую ногу: это сторона ПРОТИВ weak_leg
            _heavy_leg = ('YES' if weak_leg == 'NO' else
                          'NO'  if weak_leg == 'YES' else '')
            _imb_thr = getattr(self.config, 'hunter_imb_threshold', 10) if self.config else 10

            if yes_price >= 0.01 and yes_lot > 0:
                min_lot_y = int(1.05 / yes_price) + 1
                # На тяжёлой ноге при значимом перекосе — не раздуваем лот принудительно.
                # Если лот мал → notional < $1.01 → ордер тихо отклонится ниже.
                if not (_heavy_leg == 'YES' and imbalance_shares > _imb_thr):
                    yes_lot = max(yes_lot, min_lot_y)

            if no_price >= 0.01 and no_lot > 0:
                min_lot_n = int(1.05 / no_price) + 1
                if not (_heavy_leg == 'NO' and imbalance_shares > _imb_thr):
                    no_lot = max(no_lot, min_lot_n)

            # Пересчет фактической суммы сделки
            yes_notional = yes_price * yes_lot
            no_notional = no_price * no_lot

            # Разрешаем ставить ордера, только если они проходят по лимиту $1.00 и бюджету
            if yes_notional >= 1.01 and yes_lot > 0 and (cumulative_cost + yes_notional) <= budget_remaining:
                levels.append(GridLevel(side='YES', price=yes_price, size=yes_lot, level_idx=k))
                cumulative_cost += yes_notional

            if no_notional >= 1.01 and no_lot > 0 and (cumulative_cost + no_notional) <= budget_remaining:
                levels.append(GridLevel(side='NO', price=no_price, size=no_lot, level_idx=k))
                cumulative_cost += no_notional
                       
        return levels
    # ------------------------------------------------------------------
    # Sync: diff pending vs target -> cancel/place
    # ------------------------------------------------------------------

    def sync(self, target: list[GridLevel], refresh_timeout: float = 15.0) -> list[OrderAction]:
        actions: list[OrderAction] = []
        target_map: dict[tuple[str, float], GridLevel] = {}
        for lvl in target:
            target_map[(lvl.side, lvl.price)] = lvl

        side_targets: dict[str, list[GridLevel]] = {'YES': [], 'NO': []}
        for lvl in target:
            side_targets[lvl.side].append(lvl)

        covered: set[tuple[str, float]] = set()
        now = time.time()

        for oid, pending in list(self.pending_orders.items()):
            # 1. Smart Refresh
            if now - pending.timestamp > refresh_timeout:
                self._cancel_with_event(actions, oid, reason="REFRESH_TIMEOUT")
                continue 

            # 2. Точное совпадение
            key = (pending.side, pending.price)
            if key in target_map:
                t = target_map[key]
                if abs(t.size - pending.size) > 2: 
                    self._cancel_with_event(actions, oid, reason=f"RESIZE")
                else:
                    covered.add(key)
                continue

            # 3. Поиск ближайшей цели
            nearest_target = None
            min_dist = float('inf')
            for tlvl in side_targets.get(pending.side, []):
                dist = abs(tlvl.price - pending.price)
                if dist < min_dist:
                    min_dist = dist
                    nearest_target = tlvl

            if nearest_target is None:
                self._cancel_with_event(actions, oid, reason="NO_TARGET")
                continue

            # 4. [v9.25] ГИСТЕРЕЗИС В ТИКАХ (АБСОЛЮТНЫЙ)
            # Мы больше не зависим от ширины шага сетки (spacing). 
            # Допуск всегда равен X центам из конфига.

            # 4. [v12.8-SALVAGE] SMART HYSTERESIS (Охотничий Якорь)
            current_defcon = getattr(self, '_current_defcon', 0)
            is_hunter_leg = (pending.side == getattr(self, '_current_weak_leg', None))
            
            if is_hunter_leg:
                # Если нога спасительная, стоим мертво (якорь 4 тика)
                retreat_tol = 4 * TICK_SIZE
                chase_tol = 4 * TICK_SIZE
            elif current_defcon > 0:
                retreat_tol = 2 * TICK_SIZE
                chase_tol = 3 * TICK_SIZE
            else:
                retreat_tol = self.stale_threshold_ticks * TICK_SIZE
                chase_tol = self.chase_threshold_ticks * TICK_SIZE
            
            price_diff = nearest_target.price - pending.price 

            # СИТУАЦИЯ: Цена упала (Наш Bid стал слишком высоким/дорогим)
            if price_diff < 0:
                if abs(price_diff) <= retreat_tol:
                    covered.add((nearest_target.side, nearest_target.price))
                    continue
                else:
                    self._cancel_with_event(actions, oid, reason=f"RETREAT (Δ{abs(price_diff):.3f})")
                    continue

            # СИТУАЦИЯ: Цена выросла (Наш Bid остался слишком глубоко внизу)
            if price_diff > 0:
                # Сохраняем логику "статичных глубоких уровней" (L1+ ленивее в 2 раза)
                effective_chase_tol = chase_tol * (2.0 if (self.deep_level_static and nearest_target.level_idx > 0) else 1.0)
                
                if abs(price_diff) <= effective_chase_tol:
                    covered.add((nearest_target.side, nearest_target.price))
                    continue
                else:
                    self._cancel_with_event(actions, oid, reason=f"CHASE (Δ{abs(price_diff):.3f})")
                    continue

            covered.add(key)

        # Place new orders for uncovered targets
        for tkey, tlvl in target_map.items():
            if tkey not in covered:
                if self.fill_cooldown_sec > 0:
                    last_fill = self._last_fill_time.get(tlvl.side, 0.0)
                    if now - last_fill < self.fill_cooldown_sec:
                        continue
                actions.append(OrderAction(
                    action='place', side=tlvl.side, price=tlvl.price, size=tlvl.size,
                    reason="NEW_GRID_LEVEL", level_idx=tlvl.level_idx, intent=tlvl.intent
                ))
                if self._event_callback:
                    self._event_callback('place', tlvl.side, tlvl.price, tlvl.size)

        return actions

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _cancel_with_event(self, actions: list, oid: str, reason: str = "Stale"):
        """Cancel order and emit event callback."""
        pending = self.pending_orders.get(oid)
        actions.append(OrderAction(action='cancel', order_id=oid, reason=reason))
        if pending and self._event_callback:
            self._event_callback('cancel', pending.side, pending.price, pending.size)

    def register_order(self, order_id: str, side: str, price: float, size: int,
                       intent: str = 'NORMAL', regime_at_creation: str = '?',
                       fv_at_creation: float = 0.5, pair_state_at_creation: str = '?',
                       intent_mode_at_creation: str = '?', spread_at_creation: float = 0.0) -> None:
        """Register a newly placed order. [v3.2+v3.3] capture full context at moment of intent creation."""
        self.pending_orders[order_id] = PendingOrder(
            order_id=order_id,
            side=side,
            price=price,
            size=size,
            intent=intent,
            regime_at_creation=regime_at_creation,
            fv_at_creation=fv_at_creation,
            pair_state_at_creation=pair_state_at_creation,
            intent_mode_at_creation=intent_mode_at_creation,
            spread_at_creation=spread_at_creation,
        )

    def on_fill(self, order_id: str, fill_size: int, fill_price: float) -> None:
        """Order filled — update size or remove if fully filled."""
        pending = self.pending_orders.get(order_id)
        if pending:
            # Уменьшаем размер в памяти менеджера
            pending.size -= fill_size
            self._last_fill_time[pending.side] = time.time()
            
            # Удаляем только если ордер съеден полностью
            if pending.size <= 0:
                self.pending_orders.pop(order_id, None)

    def on_cancel_confirmed(self, order_id: str) -> None:
        """Cancel confirmed by CLOB — remove from pending."""
        self.pending_orders.pop(order_id, None)

    def cancel_all(self) -> list[str]:
        """[v11.59] Полная очистка: и покупки (grid) и продажи (recycling)."""
        buy_ids = list(self.pending_orders.keys())
        sell_ids = list(self.pending_sell_orders.keys())
        return buy_ids + sell_ids

    def cancel_side(self, side: str) -> list[str]:
        """Отменить все ордера одной стороны (YES или NO)."""
        ids = [
            oid for oid, order in self.pending_orders.items()
            if order.side == side
        ]
        for oid in ids:
            del self.pending_orders[oid]
        return ids    

    def clear_all(self) -> None:
        """Clear all pending orders from internal tracking (after batch cancel)."""
        self.pending_orders.clear()
        self.pending_sell_orders.clear()

    def get_pending_notional(self) -> float:
        """Calculate total value of all orders currently waiting in the CLOB."""
        total = 0.0
        for pending in self.pending_orders.values():
            total += pending.price * pending.size
        return total

    @property
    def pending_count(self) -> int:
        return len(self.pending_orders)
