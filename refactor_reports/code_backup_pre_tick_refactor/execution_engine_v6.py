"""
ExecutionEngine v6 — Batch order execution for Grid strategy.

Capabilities:
- Batch place: up to 15 GTC maker orders per HTTP request
- Batch cancel: cancel multiple orders in one request
- Cancel all market: cancel all orders for a token
- Single taker: place one taker order (recovery only, +250ms delay)
- Fill tracking: poll CLOB for fill status

All maker orders: GTC, postOnly=True.
Batch chunking: >15 orders split into 15-order chunks.

See: docs/STRATEGY_V6_GRID.md section 6.5
"""

from __future__ import annotations
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Optional
import asyncio
from collections import deque
from strategies.gabagool.grid_manager import OrderAction
from py_clob_client.clob_types import OrderArgs, PostOrdersArgs, OrderType, CreateOrderOptions
from py_clob_client.clob_types import RequestArgs
from py_clob_client.headers.headers import create_level_2_headers

def safe_poly_serialize(obj):
    """Глобальный сериализатор для Pydantic объектов Polymarket"""
    if hasattr(obj, 'dict'): return obj.dict()
    if hasattr(obj, 'model_dump'): return obj.model_dump()
    if hasattr(obj, 'to_dict'): return obj.to_dict()
    if hasattr(obj, '__dict__'): return obj.__dict__
    return str(obj)

logger = logging.getLogger('gabalog.execution_engine_v6')

# Polymarket batch limit
MAX_BATCH_SIZE = 15

# Polymarket enforced taker delay
TAKER_DELAY_MS = 250

# Paper mode: cancel race condition window (ms)
# Orders in PENDING_CANCEL can still be filled during this window
CANCEL_RACE_WINDOW_MS = 150


@dataclass
class FillEvent:
    """A fill event from the CLOB."""
    order_id: str
    side: str        
    size: int
    price: float
    is_taker: bool = False  
    timestamp: float = field(default_factory=time.time)
    latency_ms: int = 0  # <--- НОВОЕ: Для передачи реальной задержки
    level_idx: str = '?' # <--- НОВОЕ: Чтобы видеть L0, L1... в логах


