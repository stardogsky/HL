#!/usr/bin/env python3
"""
hl_feeder.py — Hyperliquid → ZMQ Feeder (auto-discovery)

Reads HL collector JSONL files, converts to Polymarket-compatible
ZMQ messages, publishes on tcp://*:5575. Replacement for the prior
hardcoded-OUTCOME_ID feeder. Survives daily settlement without
human intervention.

Architecture (see HL/Auto_Discovery_Design.md):
    STEADY → PRE_SETTLE → TRANSITION → POST_SETTLE → STEADY
                              ↑                          │
                              └──── watchdog forces ─────┘
                                    if data silence

Defense in depth:
    L1 — Phase-gated state machine auto-detects active outcome
         from outcome_meta_*.jsonl.
    L2 — Internal watchdog: in STEADY with a presumed-active outcome,
         if no book message received for STALE_BOOK_ALARM_SEC, log
         CRITICAL and force re-discovery.
    L3 — Health file ~/HL/data/feeder_health.json updated every heartbeat
         so an external monitor can detect freeze even if logs are silent.

Bot config to use this feeder (unchanged):
    data_source: zmq://127.0.0.1:5575

Usage:
    python3 ~/HL/hl_feeder.py             # mainnet (default)
    python3 ~/HL/hl_feeder.py --testnet   # testnet
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import aiohttp
import zmq
import zmq.asyncio

# ─── Config ─────────────────────────────────────────────────────────────
ZMQ_BIND = "tcp://*:5575"
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

# Filter — what kind of outcomes this feeder tracks
TARGET_UNDERLYING = "BTC"
TARGET_PERIOD = "1d"

# Phase timing thresholds (seconds)
PRE_SETTLE_LEAD_SEC = 60        # T-60s before expiry → enter PRE_SETTLE
TRANSITION_TIMEOUT_SEC = 180    # T+180s after expiry → give up TRANSITION (retry)
POST_SETTLE_VERIFY_SEC = 180    # T+180s after switch → accept best-effort
STEADY_DISCOVERY_INTERVAL_SEC = 60  # In STEADY, failsafe re-discover every N seconds

# Watchdog (Layer 2) — kicks in only in STEADY with a known-active outcome
STALE_BOOK_ALARM_SEC = 120      # If no book msg for 120s while STEADY+active → CRITICAL + force rediscover
STALE_BOOK_WARN_SEC = 45        # First warning at 45s

# Heartbeat / health file (Layer 3)
HEARTBEAT_INTERVAL_SEC = 30
HEALTH_FILE = Path.home() / "HL" / "data" / "feeder_health.json"


# ─── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('hl_feeder')


# ════════════════════════════════════════════════════════════════════════
# OutcomeInfo — parsed outcome metadata
# ════════════════════════════════════════════════════════════════════════
@dataclass
class OutcomeInfo:
    outcome_id: int
    underlying: str
    period: str
    target_price: float
    expiry_str: str       # "20260517-0600"
    expiry_ts: float      # epoch seconds (UTC)
    raw_description: str

    @property
    def yes_token_id(self) -> str:
        return str(self.outcome_id * 10)

    @property
    def no_token_id(self) -> str:
        return str(self.outcome_id * 10 + 1)

    @property
    def yes_book_prefix(self) -> str:
        return f"book_h{self.yes_token_id}_"

    @property
    def no_book_prefix(self) -> str:
        return f"book_h{self.no_token_id}_"

    @property
    def yes_trades_prefix(self) -> str:
        return f"trades_h{self.yes_token_id}_"

    @property
    def no_trades_prefix(self) -> str:
        return f"trades_h{self.no_token_id}_"

    @property
    def slug(self) -> str:
        return f"hl-{self.underlying.lower()}-{self.period}-{int(self.target_price)}-{self.expiry_str}"

    @property
    def seconds_until_expiry(self) -> float:
        return self.expiry_ts - time.time()


def parse_outcome(outcome_data: dict) -> Optional[OutcomeInfo]:
    """Parse outcome dict from outcome_meta. Returns None unless matches TARGET filter.

    Filter rejects:
      - 'Recurring Fallback' (description='other')
      - 'Recurring Named Outcome' (description='index:N')
      - Other underlying / period
    """
    desc = outcome_data.get('description', '')
    if not desc.startswith('class:priceBinary'):
        return None

    parsed = {}
    for part in desc.split('|'):
        if ':' in part:
            k, v = part.split(':', 1)
            parsed[k.strip()] = v.strip()

    if parsed.get('underlying') != TARGET_UNDERLYING:
        return None
    if parsed.get('period') != TARGET_PERIOD:
        return None

    try:
        target_price = float(parsed.get('targetPrice', 0))
        expiry_str = parsed.get('expiry', '')
        expiry_dt = datetime.strptime(expiry_str, '%Y%m%d-%H%M').replace(tzinfo=timezone.utc)
        expiry_ts = expiry_dt.timestamp()
        outcome_id = int(outcome_data.get('outcome', 0))
    except (ValueError, KeyError, TypeError):
        return None

    return OutcomeInfo(
        outcome_id=outcome_id,
        underlying=parsed.get('underlying', ''),
        period=parsed.get('period', ''),
        target_price=target_price,
        expiry_str=expiry_str,
        expiry_ts=expiry_ts,
        raw_description=desc,
    )


def find_active_outcome(meta_data: dict) -> Optional[OutcomeInfo]:
    """Find single active outcome (expiry > now) matching filter.
    If multiple match → pick earliest expiry (current cycle)."""
    candidates = []
    for outcome_data in meta_data.get('outcomes', []):
        oc = parse_outcome(outcome_data)
        if oc is None:
            continue
        if oc.seconds_until_expiry > 0:
            candidates.append(oc)
    if not candidates:
        return None
    candidates.sort(key=lambda o: o.expiry_ts)
    return candidates[0]


# ════════════════════════════════════════════════════════════════════════
# Phase state machine
# ════════════════════════════════════════════════════════════════════════
class Phase(Enum):
    STEADY = "STEADY"
    PRE_SETTLE = "PRE_SETTLE"
    TRANSITION = "TRANSITION"
    POST_SETTLE = "POST_SETTLE"


# ════════════════════════════════════════════════════════════════════════
# JSONL tailer
# ════════════════════════════════════════════════════════════════════════
class JsonlTailer:
    def __init__(self, path: Optional[Path]):
        self.path = path
        self.position = 0

    def reset_to_end(self):
        if self.path and self.path.exists():
            self.position = self.path.stat().st_size

    async def get_new(self) -> list:
        if not self.path or not self.path.exists():
            return []
        try:
            with open(self.path, 'r') as f:
                f.seek(self.position)
                data = f.read()
                self.position = f.tell()
            if not data:
                return []
            results = []
            for line in data.strip().split('\n'):
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return results
        except Exception as e:
            logger.warning(f"Tailer error on {self.path.name if self.path else '?'}: {e}")
            return []


# ════════════════════════════════════════════════════════════════════════
# Format conversion
# ════════════════════════════════════════════════════════════════════════
def convert_orderbook(hl_msg: dict, is_yes: bool, token_id: str) -> dict:
    return {
        'asset_id': token_id,
        'is_yes': is_yes,
        'bids': [
            {'price': str(level.get('px', 0)), 'size': str(level.get('sz', 0))}
            for level in hl_msg.get('bids', [])
        ],
        'asks': [
            {'price': str(level.get('px', 0)), 'size': str(level.get('sz', 0))}
            for level in hl_msg.get('asks', [])
        ],
        'timestamp': hl_msg.get('ts_local', time.time()),
        'hl_coin': hl_msg.get('coin'),
        'hl_latency_ms': hl_msg.get('latency_ms', 0),
    }


def convert_trade(hl_msg: dict, is_yes: bool) -> dict:
    side_map = {'A': 'BUY', 'B': 'SELL'}
    return {
        'price': float(hl_msg.get('px', 0)),
        'size': float(hl_msg.get('sz', 0)),
        'side': side_map.get(hl_msg.get('side', 'A'), 'BUY'),
        'is_yes': is_yes,
        'timestamp': hl_msg.get('ts_local', time.time()),
        'asset': TARGET_UNDERLYING,
        'maker_address': hl_msg.get('seller', '') or '',
        'hl_buyer': hl_msg.get('buyer'),
        'hl_seller': hl_msg.get('seller'),
        'hl_tid': hl_msg.get('tid'),
    }


def build_market_info(outcome: OutcomeInfo, ob_count: int, trade_count: int) -> dict:
    duration_map = {'1d': 86400, '1h': 3600, '15m': 900, '15min': 900}
    duration_sec = duration_map.get(outcome.period, 86400)
    now_ts = int(time.time())
    return {
        'slug': outcome.slug,
        'condition_id': f"hl-outcome-{outcome.outcome_id}",
        'yes_token_id': outcome.yes_token_id,
        'no_token_id': outcome.no_token_id,
        'window_timestamp': int(outcome.expiry_ts - duration_sec),
        'window_end': int(outcome.expiry_ts),
        'time_remaining_sec': max(0, int(outcome.expiry_ts - now_ts)),
        'transition_state': 'ACTIVE' if outcome.expiry_ts > now_ts else 'EXPIRED',
        'updates_count': ob_count,
        'trades_count': trade_count,
        'strike_price': outcome.target_price,
        'underlying': outcome.underlying,
    }


# ════════════════════════════════════════════════════════════════════════
# Main feeder with auto-discovery + watchdog + health file
# ════════════════════════════════════════════════════════════════════════
class HLFeeder:
    def __init__(self, network: str = 'mainnet'):
        self.network = network
        self.data_root = Path.home() / "HL" / "data" / "raw" / network
        self.running = False

        self.ctx = zmq.asyncio.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.setsockopt(zmq.SNDHWM, 5000)
        self.pub.setsockopt(zmq.LINGER, 0)
        self.pub.bind(ZMQ_BIND)

        self.current_outcome: Optional[OutcomeInfo] = None
        self.phase: Phase = Phase.STEADY
        self.transition_started_ts: float = 0.0
        self.post_settle_started_ts: float = 0.0
        self.last_steady_discovery_ts: float = 0.0

        self.tailers: dict = {}
        self.last_btc_price = 0.0
        self.last_book_msg_ts: float = 0.0   # watchdog signal
        self.last_book_warn_ts: float = 0.0  # throttle warnings
        self.last_force_rediscover_ts: float = 0.0
        self.startup_ts: float = time.time()

        self.stats = {
            'ob_yes': 0, 'ob_no': 0,
            'tr_yes': 0, 'tr_no': 0,
            'mi': 0, 'btc': 0,
            'switches': 0,
            'watchdog_alarms': 0,
            'forced_rediscoveries': 0,
        }

    async def publish(self, msg_type: str, data: dict, stat_key: Optional[str] = None):
        try:
            payload = json.dumps({"type": msg_type, "data": data}, default=str)
            await self.pub.send_string(payload, flags=1)  # NOBLOCK
            if stat_key:
                self.stats[stat_key] = self.stats.get(stat_key, 0) + 1
        except Exception as e:
            logger.warning(f"publish {msg_type} error: {e}")

    def _today_dir(self) -> Path:
        return self.data_root / datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _latest_file(self, prefix: str) -> Optional[Path]:
        base = self._today_dir()
        if not base.exists():
            return None
        files = sorted(
            (p for p in base.glob(f"{prefix}*.jsonl") if not p.name.endswith('.gz')),
            key=lambda p: p.stat().st_mtime
        )
        return files[-1] if files else None

    def _read_latest_meta(self) -> Optional[dict]:
        """Read last line of outcome_meta_*.jsonl from today's dir."""
        meta_path = self._latest_file('outcome_meta_')
        if meta_path is None:
            return None
        try:
            with open(meta_path, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 16384))
                data = f.read().decode('utf-8', errors='ignore')
                lines = [l for l in data.strip().split('\n') if l]
                if lines:
                    return json.loads(lines[-1])
        except Exception as e:
            logger.warning(f"_read_latest_meta error: {e}")
        return None

    def _discover_active_outcome(self) -> Optional[OutcomeInfo]:
        """Read latest meta and find an active outcome matching filter."""
        meta = self._read_latest_meta()
        if meta is None:
            return None
        return find_active_outcome(meta)

    def _attach_tailers_for(self, outcome: OutcomeInfo) -> bool:
        """Set up tailers for the outcome's files. Returns True if all 4 found."""
        targets = {
            'book_yes': outcome.yes_book_prefix,
            'book_no': outcome.no_book_prefix,
            'trades_yes': outcome.yes_trades_prefix,
            'trades_no': outcome.no_trades_prefix,
        }
        all_ok = True
        for key, prefix in targets.items():
            path = self._latest_file(prefix)
            if path is None:
                logger.warning(f"⚠️  no file for {key} (prefix '{prefix}')")
                self.tailers[key] = JsonlTailer(None)
                all_ok = False
                continue
            t = JsonlTailer(path)
            t.reset_to_end()
            self.tailers[key] = t
            logger.info(f"📂 [{key}] {path.name}")
        return all_ok

    def _switch_to_outcome(self, new_outcome: OutcomeInfo):
        old_id = self.current_outcome.outcome_id if self.current_outcome else None
        self.current_outcome = new_outcome
        self._attach_tailers_for(new_outcome)
        self.stats['switches'] += 1
        # Reset watchdog signal — give the new outcome time to start flowing
        self.last_book_msg_ts = time.time()
        self.last_book_warn_ts = 0.0
        logger.info(
            f"🎯 SWITCH: {old_id} → {new_outcome.outcome_id} "
            f"({new_outcome.slug}) | strike=${new_outcome.target_price:,.0f} | "
            f"expires_in={new_outcome.seconds_until_expiry:.0f}s"
        )

    def _force_rediscover(self, reason: str) -> bool:
        """Watchdog escalation: clear state and re-discover. Returns True if found new."""
        now = time.time()
        if now - self.last_force_rediscover_ts < 30:
            # Don't thrash — at most one forced rediscover per 30s
            return False
        self.last_force_rediscover_ts = now
        self.stats['forced_rediscoveries'] += 1
        logger.error(f"🚨 WATCHDOG forcing rediscover (reason: {reason})")
        new_oc = self._discover_active_outcome()
        if new_oc:
            if self.current_outcome and new_oc.outcome_id == self.current_outcome.outcome_id:
                # Same outcome — files may have rolled over within the hour;
                # re-attach to latest files anyway
                logger.warning(f"   Same outcome {new_oc.outcome_id} — re-attaching tailers")
                self._attach_tailers_for(new_oc)
                self.last_book_msg_ts = time.time()
                self.last_book_warn_ts = 0.0
                return False
            self._switch_to_outcome(new_oc)
            self.phase = Phase.POST_SETTLE
            self.post_settle_started_ts = now
            return True
        logger.error("   ✗ No active outcome found via meta — collector dead?")
        return False

    def _check_watchdog(self) -> None:
        """Layer 2: in STEADY with presumed-active outcome, alert + auto-rediscover
        if no book messages have been received recently."""
        if self.phase != Phase.STEADY or self.current_outcome is None:
            return
        if self.current_outcome.seconds_until_expiry <= 0:
            # Expiry passed — main phase logic handles this
            return
        now = time.time()
        # Give a grace period after startup or recent switch
        if now - self.last_book_msg_ts < STALE_BOOK_WARN_SEC:
            return
        # If we've never received any book msg yet, anchor on startup_ts
        if self.last_book_msg_ts == 0.0:
            ref_ts = max(self.startup_ts, self.last_force_rediscover_ts or self.startup_ts)
            silence = now - ref_ts
        else:
            silence = now - self.last_book_msg_ts

        if silence >= STALE_BOOK_ALARM_SEC:
            logger.critical(
                f"🚨 STALE BOOK ALARM: no orderbook for {silence:.0f}s in STEADY "
                f"(outcome {self.current_outcome.outcome_id}, "
                f"T-{self.current_outcome.seconds_until_expiry:.0f}s). Force rediscover."
            )
            self.stats['watchdog_alarms'] += 1
            self._force_rediscover(reason=f"stale_book_{int(silence)}s")
        elif silence >= STALE_BOOK_WARN_SEC and (now - self.last_book_warn_ts) > 30:
            self.last_book_warn_ts = now
            logger.warning(
                f"⚠️  Book silence {silence:.0f}s (alarm at {STALE_BOOK_ALARM_SEC}s) "
                f"on outcome {self.current_outcome.outcome_id}"
            )

    # ─── Phase state machine ────────────────────────────────────────────
    async def update_phase(self):
        now = time.time()

        if self.current_outcome is None:
            # No outcome — keep trying to discover one
            if now - self.last_steady_discovery_ts > 5:
                self.last_steady_discovery_ts = now
                new_oc = self._discover_active_outcome()
                if new_oc:
                    self._switch_to_outcome(new_oc)
                    self.phase = Phase.POST_SETTLE
                    self.post_settle_started_ts = now
                    logger.info("→ POST_SETTLE: initial outcome discovered")
            return

        secs_to_expiry = self.current_outcome.seconds_until_expiry

        if self.phase == Phase.STEADY:
            # Failsafe periodic check
            if now - self.last_steady_discovery_ts > STEADY_DISCOVERY_INTERVAL_SEC:
                self.last_steady_discovery_ts = now
                if secs_to_expiry < 0:
                    logger.warning(
                        f"⚠️ STEADY but outcome already expired ({-secs_to_expiry:.0f}s ago) "
                        f"— entering TRANSITION"
                    )
                    self.phase = Phase.TRANSITION
                    self.transition_started_ts = now
                    return

            # Normal STEADY → PRE_SETTLE
            if 0 < secs_to_expiry < PRE_SETTLE_LEAD_SEC:
                logger.info(
                    f"→ PRE_SETTLE: outcome {self.current_outcome.outcome_id} "
                    f"expires in {secs_to_expiry:.0f}s"
                )
                self.phase = Phase.PRE_SETTLE

        elif self.phase == Phase.PRE_SETTLE:
            if secs_to_expiry <= 0:
                logger.info(
                    f"→ TRANSITION: outcome {self.current_outcome.outcome_id} "
                    f"settled, searching for new"
                )
                self.phase = Phase.TRANSITION
                self.transition_started_ts = now

        elif self.phase == Phase.TRANSITION:
            new_oc = self._discover_active_outcome()
            if new_oc and new_oc.outcome_id != self.current_outcome.outcome_id:
                self._switch_to_outcome(new_oc)
                self.phase = Phase.POST_SETTLE
                self.post_settle_started_ts = now
                logger.info(f"→ POST_SETTLE: switched to outcome {new_oc.outcome_id}")
            elif now - self.transition_started_ts > TRANSITION_TIMEOUT_SEC:
                logger.error(
                    f"⚠️ TRANSITION TIMEOUT: no new {TARGET_UNDERLYING} {TARGET_PERIOD} "
                    f"outcome after {TRANSITION_TIMEOUT_SEC}s. Falling back to STEADY (retry)."
                )
                self.phase = Phase.STEADY
                self.last_steady_discovery_ts = now

        elif self.phase == Phase.POST_SETTLE:
            # Verify we're actually receiving book data on the new outcome
            had_any = self.last_book_msg_ts >= self.post_settle_started_ts
            if had_any:
                logger.info(
                    f"→ STEADY: outcome {self.current_outcome.outcome_id} confirmed "
                    f"(book data flowing)"
                )
                self.phase = Phase.STEADY
                self.last_steady_discovery_ts = now
            elif now - self.post_settle_started_ts > POST_SETTLE_VERIFY_SEC:
                logger.warning(
                    f"⚠️ POST_SETTLE TIMEOUT: outcome {self.current_outcome.outcome_id} "
                    f"no book data after {POST_SETTLE_VERIFY_SEC}s. "
                    f"Accepting → STEADY (watchdog will retry if still silent)."
                )
                self.phase = Phase.STEADY
                self.last_steady_discovery_ts = now

        self._check_watchdog()

    # ─── Reading loops ──────────────────────────────────────────────────
    async def book_loop(self, side: str):
        is_yes = (side == 'yes')
        key = f'book_{side}'
        stat = 'ob_yes' if is_yes else 'ob_no'
        while self.running:
            try:
                t = self.tailers.get(key)
                if t and self.current_outcome:
                    token_id = (self.current_outcome.yes_token_id if is_yes
                                else self.current_outcome.no_token_id)
                    new_msgs = await t.get_new()
                    if new_msgs:
                        self.last_book_msg_ts = time.time()
                    for hl in new_msgs:
                        await self.publish('orderbook',
                                           convert_orderbook(hl, is_yes, token_id),
                                           stat)
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"book_loop({side}): {e}")
                await asyncio.sleep(1)

    async def trades_loop(self, side: str):
        is_yes = (side == 'yes')
        key = f'trades_{side}'
        stat = 'tr_yes' if is_yes else 'tr_no'
        while self.running:
            try:
                t = self.tailers.get(key)
                if t and self.current_outcome:
                    for hl in await t.get_new():
                        await self.publish('trade', convert_trade(hl, is_yes), stat)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"trades_loop({side}): {e}")
                await asyncio.sleep(1)

    async def market_info_loop(self):
        """Broadcast market_info every second from current outcome."""
        while self.running:
            try:
                if self.current_outcome is not None:
                    ob_total = self.stats['ob_yes'] + self.stats['ob_no']
                    tr_total = self.stats['tr_yes'] + self.stats['tr_no']
                    mi = build_market_info(self.current_outcome, ob_total, tr_total)
                    await self.publish('market_info', mi, 'mi')
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"market_info_loop: {e}")
                await asyncio.sleep(2)

    async def btc_loop(self):
        """Fetch BTC from Binance, broadcast as btc_update at 1Hz."""
        last = 0.0
        while self.running:
            try:
                async with aiohttp.ClientSession() as sess:
                    while self.running:
                        try:
                            async with sess.get(
                                BINANCE_URL,
                                timeout=aiohttp.ClientTimeout(total=3)
                            ) as r:
                                if r.status == 200:
                                    d = await r.json()
                                    px = float(d.get('price', 0))
                                    if px > 0:
                                        delta = ((px - last) / last * 100) if last > 0 else 0.0
                                        last = px
                                        self.last_btc_price = px
                                        await self.publish('btc_update', {
                                            'btc_price': px,
                                            'btc_ts': time.time(),
                                            'vol_ratio': 1.0,
                                            'btc_delta': delta,
                                            'gateway_ts': time.time(),
                                        }, 'btc')
                        except Exception:
                            pass
                        await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"btc_loop: {e}")
                await asyncio.sleep(5)

    async def phase_loop(self):
        """Drive the phase state machine + watchdog at appropriate frequency."""
        while self.running:
            try:
                await self.update_phase()
                if self.phase == Phase.STEADY:
                    await asyncio.sleep(2.0)
                elif self.phase == Phase.PRE_SETTLE:
                    await asyncio.sleep(0.5)
                elif self.phase == Phase.TRANSITION:
                    await asyncio.sleep(2.0)
                elif self.phase == Phase.POST_SETTLE:
                    await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"phase_loop: {e}")
                await asyncio.sleep(2)

    async def file_refresh_loop(self):
        """Re-discover hourly files every minute (handles hour rollover)."""
        while self.running:
            await asyncio.sleep(60)
            try:
                if self.current_outcome:
                    for key, prefix_attr in [
                        ('book_yes', 'yes_book_prefix'),
                        ('book_no', 'no_book_prefix'),
                        ('trades_yes', 'yes_trades_prefix'),
                        ('trades_no', 'no_trades_prefix'),
                    ]:
                        prefix = getattr(self.current_outcome, prefix_attr)
                        latest = self._latest_file(prefix)
                        existing = self.tailers.get(key)
                        if latest and (not existing or existing.path != latest):
                            new_t = JsonlTailer(latest)
                            new_t.reset_to_end()
                            self.tailers[key] = new_t
                            logger.info(f"📂 [{key}] hourly rollover → {latest.name}")
            except Exception as e:
                logger.warning(f"file_refresh: {e}")

    def _write_health(self):
        try:
            HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
            now = time.time()
            payload = {
                'ts': now,
                'iso': datetime.now(timezone.utc).isoformat(),
                'network': self.network,
                'phase': self.phase.value,
                'current_outcome_id': (self.current_outcome.outcome_id
                                       if self.current_outcome else None),
                'current_slug': (self.current_outcome.slug
                                 if self.current_outcome else None),
                'seconds_to_expiry': (self.current_outcome.seconds_until_expiry
                                      if self.current_outcome else None),
                'last_book_msg_ts': self.last_book_msg_ts,
                'seconds_since_last_book': (now - self.last_book_msg_ts
                                            if self.last_book_msg_ts > 0 else None),
                'last_btc_price': self.last_btc_price,
                'stats': dict(self.stats),
                'uptime_sec': now - self.startup_ts,
            }
            tmp = HEALTH_FILE.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(HEALTH_FILE)
        except Exception as e:
            logger.warning(f"health write failed: {e}")

    async def heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
            s = self.stats
            oc_id = self.current_outcome.outcome_id if self.current_outcome else 'NONE'
            secs_left = (self.current_outcome.seconds_until_expiry
                         if self.current_outcome else 0)
            book_age = (time.time() - self.last_book_msg_ts
                        if self.last_book_msg_ts > 0 else -1)
            logger.info(
                f"💓 [FEEDER] phase={self.phase.value} oc=#{oc_id} T-{secs_left:.0f}s "
                f"| OB Y/N: {s['ob_yes']}/{s['ob_no']} (age:{book_age:.0f}s) "
                f"| TR Y/N: {s['tr_yes']}/{s['tr_no']} | MI: {s['mi']} "
                f"| switches: {s['switches']} | watchdog_alarms: {s['watchdog_alarms']} "
                f"| BTC: ${self.last_btc_price:,.0f}"
            )
            self._write_health()

    async def run(self):
        self.running = True
        logger.info(f"🚀 [FEEDER] Network: {self.network} | ZMQ: {ZMQ_BIND}")
        logger.info(
            f"🚀 [FEEDER] Filter: underlying={TARGET_UNDERLYING}, period={TARGET_PERIOD}"
        )
        logger.info(
            f"🚀 [FEEDER] Watchdog: alarm if STEADY + no book {STALE_BOOK_ALARM_SEC}s "
            f"| Health file: {HEALTH_FILE}"
        )

        # Initial discovery
        retries = 0
        while self.running:
            oc = self._discover_active_outcome()
            if oc:
                self._switch_to_outcome(oc)
                self.phase = Phase.POST_SETTLE
                self.post_settle_started_ts = time.time()
                break
            retries += 1
            logger.warning(
                f"Waiting for active {TARGET_UNDERLYING} {TARGET_PERIOD} outcome... ({retries})"
            )
            if retries > 24:
                logger.error(
                    f"No active {TARGET_UNDERLYING} {TARGET_PERIOD} outcome after 2min. "
                    f"Is hl_collector running on {self.network}?"
                )
                return
            await asyncio.sleep(5)

        tasks = [
            asyncio.create_task(self.book_loop('yes')),
            asyncio.create_task(self.book_loop('no')),
            asyncio.create_task(self.trades_loop('yes')),
            asyncio.create_task(self.trades_loop('no')),
            asyncio.create_task(self.market_info_loop()),
            asyncio.create_task(self.btc_loop()),
            asyncio.create_task(self.phase_loop()),
            asyncio.create_task(self.file_refresh_loop()),
            asyncio.create_task(self.heartbeat_loop()),
        ]
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 KeyboardInterrupt — stopping...")
        finally:
            self.running = False
            for t in tasks:
                t.cancel()
            try:
                self.pub.close()
                self.ctx.term()
            except Exception:
                pass
            logger.info("👋 Stopped.")


