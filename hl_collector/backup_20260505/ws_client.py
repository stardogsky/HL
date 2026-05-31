"""
WebSocket client per network endpoint.

Responsibilities:
- Connect, subscribe to specified channels
- Dispatch incoming messages to writer
- Reconnect on disconnect with exponential backoff
- Write gap markers when reconnect happens
- Track subscriptions to resub on reconnect
- Measure message receive latency (ts_local - ts_exchange)

Each outcome → 4 subscription types:
  - l2Book (per coin: YES + NO)
  - bbo (per coin)
  - trades (per coin)
  - activeAssetCtx (per coin)
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


@dataclass
class WsClient:
    network: str
    ws_url: str
    writer: object  # JsonlWriter
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    ping_interval: float = 30.0
    ping_timeout: float = 10.0

    _ws: object = None
    _subscriptions: list = field(default_factory=list)  # list of subscription dicts to resub
    _connected: bool = False
    _msg_count: int = 0
    _connect_count: int = 0
    _last_msg_ts: float = 0.0

    async def connect_and_run(self):
        """Outer loop with reconnect."""
        delay = self.reconnect_initial_delay
        gap_start_ts = None

        while True:
            try:
                logger.info(f"[{self.network}] connecting to {self.ws_url}")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    max_size=10 * 1024 * 1024,  # 10MB messages allowed
                ) as ws:
                    self._ws = ws
                    self._connect_count += 1
                    self._connected = True

                    # Write gap-end marker if we were in a gap
                    if gap_start_ts is not None:
                        await self._write_gap_event(gap_start_ts, time.time(), reason="reconnect_success")
                        gap_start_ts = None

                    # Resubscribe (throttled to avoid HL server-side rate limit
                    # on subscribe burst — empirically threshold sits between 16
                    # and 100 subs/sec per IP. Verified via burst test 2026-05-05:
                    # T4=16 OK, T5=100 disconnect at +0.85s. 67/sec gives margin.)
                    for sub in self._subscriptions:
                        await self._send_subscribe(sub)

                    delay = self.reconnect_initial_delay  # reset backoff on success
                    logger.info(f"[{self.network}] connected, {len(self._subscriptions)} subscriptions resubscribed")

                    # Receive loop
                    async for raw in ws:
                        self._last_msg_ts = time.time()
                        await self._handle_message(raw)
                        self._msg_count += 1

            except (ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                self._connected = False
                if gap_start_ts is None:
                    gap_start_ts = time.time()
                logger.warning(f"[{self.network}] disconnected: {e}; reconnecting in {delay:.1f}s")
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_delay)

            except Exception as e:
                self._connected = False
                logger.error(f"[{self.network}] unexpected error: {e}", exc_info=True)
                if gap_start_ts is None:
                    gap_start_ts = time.time()
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_delay)

    async def subscribe(self, subscription: dict):
        """Add subscription. If connected, send immediately. Always tracked for resub."""
        if subscription not in self._subscriptions:
            self._subscriptions.append(subscription)
        if self._connected:
            await self._send_subscribe(subscription)

    async def unsubscribe(self, subscription: dict):
        """Remove subscription."""
        if subscription in self._subscriptions:
            self._subscriptions.remove(subscription)
        if self._connected:
            msg = {"method": "unsubscribe", "subscription": subscription}
            try:
                await self._ws.send(json.dumps(msg))
            except Exception as e:
                logger.warning(f"[{self.network}] unsubscribe send failed: {e}")

    async def _send_subscribe(self, subscription: dict):
        msg = {"method": "subscribe", "subscription": subscription}
        try:
            await self._ws.send(json.dumps(msg))
            logger.debug(f"[{self.network}] subscribed: {subscription}")
        except Exception as e:
            logger.warning(f"[{self.network}] subscribe send failed: {e}")

    async def _handle_message(self, raw: str):
        """Parse one WS message and dispatch to writer."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[{self.network}] non-JSON message: {raw[:200]}")
            return

        channel = msg.get("channel")
        data = msg.get("data")
        ts_local = time.time()

        # Skip subscription acks and pongs
        if channel == "subscriptionResponse":
            return
        if channel == "pong":
            return
        if channel is None:
            return

        # Route by channel type
        if channel == "l2Book":
            await self._handle_l2book(data, ts_local)
        elif channel == "bbo":
            await self._handle_bbo(data, ts_local)
        elif channel == "trades":
            await self._handle_trades(data, ts_local)
        elif channel == "activeAssetCtx" or channel == "activeSpotAssetCtx":
            await self._handle_asset_ctx(data, ts_local, channel)
        elif channel == "allMids":
            await self._handle_all_mids(data, ts_local)
        else:
            # Unknown channel — log raw for inspection (don't lose data)
            await self.writer.write(self.network, "unknown", {
                "ts_local": ts_local,
                "channel": channel,
                "raw": data,
            })

    async def _handle_l2book(self, data: dict, ts_local: float):
        coin = data.get("coin")
        levels = data.get("levels", [[], []])
        ts_exchange = data.get("time")

        payload = {
            "ts_local": ts_local,
            "ts_exchange": ts_exchange,
            "latency_ms": (ts_local * 1000 - ts_exchange) if ts_exchange else None,
            "coin": coin,
            "bids": levels[0] if len(levels) > 0 else [],
            "asks": levels[1] if len(levels) > 1 else [],
        }
        await self.writer.write(self.network, "book", payload, coin=coin)

    async def _handle_bbo(self, data: dict, ts_local: float):
        coin = data.get("coin")
        bbo = data.get("bbo", [None, None])
        ts_exchange = data.get("time")

        bid = bbo[0] if len(bbo) > 0 else None
        ask = bbo[1] if len(bbo) > 1 else None

        payload = {
            "ts_local": ts_local,
            "ts_exchange": ts_exchange,
            "latency_ms": (ts_local * 1000 - ts_exchange) if ts_exchange else None,
            "coin": coin,
            "bid_px": bid["px"] if bid else None,
            "bid_sz": bid["sz"] if bid else None,
            "bid_n": bid["n"] if bid else None,
            "ask_px": ask["px"] if ask else None,
            "ask_sz": ask["sz"] if ask else None,
            "ask_n": ask["n"] if ask else None,
        }
        await self.writer.write(self.network, "bbo", payload, coin=coin)

    async def _handle_trades(self, data: list, ts_local: float):
        """Each trade gets its own line."""
        if not isinstance(data, list):
            return
        for trade in data:
            coin = trade.get("coin")
            users = trade.get("users", [None, None])
            payload = {
                "ts_local": ts_local,
                "ts_exchange": trade.get("time"),
                "latency_ms": (ts_local * 1000 - trade["time"]) if trade.get("time") else None,
                "coin": coin,
                "side": trade.get("side"),
                "px": trade.get("px"),
                "sz": trade.get("sz"),
                "tid": trade.get("tid"),
                "hash": trade.get("hash"),
                "buyer": users[0] if len(users) > 0 else None,
                "seller": users[1] if len(users) > 1 else None,
            }
            await self.writer.write(self.network, "trades", payload, coin=coin)

    async def _handle_asset_ctx(self, data: dict, ts_local: float, channel: str):
        coin = data.get("coin")
        ctx = data.get("ctx", {})
        payload = {
            "ts_local": ts_local,
            "channel": channel,
            "coin": coin,
            "ctx": ctx,
        }
        await self.writer.write(self.network, "asset_ctx", payload, coin=coin)

    async def _handle_all_mids(self, data: dict, ts_local: float):
        # Note: usually pulled via REST, but allMids sub also exists
        mids = data.get("mids", {})
        payload = {
            "ts_local": ts_local,
            "mids": mids,
        }
        await self.writer.write(self.network, "all_mids_ws", payload)

    async def _write_gap_event(self, start_ts: float, end_ts: float, reason: str):
        await self.writer.write(self.network, "gaps", {
            "ts_local_start": start_ts,
            "ts_local_end": end_ts,
            "duration_sec": end_ts - start_ts,
            "reason": reason,
        })
        logger.warning(f"[{self.network}] GAP {end_ts - start_ts:.1f}s: {reason}")

    def get_stats(self) -> dict:
        return {
            "connected": self._connected,
            "msg_count": self._msg_count,
            "connect_count": self._connect_count,
            "subscriptions": len(self._subscriptions),
            "last_msg_age_sec": (time.time() - self._last_msg_ts) if self._last_msg_ts else None,
        }
