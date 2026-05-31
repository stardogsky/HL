#!/usr/bin/env bash
# monitor_feeder.sh — Layer 3 external watchdog for hl_feeder
#
# Reads ~/HL/data/feeder_health.json (written by hl_feeder every 30s)
# Exits with code:
#   0 — healthy
#   1 — STALE (no heartbeat update in >5min)
#   2 — WEDGED (heartbeat fresh but no book data in >5min)
#   3 — NO_OUTCOME (feeder discovered no active outcome)
#   4 — NO_FILE (health file missing — feeder not started or never wrote)
#
# Print human-readable status to stdout (single line).
# Designed to be run from cron / pm2 / desktop notification.
#
# Usage:
#   bash ~/HL/monitor_feeder.sh         # one-shot check
#   bash ~/HL/monitor_feeder.sh --watch # continuous loop (every 60s)

HEALTH_FILE="${HEALTH_FILE:-$HOME/HL/data/feeder_health.json}"
STALE_HEARTBEAT_SEC=300   # health file older than this → STALE
STALE_BOOK_SEC=300        # last book msg older than this → WEDGED
WATCH_INTERVAL=60

check_once() {
    if [ ! -f "$HEALTH_FILE" ]; then
        echo "[$(date -u +%H:%M:%S)] ❌ NO_FILE: $HEALTH_FILE missing"
        return 4
    fi

    python3 - "$HEALTH_FILE" "$STALE_HEARTBEAT_SEC" "$STALE_BOOK_SEC" <<'PY'
import json, sys, time, os
path, stale_hb, stale_book = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
try:
    with open(path) as f:
        h = json.load(f)
except Exception as e:
    print(f"❌ PARSE_ERROR: {e}")
    sys.exit(4)

now = time.time()
hb_age = now - h.get('ts', 0)
book_age = h.get('seconds_since_last_book')
outcome = h.get('current_outcome_id')
phase = h.get('phase', '?')
slug = h.get('current_slug', '?')
ttl = h.get('seconds_to_expiry')
alarms = h.get('stats', {}).get('watchdog_alarms', 0)
switches = h.get('stats', {}).get('switches', 0)
forced = h.get('stats', {}).get('forced_rediscoveries', 0)

prefix = time.strftime('%H:%M:%S', time.gmtime())
status_line = (f"oc=#{outcome} phase={phase} hb_age={hb_age:.0f}s "
               f"book_age={book_age:.0f}s ttl={ttl:.0f}s "
               f"sw={switches} wd={alarms} rd={forced}")

if hb_age > stale_hb:
    print(f"[{prefix}] ❌ STALE: health file {hb_age:.0f}s old — feeder dead? | {status_line}")
    sys.exit(1)

if outcome is None:
    print(f"[{prefix}] ❌ NO_OUTCOME: feeder running but no active outcome | {status_line}")
    sys.exit(3)

if book_age is not None and book_age > stale_book and phase == 'STEADY':
    print(f"[{prefix}] ❌ WEDGED: no book {book_age:.0f}s in STEADY | {status_line}")
    sys.exit(2)

print(f"[{prefix}] ✅ OK: {slug} | {status_line}")
sys.exit(0)
PY
}

case "${1:-}" in
    --watch)
        echo "monitor_feeder: watch mode, interval=${WATCH_INTERVAL}s"
        while :; do
            check_once
            sleep "$WATCH_INTERVAL"
        done
        ;;
    *)
        check_once
        exit $?
        ;;
esac