def main():
    p = argparse.ArgumentParser(description="HL → ZMQ feeder with auto-discovery")
    p.add_argument('--testnet', action='store_true', help='Use testnet data dir')
    p.add_argument('--dry-run', action='store_true',
                   help='Discover current outcome and exit (no ZMQ bind)')
    args = p.parse_args()

    network = 'testnet' if args.testnet else 'mainnet'

    if args.dry_run:
        data_root = Path.home() / "HL" / "data" / "raw" / network
        today = data_root / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        meta_files = sorted(today.glob('outcome_meta_*.jsonl'))
        if not meta_files:
            print(f"NO_META_FILES in {today}")
            sys.exit(2)
        with open(meta_files[-1], 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 16384))
            data = f.read().decode('utf-8', errors='ignore')
            lines = [l for l in data.strip().split('\n') if l]
            meta = json.loads(lines[-1])
        oc = find_active_outcome(meta)
        if oc is None:
            print(f"NO_ACTIVE_OUTCOME (filter={TARGET_UNDERLYING}/{TARGET_PERIOD})")
            sys.exit(3)
        print(f"ACTIVE_OUTCOME id={oc.outcome_id}")
        print(f"  slug={oc.slug}")
        print(f"  strike=${oc.target_price:,.0f}")
        print(f"  expires_in={oc.seconds_until_expiry:.0f}s")
        print(f"  yes_token={oc.yes_token_id}  no_token={oc.no_token_id}")
        print(f"  yes_prefix={oc.yes_book_prefix}  no_prefix={oc.no_book_prefix}")
        sys.exit(0)

    feeder = HLFeeder(network=network)
    try:
        asyncio.run(feeder.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