class ExecutionEngineV6:
    """
    Batch order execution engine for v6 grid strategy.

    Designed for grid market making: frequent batch place/cancel cycles.
    All communication with CLOB goes through the clob_client.

    Usage:
        engine = ExecutionEngineV6(clob_client=client, paper_mode=True)
        order_ids = await engine.batch_place(place_actions)
        await engine.batch_cancel(stale_order_ids)
    """

    def __init__(
        self,
        clob_client: Any = None,
        paper_mode: bool = True,
        yes_token_id: str = '',
        no_token_id: str = '',
        funder_address: str = '', # Добавляем хранение адреса
    ):
        self.funder_address = funder_address
        self.clob_client = clob_client
        self.paper_mode = paper_mode
        self.active_orders_metadata = {}
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self._token_params_cache = {}

        # Internal tracking
        self._order_counter: int = 0
        self._active_orders: dict[str, dict] = {}
        self._active_sell_orders: dict[str, dict] = {}  # SELL limit orders (recycling)
        self.recent_fills = deque(maxlen=50) # Храним последние 50 сделок
        self._inventory_lock = asyncio.Lock()

        # API request callback (set by adapter to track in strategy)
        self._api_request_callback = None
        
        self.nudge_size = 0.003 # По умолчанию
        # Stats
        self.stats = {
            'batches_placed': 0,
            'orders_placed': 0,
            'orders_cancelled': 0,
            'taker_orders': 0,
            'fills': 0,
            'api_errors': 0,
        }
        self._throttle_until = 0.0  # Unix-время, до которого мы на паузе

        # [v11.60-HFT] Окно мониторинга Round-trip time (RTT)
        self._latency_history = deque(maxlen=10)

        # [PHASE 1] Rolling CFR Tracker        
        self._action_history = deque(maxlen=200) # Помним последние 200 событий (C - Cancel, F - Fill)


    # ИСПРАВЛЕННЫЙ МЕТОД:
    def _nudge_price(self, side: str, price: float) -> float:
        """
        При TICK_SIZE = 0.01 минимальный сдвиг — это 1 цент.
        """
        shift = 0.01 
        if 'SELL_' in side:
            return round(price + shift, 2)
        else:
            return round(price - shift, 2)

    # ------------------------------------------------------------------
    # Batch Place
    # ------------------------------------------------------------------

    async def batch_place(self, intents: list[OrderAction]) -> list[str]:
        """
        Place up to N orders via batch API. Chunks into groups of 15.

        All orders: GTC, postOnly=True (maker).

        Args:
            intents: List of OrderAction with action='place'.

        Returns:
            List of order_ids from CLOB (or generated for paper mode).
        """
        place_intents = [i for i in intents if i.action == 'place' and not i.is_taker]
        if not place_intents:
            return []

        all_order_ids: list[str] = []

        # Chunk into batches of MAX_BATCH_SIZE
        for chunk_start in range(0, len(place_intents), MAX_BATCH_SIZE):
            chunk = place_intents[chunk_start:chunk_start + MAX_BATCH_SIZE]

            if self.paper_mode:
                ids = self._paper_place(chunk)
            else:
                ids = await self._live_place(chunk)

            all_order_ids.extend(ids)

        self.stats['batches_placed'] += (len(place_intents) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        self.stats['orders_placed'] += len(all_order_ids)

        # --- [LOGGING] ---
        # Собираем краткое резюме пакета
        if place_intents:
            reasons = {i.reason for i in place_intents}
            logger.info(f"🔸 [BATCH] Выставлено {len(place_intents)} ордеров. Причины: {', '.join(reasons)}")
        
        return all_order_ids

    def _paper_place(self, intents: list[OrderAction]) -> list[str]:
        """Paper mode: generate local order IDs."""
        ids = []
        for intent in intents:
            self._order_counter += 1
            oid = f"GRID-P-{self._order_counter:06d}"
            self._active_orders[oid] = {
                'side': intent.side,
                'price': intent.price,
                'size': intent.size,
                'timestamp_send': time.time(),
                'level_idx': getattr(intent, 'level_idx', '?'),
            }
            ids.append(oid)
        return ids

    # ------------------------------------------------------------------
    # Batch Place (FIXED: SDK-only for 401 avoidance)
    # ------------------------------------------------------------------

    async def _live_place(self, intents: list[OrderAction]) -> list[str]:
        """[v11.50-FINAL] Optimized Logging: Details on error only. Correct batch tracking."""
        if self.clob_client is None: return []
        from py_clob_client.clob_types import OrderArgs, PostOrdersArgs, OrderType, CreateOrderOptions
        import asyncio, json

        all_confirmed_ids = []
        # Список для хранения объектов подписанных ордеров, чтобы логгер не ошибался
        signed_orders_list = [] 
        
        try:
            post_args = []
            for intent in intents:
                actual_side = intent.side.replace('SELL_', '')
                token_id = self.yes_token_id if actual_side == 'YES' else self.no_token_id
                clob_side = 'SELL' if 'SELL_' in intent.side else 'BUY'

                market_params = self._token_params_cache.get(token_id, {})
                server_fee = market_params.get('fee_bps', 1000)

                order_args = OrderArgs(
                    token_id=token_id,
                    price=round(intent.price, 2),
                    size=float(max(5, int(intent.size))),
                    side=clob_side,
                    fee_rate_bps=server_fee
                )

                options = CreateOrderOptions(tick_size="0.01", neg_risk=False)
                signed_order = self.clob_client.create_order(order_args, options=options)
                
                # Сохраняем ордер в список для синхронизации с результатами
                signed_orders_list.append(signed_order)
                post_args.append(PostOrdersArgs(order=signed_order, orderType=OrderType.GTC, postOnly=True))

            if not post_args: return []
            
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: self.clob_client.post_orders(post_args))
            
            results = resp if isinstance(resp, list) else resp.get('orderResults', [])
            
            # ZIP трех списков: намерения, ответы сервера и конкретные подписанные объекты
            for intent, res, s_order in zip(intents, results, signed_orders_list):
                oid = res.get('orderID') if isinstance(res, dict) else (res if isinstance(res, str) else None)
                
                if oid and len(str(oid)) > 10:
                    all_confirmed_ids.append(str(oid))
                    self._active_orders[oid] = {
                        'side': intent.side, 
                        'price': intent.price, 
                        'size': intent.size, 
                        'timestamp_send': time.time(),
                        'level_idx': getattr(intent, 'level_idx', '?') # [FIX] Запоминаем уровень
                    }
                else:
                    # ВЫВОДИМ ПОДРОБНОСТИ ТОЛЬКО ПРИ ОШИБКЕ (Блок строго внутри else)
                    error_msg = res.get('errorMsg') if isinstance(res, dict) else res
                    logger.warning(f"⚠️ ОТКАЗ {intent.side}@{intent.price}: {error_msg}")
                
                    try:
                        # Используем s_order (соответствующий объект), а не signed_order (последний в цикле)
                        raw_data = s_order.dict() if hasattr(s_order, 'dict') else s_order
                        o_part = raw_data.get('order', raw_data)
                        logger.warning(f"🔍 [DEBUG_DATA] Wire Data (This Order): {json.dumps(o_part, indent=2)}")
                        logger.warning(f"🎯 [DEBUG_DATA] Full Batch Server Response: {resp}")
                    except: pass

        except Exception as e:
            logger.error(f"‼️ [LIVE_PLACE_FAILED] {e}")
            
        return all_confirmed_ids

    # ------------------------------------------------------------------
    # Batch Cancel (FIXED: SDK-only)
    # ------------------------------------------------------------------

    async def cancel_stale_orders(self, max_ttl_sec: float = 3.0) -> list[str]:
        """
        [v14.7-CORE] Hard TTL: Поиск и принудительная отмена ордеров-мишеней.
        Ордер считается протухшим, если он висит в стакане дольше max_ttl_sec.
        """
        now = time.time()
        to_cancel = []
        reasons = {}

        # Создаем копию ключей, чтобы не словить RuntimeError при изменении словаря
        for oid, info in list(self._active_orders.items()):
            # Пропускаем такеры (они и так FOK) и те, что уже в процессе отмены
            if info.get('is_taker') or 'cancel_requested_at' in info or 'cancel_pending_at' in info:
                continue

            # Считаем возраст от момента отправки (timestamp_send)
            created_at = info.get('timestamp_send', now)
            age = now - created_at

            if age > max_ttl_sec:
                to_cancel.append(oid)
                reasons[oid] = f"TTL_EXPIRED({age:.1f}s)"

        if to_cancel:
            logger.warning(f"⏰ [TTL_GUARD] Обнаружено {len(to_cancel)} старых лимиток. Запуск зачистки...")
            # Вызываем метод, который идет сразу ниже в коде
            await self.batch_cancel(to_cancel, reasons=reasons)
            
        return to_cancel

    async def batch_cancel(self, order_ids: list[str], reasons: dict = None) -> None:
        """Cancel multiple orders via SDK with summary logging (v16.4-NO_SPAM)"""
        if not order_ids:
            return

        if not self.paper_mode and not callable(getattr(self.clob_client, 'cancel_orders', None)):
            logger.error("‼️ [SDK_CRASH] Метод cancel_orders поврежден.")
            return

        now = time.time()
        # Статистика для итогового лога
        stats = {"YES": 0, "NO": 0}
        
        # 1. ОБРАБОТКА В PAPER_MODE
        if self.paper_mode:
            reason_summary = "PAPER_CANCEL"
            for oid in order_ids:
                if oid in self._active_orders:
                    info = self._active_orders[oid]
                    side = info.get('side', 'UNK')
                    size = int(info.get('size', 0))
                    stats[side] = stats.get(side, 0) + size
                    
                    self._active_orders[oid]['cancel_pending_at'] = now
                    reason_summary = reasons.get(oid, "PAPER_CANCEL") if reasons else "PAPER_CANCEL"
                    
                    # Пишем только в RAW LOG (тихий файл), не в консоль PM2
                    self._write_to_orders_log({
                        "event": "cancel", "order_id": oid, "latency_ms": 0,
                        "target_price": info.get('price', 0), "side": side,
                        "reason": reason_summary
                    })
            
            # ОДИН ЛОГ НА ВЕСЬ БАТЧ (Console/PM2)
            summary_str = ", ".join([f"{s}: {q}" for s, q in stats.items() if q > 0])
            logger.info(f"🚫 [CANCEL BATCH PAPER] {summary_str} | Reason: {reason_summary}")

        # 2. ОБРАБОТКА В LIVE MODE (SDK)
        else:
            for oid in order_ids:
                if oid in self._active_orders:
                    self._active_orders[oid]['cancel_requested_at'] = now
            
            try:
                loop = asyncio.get_event_loop()
                start_api = time.time()
                await loop.run_in_executor(None, lambda: self.clob_client.cancel_orders(order_ids))
                latency_api = int((time.time() - start_api) * 1000)
                
                unique_reasons = ", ".join(set(reasons.values())) if reasons else "BATCH_CANCEL"
                
                # Собираем статистику по сторонам для Live-лога
                for oid in order_ids:
                    info = self._active_orders.get(oid)
                    if info:
                        side = info.get('side', 'UNK')
                        stats[side] = stats.get(side, 0) + int(info.get('size', 0))
                        
                        # RAW LOG (тихий)
                        life_time_ms = int((time.time() - info.get('timestamp_send', time.time())) * 1000)
                        self._write_to_orders_log({
                            "event": "cancel", "order_id": oid, "latency_ms": life_time_ms,
                            "target_price": info.get('price', 0), "side": side, "reason": unique_reasons
                        })

                # ОДИН ЛОГ НА ВЕСЬ БАТЧ (Console/PM2)
                summary_str = ", ".join([f"{s}: {q}" for s, q in stats.items() if q > 0])
                logger.info(f"🗑️ [BATCH CANCEL LIVE] {summary_str} | {latency_api}ms | Reason: {unique_reasons}")
                
                for _ in order_ids:
                    self._action_history.append('C')

            except Exception as e:
                err_msg = str(e).lower()
                if '429' in err_msg or 'too many' in err_msg:
                    logger.warning("🚨 [API LIMIT] 429 Detected! Throttling CANCEL for 3s")
                    self._throttle_until = time.time() + 3.0
                logger.error(f"‼️[ENGINE_V6] SDK Batch Cancel error: {e}")
                self.stats['api_errors'] += 1

        self.stats['orders_cancelled'] += len(order_ids)

    # ------------------------------------------------------------------
    # Cancel All Market (FIXED: SDK-only)
    # ------------------------------------------------------------------

    async def cancel_all_market(self, asset_id: str = '') -> None:
        """Cancel all market orders using SDK."""
        now = time.time()
        
        if self.paper_mode:
            # ИЗВЛЕКАЕМ INFO В ЦИКЛЕ
            for oid, info in self._active_orders.items():
                logger.info(f"☢️ [NUCLEAR PAPER] Killed {info.get('side', '')} {info.get('size', 0)}@{info.get('price', 0)}")
            self._active_orders.clear()
            return

        try:
            # ИЗВЛЕКАЕМ INFO В ЦИКЛЕ перед сбросом
            for oid, info in self._active_orders.items():
                # 1. PM2 LOG
                logger.info(f"☢️ [NUCLEAR ITEM] Killed {info.get('side', 'UNKNOWN')} {info.get('size', 0)}@{info.get('price', 0)} | ID: {oid[:12]}...")
                
                # 2. RAW LOG
                life_time_ms = int((now - info.get('timestamp_send', now)) * 1000)
                self._write_to_orders_log({
                    "event": "cancel", "order_id": oid, "latency_ms": life_time_ms,
                    "target_price": info.get('price', 0), "side": info.get('side', 'UNKNOWN'),
                    "reason": "NUCLEAR_CANCEL"
                })

            start_api = time.time()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.clob_client.cancel_all())
            
            logger.info(f"☢️ [NUCLEAR CANCEL COMPLETE] Рынок очищен через SDK за {int((time.time() - start_api)*1000)}ms")
                
        except Exception as e:
            logger.error(f"‼️[ENGINE_V6] SDK Market Cancel error: {e}")
            self.stats['api_errors'] += 1

        self._active_orders.clear()

    async def cancel_all_verified(self, max_retries: int = 5) -> bool:
        """[v11.67-SHIELD] Гарантированная зачистка с проверкой по API."""
        if self.paper_mode:
            self._active_orders.clear()
            return True

        # 1. Первый удар
        await self.cancel_all_market()

        # 2. Цикл верификации
        for attempt in range(max_retries):
            await asyncio.sleep(0.1) # Короткая пауза для обработки сервером
            
            try:
                # Проверяем наличие открытых ордеров через SDK
                open_orders = await self._call_api('get_orders')
                
                # Если список пуст (None или []) — успех
                if not open_orders:
                    logger.info(f"✅ [SHIELD] Стакан зачищен (попытка {attempt + 1})")
                    return True
                
                # Если что-то осталось — повторяем cancel_all
                logger.warning(f"⚠️ [SHIELD] В стакане осталось {len(open_orders)} ордеров. Повторный снос...")
                await self.cancel_all_market()
                
            except Exception as e:
                logger.error(f"⁉️ [SHIELD] Ошибка при верификации стакана: {e}")

        logger.error("❌ [FATAL] Не удалось зачистить стакан за 5 попыток! Сеть или API нестабильны.")
        return False    

    def check_sell_fills(self, trade_price: float, trade_is_yes: bool, trade_size: float) -> list:
        """Check if any SELL orders can be filled by this trade.
        SELL YES fills when someone BUYs YES at price >= our sell price.
        SELL NO fills when someone BUYs NO at price >= our sell price.
        Returns list of (order_id, side, size, price) tuples.
        """
        filled = []
        for oid, info in list(self._active_sell_orders.items()):
            sell_side = info['side']
            # SELL YES fills on YES trades at >= our price
            # SELL NO fills on NO trades at >= our price
            is_yes_sell = (sell_side == 'YES')
            if is_yes_sell == trade_is_yes and trade_price >= info['price']:
                filled.append((oid, sell_side, info['size'], info['price']))
                self._active_sell_orders.pop(oid)
        return filled

    def get_active_sell_orders(self) -> dict:
        """Return copy of active sell orders for dashboard display."""
        return dict(self._active_sell_orders)

    # ------------------------------------------------------------------
    # Single Taker (recovery only)
    # ------------------------------------------------------------------

    async def place_taker(self, intent: OrderAction) -> Optional[str]:
        """[v11.50-FINAL] Dynamic Fee Taker Sync."""
        if self.paper_mode: return f"PAPER-T-{time.time()}"
        if self.clob_client is None: return None
        from py_clob_client.clob_types import OrderArgs, CreateOrderOptions

        try:
            actual_side = intent.side.replace('SELL_', '')
            token_id = self.yes_token_id if actual_side == 'YES' else self.no_token_id
            clob_side = 'SELL' if 'SELL_' in intent.side else 'BUY'

            # --- ДОБАВЛЯЕМ ДИНАМИЧЕСКУЮ КОМИССИЮ ---
            market_params = self._token_params_cache.get(token_id, {})
            server_fee = market_params.get('fee_bps', 1000) # Берем из кэша, как в мейкерах

            order_args = OrderArgs(
                token_id=token_id, 
                price=round(intent.price, 2),
                size=float(max(5, int(intent.size))), 
                side=clob_side,
                fee_rate_bps=server_fee # <--- Теперь синхронно с рынком
            )
            
            options = CreateOrderOptions(tick_size="0.01", neg_risk=False)
            signed_order = self.clob_client.create_order(order_args, options=options)

            # [v11.85] Превращаем ордер в настоящий Taker (FOK)

            post_args = PostOrdersArgs(
                order=signed_order, 
                orderType=OrderType.FOK, # Fill or Kill: исполни сразу или отмени
                postOnly=False
            )

            resp = await self._call_api('post_order', post_args)
            
            oid = resp.get('orderID') if isinstance(resp, dict) else None
            if oid:
                self._active_orders[oid] = {'side': intent.side, 'price': intent.price, 'size': intent.size, 'is_taker': True}
                logger.info(f"✅ TAKER ВЫСТАВЛЕН: {oid}")
                return str(oid)
            else:
                logger.warning(f"⚠️ Taker Rejected. Server says: {resp}")
                return None
        except Exception as e:
            # [v11.64-ULTIMATE] Глубокий аудит отклоненного Taker-ордера
            side = intent.side
            price = intent.price
            size = intent.size
            logger.error(f"‼️ [SDK_FATAL] Отказ TAKER-ордера: {e}")
            logger.error(f"🔍 [DEBUG_TAKER] Попытка: {side} | SIZE: {size} | PRICE: {price}")
            return None
    # ------------------------------------------------------------------
    # Fill tracking
    # ------------------------------------------------------------------

    async def on_fill(self, order_id: str, size: int, price: float) -> Optional[FillEvent]:
        """[v11.67-OPTIMISTIC] Атомарная регистрация филла с блокировкой инвентаря и сохранением всех логов."""
        import time
        import logging
        log = logging.getLogger('gabalog.execution_engine_v6')

        async with self._inventory_lock:
            info = self._active_orders.get(order_id)
            if info is None:
                return None

            # [v14.5-ELASTIC FIX] Частичное исполнение в Paper Mode (Механика ведра)
            if self.paper_mode:
                info['size'] -= size
                if info['size'] <= 0:
                    self._active_orders.pop(order_id) # Удаляем только когда объем исчерпан
            else:
                # В боевом (LIVE) режиме биржа сама пришлет финальный статус, 
                # тут логику пока не трогаем, если она завязана на поллинг
                self._active_orders.pop(order_id)

            side = info.get('side', '')
            is_taker = info.get('is_taker', False)  
            lvl_tag = f"L{info.get('level_idx', '?')}" 
            
            target_price = info.get('price', price)
            created_at = info.get('timestamp_send', time.time())
            latency_ms = int((time.time() - created_at) * 1000)
            
            action_word = "ПРОДАЛИ" if 'SELL_' in side else "КУПИЛИ"
            clean_side = side.replace('SELL_', '')
            
            # Логика Toxic Fill
            cancel_req = info.get('cancel_requested_at') or info.get('cancel_pending_at')
            if cancel_req:
                race_lost_by_ms = int((time.time() - cancel_req) * 1000)
                log.warning(f"☠️ [LDM] TOXIC FILL [{lvl_tag}]: {action_word} {size} {clean_side} по ${price:.2f} | Мы пытались отменить его, но опоздали на {race_lost_by_ms}ms!")
                
            log.info(f"[ENGINE_TO_STRATEGY] Fill passed to strategy: {side} {size}@{price:.2f} ({lvl_tag})")

            # Обновление статистики и трекера
            self._action_history.append('F')
            self.stats['fills'] += 1

            # Регистрация события для анализатора LDM
            self._write_to_orders_log({
                "event": "fill", "order_id": order_id, "latency_ms": latency_ms,
                "fill_price": price, "target_price": target_price, "side": side
            })

            # Обновление Дашборда
            self.recent_fills.append({
                'type': 'fill' if not is_taker else 'taker_fill',
                'side': side, 'size': size, 'price': price, 'ts': time.time()
            })

            return FillEvent(
                order_id=order_id, side=side, size=size, price=price,
                is_taker=is_taker, latency_ms=latency_ms, level_idx=lvl_tag
            )

    # ------------------------------------------------------------------
    # Live Fill Polling
    # ------------------------------------------------------------------

    async def poll_fills(self) -> list[FillEvent]:
        """
        Poll CLOB API for filled orders (live mode only).

        Uses get_trades(after=<timestamp>) — 2 requests (YES + NO token) instead of N.
        Called by LiveTradingBridge._poll_fills_loop() every ~1.5s.

        Real CLOB /data/trades response format:
        {
          "id": "uuid-trade",
          "maker_orders": [
            {
              "order_id": "0xa5aa...",    ← OUR maker order_id
              "matched_amount": "10",     ← size filled
              "price": "0.10",            ← fill price
              "side": "BUY",
              "outcome": "Down"
            }
          ],
          "trader_side": "MAKER"
        }

        Our order_id lives in trade['maker_orders'][N]['order_id'], NOT in trade root.
        Fallback: if get_trades() fails, falls back to get_order()×N.
        """
        if self.paper_mode or not self.clob_client:
            return []

        if not self._active_orders:
            return []

        filled: list[FillEvent] = []
        active_oids = set(self._active_orders.keys())
        already_filled: set[str] = set()  # deduplicate across YES/NO queries

        # Use after=30s ago to avoid full pagination (only recent trades)
        after_ts = int(time.time()) - 30

        try:
            from py_clob_client.clob_types import TradeParams

            loop = asyncio.get_event_loop()
            for token_id in [self.yes_token_id, self.no_token_id]:
                if not token_id:
                    continue

                # [v11.69-FREEDOM] Замеряем RTT на фоновых запросах для выхода из комы
                start_api = time.time()
                trades = await loop.run_in_executor(
                    None, 
                    lambda: self.clob_client.get_trades(TradeParams(asset_id=token_id, after=after_ts))
                )
                rtt = int((time.time() - start_api) * 1000)
                self._latency_history.append(rtt)
                
                if not isinstance(trades, list):
                    trades = trades.get('data', []) if isinstance(trades, dict) else []

                for trade in trades:
                    # Our fills are in maker_orders array (we are the maker)
                    maker_orders = trade.get('maker_orders', [])
                    for mo in maker_orders:
                        oid = mo.get('order_id', '')
                        if not oid or oid not in active_oids or oid in already_filled:
                            continue

                        info = self._active_orders.get(oid)
                        if not info or 'cancel_pending_at' in info:
                            continue

                        matched = float(mo.get('matched_amount', 0))
                        fill_price = float(mo.get('price', info.get('price', 0)))
                        
                        # [v11.64-ULTIMATE] Защита от пыли (Rounding Down)
                        # int() в Python отсекает дробную часть, что эквивалентно округлению вниз для положительных чисел.
                        # Это гарантирует, что модуль Merge получит только целые, реально существующие акции.
                        fill_size = int(matched) if matched >= 1.0 else 0

                        if fill_size <= 0:
                            continue

                        fill = await self.on_fill(oid, fill_size, fill_price)
                        if fill:
                            mo_side = mo.get('side', fill.side)
                            mo_outcome = mo.get('outcome', '')
                            logger.info(
                                f"[POLL] ✅ Fill: {fill.side} {fill.size}@{fill.price:.2f} "
                                f"(order={oid[:20]}… outcome={mo_outcome})"
                            )
                            filled.append(fill)
                            already_filled.add(oid)
                    # Check if we are the TAKER (Экстренные сбросы позиции)
                    taker_oid = trade.get('taker_order_id', '')
                    if taker_oid and taker_oid in active_oids and taker_oid not in already_filled:
                        info = self._active_orders.get(taker_oid)
                        if info and 'cancel_pending_at' not in info:
                            matched = float(trade.get('size', 0))
                            fill_price = float(trade.get('price', info.get('price', 0)))
                            fill_size = int(matched) if matched >= 1.0 else 0

                            if fill_size > 0:
                                fill = await self.on_fill(taker_oid, fill_size, fill_price)
                                if fill:
                                    mo_outcome = trade.get('outcome', '')
                                    logger.info(
                                        f"[POLL] ✅ TAKER Fill: {fill.side} {fill.size}@{fill.price:.2f} "
                                        f"(order={taker_oid[:20]}… outcome={mo_outcome})"
                                    )
                                    filled.append(fill)
                                    already_filled.add(taker_oid)
        except Exception as e:
            logger.warning(f"⁉️⁉️[POLL] get_trades failed ({e}), falling back to get_order()×N")
            filled = await self._poll_fills_fallback()

        return filled

    async def _poll_fills_fallback(self) -> list[FillEvent]:
        """Fallback: check each active order via get_order() individually."""
        filled: list[FillEvent] = []
        for oid, info in list(self._active_orders.items()):
            if 'cancel_pending_at' in info:
                continue
            try:
                order = self._clob_get_order(oid)
                if not order or not isinstance(order, dict):
                    continue
                status = order.get('status', '').lower()
                size_matched = int(float(order.get('size_matched', 0)))
                if status in ('matched', 'filled') and size_matched > 0:
                    fill = await self.on_fill(oid, size_matched, info['price'])
                    if fill:
                        logger.info(
                            f"[POLL] ✅ Fill (fallback): {fill.side} {fill.size}@{fill.price:.2f}"
                        )
                        filled.append(fill)
            except Exception as e:
                logger.debug(f"⁉️⁉️[POLL] fallback get_order error {oid[:16]}: {e}")
        return filled

    def _clob_get_order(self, order_id: str) -> Optional[dict]:
        """Sync wrapper for clob_client.get_order()."""
        try:
            return self.clob_client.get_order(order_id)
        except Exception as e:
            logger.debug(f"♣️[POLL] get_order({order_id[:16]}): {e}")
            return None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def purge_expired_cancels(self) -> list[str]:
        """
        Remove orders whose PENDING_CANCEL window has expired.
        Called by adapter after processing trades each tick.

        Returns: list of order_ids that were successfully cancelled.
        """
        import time
        now = time.time()
        expired = []
        for oid, info in list(self._active_orders.items()):
            cancel_at = info.get('cancel_pending_at')
            if cancel_at is not None:
                elapsed_ms = (now - cancel_at) * 1000
                if elapsed_ms >= CANCEL_RACE_WINDOW_MS:
                    self._active_orders.pop(oid)
                    expired.append(oid)
        return expired

    def is_pending_cancel(self, order_id: str) -> bool:
        """Check if order is in PENDING_CANCEL state."""
        info = self._active_orders.get(order_id)
        return info is not None and 'cancel_pending_at' in info

    def set_token_ids(self, yes_token_id: str, no_token_id: str) -> None:
        """[v9.69] Pre-fetch market params including FEE RATE."""
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self._token_params_cache.clear()
        
        if self.clob_client and not self.paper_mode:
            try:
                for tid in [yes_token_id, no_token_id]:
                    if not tid: continue
                    # Получаем шаг цены
                    tick_size = float(self.clob_client.get_tick_size(tid))
                    # [!] ПОЛУЧАЕМ РЕАЛЬНУЮ КОМИССИЮ РЫНКА (BPS)
                    try:
                        fee_bps = int(self.clob_client.get_fee_rate_bps(tid))
                    except:
                        fee_bps = 0 # Фолбэк на 0
                        
                    self._token_params_cache[tid] = {
                        'tick_size': 0.01,   # Для математики и округления в стратегии
                        'fee_bps': fee_bps
                    }
                logger.info(f"💾 [CACHE] Token params pre-fetched: {self._token_params_cache}")
            except Exception as e:
                logger.error(f"‼️ [CACHE] Failed to pre-fetch token params: {e}")

    def reset(self) -> None:
        """Reset for new market."""
        self._active_orders.clear()

    @property
    def active_count(self) -> int:
        return len(self._active_orders)

    def get_stats(self) -> dict:
        return {**self.stats, 'active_orders': self.active_count}

    # ------------------------------------------------------------------
    # Specialized Actions (CTF & Nuclear)
    # ------------------------------------------------------------------

    async def merge_positions(self, side: str, size: int) -> bool:
        """[v11.85] Физическое слияние позиций через SDK."""
        if self.paper_mode:
            logger.info(f"🧪 [PAPER_MERGE] Схлопнуто {size} пар для {side}")
            return True

        try:
            # side здесь — это condition_id, который пришел из стратегии
            resp = await self._call_api('merge_positions', side, size)
            logger.info(f"🚀 [CTF_MERGE] Успешно схлопнуто {size} пар. Ответ: {resp}")
            return True
        except Exception as e:
            logger.error(f"‼️ [MERGE_FAILED] Не удалось слить позиции: {e}")
            return False

    async def execute_nuclear_cancel(self) -> bool:
        """[v11.85] Алиас для гарантированной очистки рынка."""
        logger.warning("☢️ [NUCLEAR_CANCEL] Запуск полной зачистки стакана...")
        return await self.cancel_all_verified()

    # ------------------------------------------------------------------
    # API helper
    # ------------------------------------------------------------------

    async def _call_api(self, method: str, *args, max_retries: int = 3) -> Any:
        """[v11.64-ULTIMATE] Call clob_client with Identity Protection."""
        if self.clob_client is None:
            logger.error(f"‼️ [ENGINE_FATAL] Вызов {method} заблокирован: clob_client=None")
            return None

        # [CRITICAL] Защита от "Слепоты RPC": 
        # Если ключи авторизации превратились в строку ошибки (сбой Polygon), прерываем торговлю.
        creds = getattr(self.clob_client, 'creds', None)
        if creds is None or isinstance(creds, str):
            logger.error(f"⚠️ [IDENTITY_HALT] Вызов {method} отменен: API Credentials повреждены или не авторизованы.")
            return None

        import time
        fn = getattr(self.clob_client, method, None)
        if fn is None:
            logger.error(f"‼️[ENGINE_V6] clob_client has no method '{method}'")
            return None

        # [v11.60-HFT] Жесткий таймаут для защиты от лагов Cloudflare
        timeout_limit = 0.350 
        for attempt in range(max_retries):
            start_api = time.time()
            try:
                loop = asyncio.get_event_loop()
                # Используем asyncio.wait_for для обрыва ожидания
                if asyncio.iscoroutinefunction(fn):
                    res = await asyncio.wait_for(fn(*args), timeout=timeout_limit)
                else:
                    res = await asyncio.wait_for(loop.run_in_executor(None, fn, *args), timeout=timeout_limit)
                
                rtt = int((time.time() - start_api) * 1000)
                self._latency_history.append(rtt) # Собираем историю задержек
                return res
                
            except asyncio.TimeoutError:
                # Фикс NameError: используем fn.__name__ вместо method
                self._latency_history.append(1000) # Штрафной балл в историю
                logger.error(f"⏱️ [API TIMEOUT] Запрос {fn.__name__} висит > {timeout_limit}s! Биржа лагает.")
                return None
                
            except Exception as e:
                err_str = str(e)
                # [v9.38] NETWORK DROP & 429 RECOVERY
                is_network_drop = "Request exception" in err_str or "status_code=None" in err_str
                is_rate_limit = '429' in err_str or 'too many' in err_str.lower()
                is_server_err = any(code in err_str for code in ['500', '502', '503'])
                
                if (is_network_drop or is_rate_limit or is_server_err) and attempt < max_retries - 1:
                    # Резолвим 429 ошибку для LDM
                    if is_rate_limit:
                        self._write_to_orders_log({"event": "error", "type": "429", "error": err_str})
                    
                    wait = 0.3 * (attempt + 1)
                    logger.warning(f"⚠️ [NET_RETRY] {method} attempt {attempt+1} failed. Retry in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                
                logger.error(f"‼️ [SDK_FATAL] {method} failed after {attempt+1} attempts: {e}")
                raise

    def _get_rust_headers(self, method: str, request_path: str, payload_json: str, body_obj: any) -> dict:
        """
        Генерирует L2 заголовки. 
        Использует serialized_body для 100% гарантии совпадения подписи.
        """
        from py_clob_client.clob_types import RequestArgs
        from py_clob_client.headers.headers import create_level_2_headers

        # КЛЮЧ К УСПЕХУ: 
        # Мы передаем payload_json (нашу готовую строку) в поле serialized_body.
        # Это заставляет SDK использовать именно эти байты для подписи,
        # игнорируя внутренние настройки пробелов в json.dumps.
        req_args = RequestArgs(
            method=method.upper(),
            request_path=request_path,
            body=body_obj,
            serialized_body=payload_json  # <--- ВОТ ОНО!
        )
        
        # Генерируем заголовки
        headers = create_level_2_headers(self.clob_client.signer, self.clob_client.creds, req_args)
        
        # Очистка для Rust (только строки)
        safe_headers = {str(k): str(v) for k, v in headers.items() if v is not None}
        safe_headers['Content-Type'] = 'application/json'
        
        return safe_headers

    def _write_to_orders_log(self, entry: dict):
        """Вспомогательный метод для записи данных в JSONL для LDM анализатора."""
        import json, os
        from pathlib import Path
        # Определяем корень проекта (на 3 уровня выше этого файла)
        base_dir = Path(__file__).resolve().parent.parent.parent
        log_dir = base_dir / "logs"
        log_path = log_dir / "orders_log.jsonl"
        
        # Создаем папку логов, если её нет
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except: pass
            
        entry['ts_log'] = time.time()
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass
        
    def get_live_cfr(self) -> float:
        """
        Возвращает Cancel-to-Fill Ratio за последние 200 событий.
        Чем ниже число, тем эффективнее работает бот.
        """
        if not self._action_history:
            return 0.0
        
        cancels = self._action_history.count('C')
        fills = self._action_history.count('F')
        
        # Индекс эффективности: сколько отмен приходится на 1 филл
        return round(cancels / max(1, fills), 1)    

    def get_avg_latency(self) -> int:
        """[v11.60-HFT] Возвращает скользящую среднюю задержку REST API в мс."""
        if not self._latency_history:
            return 0
        return int(sum(self._latency_history) / len(self._latency_history))


