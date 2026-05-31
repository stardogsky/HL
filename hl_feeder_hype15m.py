#!/usr/bin/env python3
"""
hl_feeder_hype15m.py — Hyperliquid TESTNET HYPE 15m → ZMQ Feeder

Auto-discovers active HYPE 15m outcome (settles every 15 min).
Phase-gated state machine: STEADY → PRE_SETTLE → TRANSITION → POST_SETTLE → STEADY.

Filter: outcome description must contain `class:priceBinary` AND `underlying:HYPE` AND `period:15m`.
Skips joke outcomes (Akami, Canned Tuna, etc.) and Recurring Fallback / Named Outcome entries.

Bot config to use this feeder:
    data_source: zmq://127.0.0.1:5576
    market_duration_sec: 900  # native 15min regime!

Usage:
    python3 ~/HL/hl_feeder_hype15m.py
"""
import asyncio
import json
import time
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import zmq
import zmq.asyncio
import aiohttp

# ─── Config ─────────────────────────────────────────────────────────────
NETWORK = "testnet"
DATA_ROOT = Path.home() / "HL" / "data" / "raw" / NETWORK
ZMQ_BIND = "tcp://*:5576"  # different port from mainnet feeder (5575)
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

# Filter criteria — what kind of outcomes we track
TARGET_UNDERLYING = "HYPE"
TARGET_PERIOD = "15m"

# Phase timing thresholds (seconds)
PRE_SETTLE_LEAD_SEC = 30        # T-30s before expiry → enter PRE_SETTLE
TRANSITION_TIMEOUT_SEC = 120    # T+120s after expiry → give up TRANSITION (alert)
POST_SETTLE_VERIFY_SEC = 180    # T+180s after switch → give up POST_SETTLE verify
STEADY_DISCOVERY_INTERVAL_SEC = 60  # In STEADY, check meta every N seconds (failsafe)

# ─── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('hl_feeder_hype')


# ════════════════════════════════════════════════════════════════════════
# OutcomeInfo — parsed outcome metadata
# ════════════════════════════════════════════════════════════════════════
@dataclass
class OutcomeInfo:
    outcome_id: int
    underlying: str
    period: str
    target_price: float
    expiry_str: str       # "20260507-1730"
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
    """Parse outcome dict from outcome_meta. Returns None if not a valid HYPE 15m outcome."""
    desc = outcome_data.get('description', '')
    # Filter joke / fallback outcomes
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


def find_active_hype_15m(meta_data: dict) -> Optional[OutcomeInfo]:
    """Find single active HYPE 15m outcome (expiry > now). 
    If multiple match — pick earliest expiry (current cycle, not future)."""
    candidates = []
    for outcome_data in meta_data.get('outcomes', []):
        oc = parse_outcome(outcome_data)
        if oc is None:
            continue
        if oc.seconds_until_expiry > 0:
            candidates.append(oc)
    
    if not candidates:
        return None
    
    # Earliest expiry first (most likely the "current" cycle)
    candidates.sort(key=lambda o: o.expiry_ts)
    return candidates[0]


# ════════════════════════════════════════════════════════════════════════
# Phase state machine
# ════════════════════════════════════════════════════════════════════════
class Phase(Enum):
    STEADY = "STEADY"           # Routine reading, no discovery checks
    PRE_SETTLE = "PRE_SETTLE"   # T-30s before expiry — getting ready
    TRANSITION = "TRANSITION"   # T+0..T+120s — actively looking for new outcome
    POST_SETTLE = "POST_SETTLE" # Just switched, verifying new files growing


