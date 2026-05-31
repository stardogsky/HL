#!/usr/bin/env python3
"""
test_feeder_rotation.py — verifies hl_feeder state machine handles settlement.

Drives HLFeeder.update_phase() through a synthetic timeline:
    T-90s     : STEADY with outcome A
    T-50s     : should transition STEADY → PRE_SETTLE (lead=60s)
    T+5s      : should transition PRE_SETTLE → TRANSITION (expired)
    T+10s     : meta now contains outcome B (next cycle); should transition → POST_SETTLE
    T+20s     : book data arrives for B; should transition → STEADY

Also verifies:
    - watchdog fires if STEADY but no book data for >alarm threshold
    - force_rediscover triggers in that case

Run:
    python3 ~/HL/test_feeder_rotation.py
"""
import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

import hl_feeder
from hl_feeder import HLFeeder, OutcomeInfo, Phase

# Disable ZMQ binding for test
class FakePub:
    async def send_string(self, *a, **kw):
        return
    def close(self):
        pass
    def setsockopt(self, *a, **kw):
        pass
    def bind(self, *a, **kw):
        pass

class FakeCtx:
    def socket(self, *a, **kw):
        return FakePub()
    def term(self):
        pass

# Monkey-patch zmq.asyncio.Context
import zmq.asyncio
zmq.asyncio.Context = FakeCtx


def make_outcome(oc_id: int, secs_to_expiry: float) -> OutcomeInfo:
    return OutcomeInfo(
        outcome_id=oc_id,
        underlying='BTC',
        period='1d',
        target_price=80000.0,
        expiry_str='20260101-0000',
        expiry_ts=time.time() + secs_to_expiry,
        raw_description='class:priceBinary|underlying:BTC|period:1d',
    )


async def scenario_normal_rotation():
    """Outcome A expires, B takes over cleanly."""
    print("\n=== SCENARIO 1: Normal rotation A → B ===")
    feeder = HLFeeder(network='mainnet')

    # Bootstrap: set outcome A with 90s remaining, STEADY phase
    outcome_a = make_outcome(50, secs_to_expiry=90)
    feeder.current_outcome = outcome_a
    feeder.phase = Phase.STEADY
    feeder.last_book_msg_ts = time.time()  # fresh data

    # Stub discovery to control what feeder sees
    discovered = [None]
    def fake_discover():
        return discovered[0]
    feeder._discover_active_outcome = fake_discover
    feeder._attach_tailers_for = lambda oc: True  # pretend files exist

    # Step 1: 90s to expiry, still STEADY (no transition yet — lead is 60s)
    await feeder.update_phase()
    assert feeder.phase == Phase.STEADY, f"Expected STEADY, got {feeder.phase}"
    print(f"  T-90s phase={feeder.phase.value} ✓")

    # Step 2: simulate 31s pass — now T-59s, should enter PRE_SETTLE
    outcome_a.expiry_ts = time.time() + 50
    await feeder.update_phase()
    assert feeder.phase == Phase.PRE_SETTLE, f"Expected PRE_SETTLE, got {feeder.phase}"
    print(f"  T-50s phase={feeder.phase.value} ✓")

    # Step 3: time advances past expiry
    outcome_a.expiry_ts = time.time() - 5
    await feeder.update_phase()
    assert feeder.phase == Phase.TRANSITION, f"Expected TRANSITION, got {feeder.phase}"
    print(f"  T+5s  phase={feeder.phase.value} ✓")

    # Step 4: outcome B now appears in meta
    outcome_b = make_outcome(55, secs_to_expiry=86400)
    discovered[0] = outcome_b
    await feeder.update_phase()
    assert feeder.phase == Phase.POST_SETTLE, f"Expected POST_SETTLE, got {feeder.phase}"
    assert feeder.current_outcome.outcome_id == 55
    print(f"  T+10s phase={feeder.phase.value} switched to oc#{feeder.current_outcome.outcome_id} ✓")

    # Step 5: book data flows for B → STEADY
    feeder.last_book_msg_ts = time.time()
    await feeder.update_phase()
    assert feeder.phase == Phase.STEADY, f"Expected STEADY, got {feeder.phase}"
    print(f"  T+20s phase={feeder.phase.value} confirmed ✓")
    print(f"  ✅ PASS: Normal rotation works (switches={feeder.stats['switches']})")


