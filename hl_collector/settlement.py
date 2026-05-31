"""
Settlement watcher — phase-based capture of pre/post settlement events.

For each tracked outcome, monitors expiry timestamp and switches into:
- NORMAL (>30min from expiry) — passive
- TIGHT  (T-30min) — log start of pre-settlement window
- CRITICAL (T-5min) — high-frequency allMids polling for mark price approach
- SETTLEMENT (T=0) — capture final state, target check, winning side
- POST (T+5min) — detect new instance deployment

Writes per-event golden data to:
  <base>/raw/<network>/settlements/settlement_<outcome_id>_<expiry>.json
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from discovery import OutcomeInfo
from writer import JsonFileWriter

logger = logging.getLogger(__name__)


class SettlementWatcher:
    def __init__(self, network: str, poller, json_writer: JsonFileWriter,
                 jsonl_writer,
                 pre_window_min: float = 30,
                 critical_window_min: float = 5,
                 poll_during_critical_sec: float = 0.1,
                 post_window_min: float = 5):
        self.network = network
        self.poller = poller
        self.json_writer = json_writer
        self.jsonl_writer = jsonl_writer
        self.pre_window_sec = pre_window_min * 60
        self.critical_window_sec = critical_window_min * 60
        self.poll_during_critical_sec = poll_during_critical_sec
        self.post_window_sec = post_window_min * 60
        # State per outcome_id
        self._tracked: dict[int, dict] = {}
        # outcome_id -> {'outcome': OutcomeInfo, 'phase': str, 'snapshots': dict}

    async def update_outcomes(self, outcomes: list[OutcomeInfo]):
        """Called when poller detects new outcomeMeta. Updates tracking."""
        current_ids = set()
        for oc in outcomes:
            if not oc.is_price_binary or oc.expiry_dt is None:
                continue
            current_ids.add(oc.outcome_id)
            if oc.outcome_id not in self._tracked:
                self._tracked[oc.outcome_id] = {
                    "outcome": oc,
                    "phase": "NORMAL",
                    "snapshots": {},
                    "last_phase_log_ts": 0,
                }
                logger.info(f"[{self.network}/settlement] tracking outcome #{oc.outcome_id} "
                            f"({oc.underlying} {oc.period}, expiry {oc.expiry_str})")
            else:
                # Update existing — outcomeMeta may rotate targetPrice or expiry
                old = self._tracked[oc.outcome_id]["outcome"]
                if old.expiry_str != oc.expiry_str or old.target_price != oc.target_price:
                    logger.info(f"[{self.network}/settlement] outcome #{oc.outcome_id} ROTATED: "
                                f"new expiry={oc.expiry_str} target={oc.target_price}")
                    # New instance — reset state
                    self._tracked[oc.outcome_id] = {
                        "outcome": oc,
                        "phase": "NORMAL",
                        "snapshots": {},
                        "last_phase_log_ts": 0,
                    }

        # Don't remove disappeared outcomes — they may have just settled

    async def watch_loop(self):
        """Monitor each tracked outcome, manage phase transitions, capture events."""
        while True:
            try:
                now = time.time()
                for outcome_id, state in list(self._tracked.items()):
                    oc: OutcomeInfo = state["outcome"]
                    secs_left = oc.seconds_until_expiry
                    if secs_left is None:
                        continue
                    await self._check_phase(state, secs_left, now)
            except Exception as e:
                logger.error(f"[{self.network}/settlement] watch loop error: {e}", exc_info=True)
            await asyncio.sleep(1)  # tick every second

    async def _check_phase(self, state: dict, secs_left: float, now: float):
        oc: OutcomeInfo = state["outcome"]
        old_phase = state["phase"]

        # Determine new phase
        if secs_left > self.pre_window_sec:
            new_phase = "NORMAL"
        elif secs_left > self.critical_window_sec:
            new_phase = "TIGHT"
        elif secs_left > 0:
            new_phase = "CRITICAL"
        elif secs_left > -self.post_window_sec:
            new_phase = "POST"
        else:
            new_phase = "DONE"

        # Phase transition
        if new_phase != old_phase:
            state["phase"] = new_phase
            logger.info(f"[{self.network}/settlement] outcome #{oc.outcome_id} "
                        f"{old_phase} → {new_phase} (T{secs_left:+.0f}s)")
            await self._on_phase_enter(state, new_phase, secs_left)

        # Per-phase periodic action
        if new_phase == "TIGHT":
            # Capture snapshot at T-30, T-15, T-10, T-5 markers
            await self._capture_marker_if_needed(state, secs_left,
                markers=[1800, 900, 600, 300])
        elif new_phase == "CRITICAL":
            # Critical poll allMids more frequently
            # (already done elsewhere — here we just take snapshots at fine grain)
            await self._capture_marker_if_needed(state, secs_left,
                markers=[300, 240, 180, 120, 60, 30, 10, 5, 2, 1])
            # Aggressive REST snapshot
            await self._snapshot_orderbook_via_rest(state, secs_left)
        elif new_phase == "POST":
            # Detect settlement event: BTC mark vs target
            if "settlement_event" not in state["snapshots"]:
                await self._capture_settlement(state)

    async def _on_phase_enter(self, state: dict, phase: str, secs_left: float):
        """Hook for entering a new phase."""
        oc: OutcomeInfo = state["outcome"]
        await self.jsonl_writer.write(self.network, "settlement_phase_log", {
            "ts_local": time.time(),
            "outcome_id": oc.outcome_id,
            "phase": phase,
            "seconds_left": secs_left,
            "underlying": oc.underlying,
            "period": oc.period,
            "expiry": oc.expiry_str,
            "target_price": oc.target_price,
        })

    async def _capture_marker_if_needed(self, state: dict, secs_left: float, markers: list[int]):
        """Capture snapshot at predefined T-N markers (only once each)."""
        oc: OutcomeInfo = state["outcome"]
        for marker in markers:
            key = f"t_minus_{marker}"
            if key in state["snapshots"]:
                continue
            # Trigger when secs_left first crosses below marker
            if secs_left <= marker:
                snapshot = await self._take_market_snapshot(oc)
                state["snapshots"][key] = snapshot
                logger.debug(f"[{self.network}/settlement] outcome #{oc.outcome_id} captured T-{marker}s")

    async def _take_market_snapshot(self, oc: OutcomeInfo) -> dict:
        """Take a full market snapshot via REST: orderbook YES/NO + mids."""
        snap = {"ts_local": time.time()}

        # allMids
        status, data, _ = await self.poller._post({"type": "allMids"})
        if status == 200 and isinstance(data, dict):
            snap["btc_perp_mid"] = data.get("BTC")
            snap["yes_mid"] = data.get(oc.yes_coin)
            snap["no_mid"] = data.get(oc.no_coin)

        # l2Book YES
        status, data, _ = await self.poller._post({"type": "l2Book", "coin": oc.yes_coin})
        if status == 200:
            snap["yes_book"] = data

        # l2Book NO
        status, data, _ = await self.poller._post({"type": "l2Book", "coin": oc.no_coin})
        if status == 200:
            snap["no_book"] = data

        return snap

    async def _snapshot_orderbook_via_rest(self, state: dict, secs_left: float):
        """During CRITICAL phase, take REST snapshots more frequently for fine-grain."""
        # Don't double-shoot — relies on _capture_marker_if_needed for major markers
        pass

    async def _capture_settlement(self, state: dict):
        """At T=0, capture final state and detect winning side."""
        oc: OutcomeInfo = state["outcome"]
        target = oc.target_price

        # Final snapshot
        final = await self._take_market_snapshot(oc)
        state["snapshots"]["settlement"] = final

        # BTC perp mark at settlement
        btc_mark = None
        try:
            btc_mark = float(final.get("btc_perp_mid", 0))
        except (ValueError, TypeError):
            pass

        # Winning side determination (approximation — true settlement uses interpolation between mark updates)
        winning_side = None
        if btc_mark is not None and target is not None:
            winning_side = "Yes" if btc_mark >= target else "No"

        settlement_event = {
            "ts_local": time.time(),
            "outcome_id": oc.outcome_id,
            "name": oc.name,
            "underlying": oc.underlying,
            "period": oc.period,
            "expiry": oc.expiry_str,
            "target_price": target,
            "btc_mark_at_settlement": btc_mark,
            "winning_side_estimate": winning_side,
            "note": "Estimate based on mark at settlement time. Official settle uses linear interpolation between mark updates around T=0. Reconcile from chain later.",
        }
        state["snapshots"]["settlement_event"] = settlement_event

        logger.info(f"[{self.network}/settlement] SETTLED outcome #{oc.outcome_id} "
                    f"target={target} btc_mark={btc_mark} winning={winning_side}")

        # Write golden file
        expiry_clean = oc.expiry_str.replace("-", "_") if oc.expiry_str else "unknown"
        name = f"settlement_{oc.outcome_id}_{expiry_clean}"
        full_payload = {
            "outcome": {
                "outcome_id": oc.outcome_id,
                "name": oc.name,
                "description": oc.description,
                "underlying": oc.underlying,
                "period": oc.period,
                "expiry": oc.expiry_str,
                "target_price": target,
                "yes_coin": oc.yes_coin,
                "no_coin": oc.no_coin,
            },
            "settlement_event": settlement_event,
            "snapshots": state["snapshots"],
        }
        path = self.json_writer.write(self.network, "settlements", name, full_payload)
        logger.info(f"[{self.network}/settlement] golden file: {path}")

    def get_stats(self) -> dict:
        return {
            "tracked_count": len(self._tracked),
            "tracked": [
                {
                    "outcome_id": oid,
                    "phase": s["phase"],
                    "underlying": s["outcome"].underlying,
                    "period": s["outcome"].period,
                    "expiry": s["outcome"].expiry_str,
                    "secs_until_expiry": s["outcome"].seconds_until_expiry,
                }
                for oid, s in self._tracked.items()
            ],
        }