# ════════════════════════════════════════════════════════════════════════
# JSONL tailer (same as mainnet feeder)
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
# Format conversion (same logic as mainnet feeder)
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
    duration_sec = duration_map.get(outcome.period, 900)
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
# Main feeder with auto-discovery
# ════════════════════════════════════════════════════════════════════════
class HypeFeeder:
    def __init__(self):
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

        self.tailers: dict = {}  # key → JsonlTailer
        self.last_btc_price = 0.0
        self.stats = {
            'ob_yes': 0, 'ob_no': 0,
            'tr_yes': 0, 'tr_no': 0,
            'mi': 0, 'btc': 0,
            'switches': 0,
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
        return DATA_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _latest_file(self, prefix: str) -> Optional[Path]:
        base = self._today_dir()
        if not base.exists():
            return None
        # Skip .gz compressed files — only .jsonl
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
        """Read latest meta and find active HYPE 15m outcome."""
        meta = self._read_latest_meta()
        if meta is None:
            return None
        return find_active_hype_15m(meta)

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
            t.reset_to_end()  # skip historical, get only new lines
            self.tailers[key] = t
            logger.info(f"📂 [{key}] {path.name}")
        return all_ok

    def _switch_to_outcome(self, new_outcome: OutcomeInfo):
        """Switch tailers and active state to new outcome."""
        old_id = self.current_outcome.outcome_id if self.current_outcome else None
        self.current_outcome = new_outcome
        self._attach_tailers_for(new_outcome)
        self.stats['switches'] += 1
        logger.info(
            f"🎯 SWITCH: {old_id} → {new_outcome.outcome_id} "
            f"({new_outcome.slug}) | strike=${new_outcome.target_price:.2f} | "
            f"expires_in={new_outcome.seconds_until_expiry:.0f}s"
        )

    def _are_files_growing(self) -> bool:
        """Check if YES and NO book files are receiving data (have non-zero stats since switch)."""
        # We approximate by checking if tailers exist and paths are recent
        for key in ('book_yes', 'book_no'):
            t = self.tailers.get(key)
            if t is None or t.path is None or not t.path.exists():
                return False
        return True

    # ─── Phase state machine ────────────────────────────────────────────
    async def update_phase(self):
        now = time.time()

        if self.current_outcome is None:
            # No outcome at all — stay in STEADY mode but try to discover periodically
            if now - self.last_steady_discovery_ts > 5:  # More aggressive on startup
                self.last_steady_discovery_ts = now
                new_oc = self._discover_active_outcome()
                if new_oc:
                    self._switch_to_outcome(new_oc)
                    self.phase = Phase.POST_SETTLE
                    self.post_settle_started_ts = now
                    logger.info(f"→ POST_SETTLE: initial outcome discovered")
            return

        secs_to_expiry = self.current_outcome.seconds_until_expiry

        if self.phase == Phase.STEADY:
            # Failsafe: occasional discovery in STEADY (in case we missed expiry transition)
            if now - self.last_steady_discovery_ts > STEADY_DISCOVERY_INTERVAL_SEC:
                self.last_steady_discovery_ts = now
                # If our outcome already expired (shouldn't happen in STEADY, but safe), look for new
                if secs_to_expiry < 0:
                    logger.warning(
                        f"⚠️ STEADY but outcome already expired ({-secs_to_expiry:.0f}s ago) — entering TRANSITION"
                    )
                    self.phase = Phase.TRANSITION
                    self.transition_started_ts = now
                    return

            # Normal STEADY → PRE_SETTLE check
            if secs_to_expiry < PRE_SETTLE_LEAD_SEC and secs_to_expiry > 0:
                logger.info(
                    f"→ PRE_SETTLE: outcome {self.current_outcome.outcome_id} "
                    f"expires in {secs_to_expiry:.0f}s"
                )
                self.phase = Phase.PRE_SETTLE

        elif self.phase == Phase.PRE_SETTLE:
            if secs_to_expiry <= 0:
                logger.info(
                    f"→ TRANSITION: outcome {self.current_outcome.outcome_id} "
                    f"settled, looking for new"
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
                    f"⚠️ TRANSITION TIMEOUT: no new HYPE 15m outcome after "
                    f"{TRANSITION_TIMEOUT_SEC}s. Falling back to STEADY (will retry)."
                )
                self.phase = Phase.STEADY
                self.last_steady_discovery_ts = now  # immediate retry

        elif self.phase == Phase.POST_SETTLE:
            if self._are_files_growing():
                # Verify by checking file is non-empty (could enhance with size delta later)
                meta_present = self.tailers.get('book_yes') and \
                               self.tailers['book_yes'].path is not None
                if meta_present:
                    logger.info(
                        f"→ STEADY: outcome {self.current_outcome.outcome_id} confirmed"
                    )
                    self.phase = Phase.STEADY
                    self.last_steady_discovery_ts = now
            elif now - self.post_settle_started_ts > POST_SETTLE_VERIFY_SEC:
                logger.warning(
                    f"⚠️ POST_SETTLE TIMEOUT: outcome {self.current_outcome.outcome_id} "
                    f"files not growing after {POST_SETTLE_VERIFY_SEC}s. "
                    f"Accepting as best-effort."
                )
                self.phase = Phase.STEADY
                self.last_steady_discovery_ts = now

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
                    for hl in await t.get_new():
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
        """Broadcast market_info every second based on current outcome."""
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
        """Same Binance BTC fetcher as mainnet feeder (kept for bridge BTC oracle compat).
        For HYPE 15m strategy this isn't strictly meaningful, but bridge expects btc_update.
        TODO: replace with HYPE price fetch once strategy is HYPE-aware."""
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
        """Main phase state machine driver — runs always at appropriate frequency."""
        while self.running:
            try:
                await self.update_phase()
                # Adjust frequency by phase
                if self.phase == Phase.STEADY:
                    await asyncio.sleep(2.0)
                elif self.phase == Phase.PRE_SETTLE:
                    await asyncio.sleep(0.5)
                elif self.phase == Phase.TRANSITION:
                    await asyncio.sleep(2.0)  # Check for new outcome every 2s
                elif self.phase == Phase.POST_SETTLE:
                    await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"phase_loop: {e}")
                await asyncio.sleep(2)

    async def file_refresh_loop(self):
        """Re-discover hourly files every minute (handles hour rollover within same outcome)."""
        while self.running:
            await asyncio.sleep(60)
            try:
                if self.current_outcome:
                    # Re-attach tailers if newer file exists
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

    async def heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(30)
            s = self.stats
            oc_id = self.current_outcome.outcome_id if self.current_outcome else 'NONE'
            secs_left = (self.current_outcome.seconds_until_expiry 
                         if self.current_outcome else 0)
            logger.info(
                f"💓 [HYPE_FEEDER] phase={self.phase.value} oc=#{oc_id} "
                f"T-{secs_left:.0f}s | OB Y/N: {s['ob_yes']}/{s['ob_no']} | "
                f"TR Y/N: {s['tr_yes']}/{s['tr_no']} | MI: {s['mi']} | "
                f"switches: {s['switches']} | BTC: ${self.last_btc_price:,.0f}"
            )

    async def run(self):
        self.running = True
        logger.info(f"🚀 [HYPE_FEEDER] Network: {NETWORK} | ZMQ: {ZMQ_BIND}")
        logger.info(
            f"🚀 [HYPE_FEEDER] Filter: underlying={TARGET_UNDERLYING}, period={TARGET_PERIOD}"
        )

        # Initial discovery — wait until HYPE 15m outcome appears
        retries = 0
        while self.running:
            oc = self._discover_active_outcome()
            if oc:
                self._switch_to_outcome(oc)
                self.phase = Phase.POST_SETTLE
                self.post_settle_started_ts = time.time()
                break
            retries += 1
            logger.warning(f"Waiting for active HYPE 15m outcome... ({retries})")
            if retries > 24:
                logger.error("No active HYPE 15m outcome after 2min. Is collector running on testnet?")
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
    feeder = HypeFeeder()
    try:
        asyncio.run(feeder.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