async def scenario_transition_timeout():
    """No new outcome appears within TRANSITION_TIMEOUT_SEC → fall back to STEADY (retry)."""
    print("\n=== SCENARIO 2: TRANSITION timeout — no new outcome ===")
    feeder = HLFeeder(network='mainnet')
    outcome_a = make_outcome(50, secs_to_expiry=-10)  # already expired
    feeder.current_outcome = outcome_a
    feeder.phase = Phase.TRANSITION
    feeder.transition_started_ts = time.time() - (hl_feeder.TRANSITION_TIMEOUT_SEC + 5)
    feeder._discover_active_outcome = lambda: None
    feeder._attach_tailers_for = lambda oc: True

    await feeder.update_phase()
    assert feeder.phase == Phase.STEADY, f"Expected STEADY after timeout, got {feeder.phase}"
    print(f"  After {hl_feeder.TRANSITION_TIMEOUT_SEC}s timeout phase={feeder.phase.value} ✓")
    print(f"  ✅ PASS: TRANSITION timeout falls back to STEADY for retry")


async def scenario_watchdog_alarm():
    """STEADY + active outcome + no book msg for >alarm → CRITICAL + force rediscover."""
    print("\n=== SCENARIO 3: Watchdog fires on stale book ===")
    feeder = HLFeeder(network='mainnet')
    outcome_a = make_outcome(50, secs_to_expiry=10000)
    feeder.current_outcome = outcome_a
    feeder.phase = Phase.STEADY
    # Last book was STALE_BOOK_ALARM_SEC + 5s ago
    feeder.last_book_msg_ts = time.time() - (hl_feeder.STALE_BOOK_ALARM_SEC + 5)
    feeder.last_steady_discovery_ts = time.time()  # avoid normal STEADY discovery path

    discovered = [None]  # no new outcome — same oc still active
    def fake_discover():
        return discovered[0]
    feeder._discover_active_outcome = fake_discover
    feeder._attach_tailers_for = lambda oc: True

    alarms_before = feeder.stats['watchdog_alarms']
    forced_before = feeder.stats['forced_rediscoveries']
    await feeder.update_phase()
    assert feeder.stats['watchdog_alarms'] == alarms_before + 1, \
        f"Expected watchdog alarm, got {feeder.stats}"
    assert feeder.stats['forced_rediscoveries'] == forced_before + 1
    print(f"  watchdog_alarms +{feeder.stats['watchdog_alarms'] - alarms_before} ✓")
    print(f"  forced_rediscoveries +{feeder.stats['forced_rediscoveries'] - forced_before} ✓")
    print(f"  ✅ PASS: Watchdog fires on stale book")


async def scenario_watchdog_recovers():
    """Watchdog fires → finds new outcome → SWITCH → POST_SETTLE."""
    print("\n=== SCENARIO 4: Watchdog recovery to new outcome ===")
    feeder = HLFeeder(network='mainnet')
    feeder.last_force_rediscover_ts = 0  # ensure not throttled
    outcome_a = make_outcome(50, secs_to_expiry=10000)
    feeder.current_outcome = outcome_a
    feeder.phase = Phase.STEADY
    feeder.last_book_msg_ts = time.time() - (hl_feeder.STALE_BOOK_ALARM_SEC + 5)
    feeder.last_steady_discovery_ts = time.time()

    # Discovery finds outcome B (different ID) — collector advanced silently
    outcome_b = make_outcome(55, secs_to_expiry=86000)
    feeder._discover_active_outcome = lambda: outcome_b
    feeder._attach_tailers_for = lambda oc: True

    await feeder.update_phase()
    assert feeder.phase == Phase.POST_SETTLE, f"Expected POST_SETTLE, got {feeder.phase}"
    assert feeder.current_outcome.outcome_id == 55
    print(f"  Watchdog → SWITCH 50→55, phase={feeder.phase.value} ✓")
    print(f"  ✅ PASS: Watchdog recovery via rediscover works")


async def scenario_cold_start():
    """No outcome on startup, then one appears."""
    print("\n=== SCENARIO 5: Cold start (no outcome → discovery) ===")
    feeder = HLFeeder(network='mainnet')
    feeder.last_steady_discovery_ts = time.time() - 10  # eligible immediately
    discovered = [None]
    def fake_discover():
        return discovered[0]
    feeder._discover_active_outcome = fake_discover
    feeder._attach_tailers_for = lambda oc: True

    await feeder.update_phase()
    assert feeder.current_outcome is None
    print(f"  No outcome found → stays None ✓")

    # Now one appears
    feeder.last_steady_discovery_ts = time.time() - 10
    discovered[0] = make_outcome(50, secs_to_expiry=86400)
    await feeder.update_phase()
    assert feeder.current_outcome is not None
    assert feeder.phase == Phase.POST_SETTLE
    print(f"  Outcome appeared → SWITCH, phase={feeder.phase.value} ✓")
    print(f"  ✅ PASS: Cold start works")


async def main():
    await scenario_normal_rotation()
    await scenario_transition_timeout()
    await scenario_watchdog_alarm()
    await scenario_watchdog_recovers()
    await scenario_cold_start()
    print("\n🎉 ALL 5 SCENARIOS PASSED")


if __name__ == '__main__':
    asyncio.run(main())
