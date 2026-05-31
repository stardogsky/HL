"""
REST polling for HL Info endpoint.

Tasks:
- allMids poll (every 1s) → mark price snapshots for ALL coins
- outcomeMeta poll (every 60s) → detect new instances + targetPrice rotation
- spotMeta poll (every 5min) → szDecimals tracking (rare changes)
- latency probe (every 60s) → ping endpoint, measure RTT
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self, network: str, rest_url: str, writer: object,
                 all_mids_sec: float = 1.0,
                 outcome_meta_sec: float = 60.0,
                 spot_meta_sec: float = 300.0,
                 latency_probe_sec: float = 60.0):
        self.network = network
        self.rest_url = rest_url
        self.writer = writer
        self.all_mids_sec = all_mids_sec
        self.outcome_meta_sec = outcome_meta_sec
        self.spot_meta_sec = spot_meta_sec
        self.latency_probe_sec = latency_probe_sec
        self._session = None
        self._stats = {"all_mids": 0, "outcome_meta": 0, "spot_meta": 0, "latency": 0, "errors": 0}
        # Callback set by main: on outcomeMeta change → re-evaluate subscriptions
        self.outcome_meta_callback = None  # async callable(self.network, outcomes_raw)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _post(self, payload: dict) -> tuple[int, object, float]:
        """POST to /info. Returns (status, data, elapsed_ms)."""
        session = await self._get_session()
        t0 = time.time()
        try:
            async with session.post(
                self.rest_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                text = await resp.text()
                elapsed_ms = (time.time() - t0) * 1000
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {"_non_json": text[:500]}
                return resp.status, data, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            return -1, {"_error": str(e)}, elapsed_ms

    async def all_mids_loop(self):
        """Poll allMids every N seconds — mark price for all coins."""
        while True:
            try:
                status, data, elapsed_ms = await self._post({"type": "allMids"})
                if status == 200 and isinstance(data, dict):
                    payload = {
                        "ts_local": time.time(),
                        "elapsed_ms": elapsed_ms,
                        "mids": data,
                    }
                    await self.writer.write(self.network, "all_mids_rest", payload)
                    self._stats["all_mids"] += 1
                else:
                    self._stats["errors"] += 1
                    logger.warning(f"[{self.network}] allMids failed status={status}")
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[{self.network}] allMids loop error: {e}", exc_info=True)
            await asyncio.sleep(self.all_mids_sec)

    async def outcome_meta_loop(self):
        """Poll outcomeMeta every N seconds — detect new instances + targetPrice rotation."""
        while True:
            try:
                status, data, elapsed_ms = await self._post({"type": "outcomeMeta"})
                if status == 200 and isinstance(data, dict):
                    payload = {
                        "ts_local": time.time(),
                        "elapsed_ms": elapsed_ms,
                        "outcomes": data.get("outcomes", []),
                    }
                    await self.writer.write(self.network, "outcome_meta", payload)
                    self._stats["outcome_meta"] += 1

                    # Trigger rediscovery callback
                    if self.outcome_meta_callback:
                        try:
                            await self.outcome_meta_callback(self.network, data.get("outcomes", []))
                        except Exception as e:
                            logger.error(f"[{self.network}] outcomeMeta callback error: {e}", exc_info=True)
                else:
                    self._stats["errors"] += 1
                    logger.warning(f"[{self.network}] outcomeMeta failed status={status}")
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[{self.network}] outcomeMeta loop error: {e}", exc_info=True)
            await asyncio.sleep(self.outcome_meta_sec)

    async def spot_meta_loop(self):
        """Poll spotMeta every N seconds — szDecimals/tick info (rare changes)."""
        while True:
            try:
                status, data, elapsed_ms = await self._post({"type": "spotMeta"})
                if status == 200 and isinstance(data, dict):
                    payload = {
                        "ts_local": time.time(),
                        "elapsed_ms": elapsed_ms,
                        "data": data,
                    }
                    await self.writer.write(self.network, "spot_meta", payload)
                    self._stats["spot_meta"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[{self.network}] spotMeta loop error: {e}", exc_info=True)
            await asyncio.sleep(self.spot_meta_sec)

    async def latency_probe_loop(self):
        """Lightweight ping to measure RTT. Uses smallest possible request."""
        while True:
            try:
                # allMids is reasonable: small response, indicative of API health
                status, data, elapsed_ms = await self._post({"type": "allMids"})
                payload = {
                    "ts_local": time.time(),
                    "rtt_ms": elapsed_ms,
                    "status": status,
                    "ok": status == 200,
                }
                await self.writer.write(self.network, "latency", payload)
                self._stats["latency"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[{self.network}] latency probe error: {e}", exc_info=True)
            await asyncio.sleep(self.latency_probe_sec)

    async def fetch_outcome_meta_once(self) -> list:
        """One-shot fetch (used at startup before loops begin)."""
        status, data, _ = await self._post({"type": "outcomeMeta"})
        if status == 200 and isinstance(data, dict):
            return data.get("outcomes", [])
        return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def get_stats(self) -> dict:
        return dict(self._stats)
