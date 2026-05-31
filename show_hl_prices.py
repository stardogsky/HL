#!/usr/bin/env python3
"""
show_hl_prices.py
Live viewer for Hyperliquid HIP-4 outcome market data.
Usage:
    python3 ~/HL/show_hl_prices.py             # mainnet (default)
    python3 ~/HL/show_hl_prices.py --testnet   # testnet
"""
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path.home() / "HL" / "data" / "raw"


def parse_outcome_description(desc: str) -> dict:
    out = {}
    for part in desc.split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def parse_expiry(expiry_str: str) -> datetime:
    return datetime.strptime(expiry_str, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)


def tail_jsonl(path):
    if not path or not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            f.seek(max(0, size - 8192))
            data = f.read().decode("utf-8", errors="ignore")
            lines = [line for line in data.strip().split("\n") if line]
            if lines:
                return json.loads(lines[-1])
    except Exception as e:
        return {"_error": str(e)}
    return None


def find_current_files(network, today):
    base = DATA_ROOT / network / today
    if not base.exists():
        return None, None, None

    bbo_yes_files = sorted(base.glob("bbo_h*_*.jsonl"), key=lambda p: p.stat().st_mtime)
    meta_files = sorted(base.glob("outcome_meta_*.jsonl"), key=lambda p: p.stat().st_mtime)

    if network == "mainnet":
        yes_path = next((p for p in reversed(bbo_yes_files) if "h20_" in p.name), None)
        no_path = next((p for p in reversed(bbo_yes_files) if "h21_" in p.name), None)
    else:
        yes_path = next((p for p in reversed(bbo_yes_files) if "0_" in p.name and "1_" not in p.name.split("_h")[1] if "_h" in p.name), None)
        no_path = next((p for p in reversed(bbo_yes_files) if "1_" in p.name.split("_h")[-1] if "_h" in p.name), None)
        if not yes_path and bbo_yes_files:
            yes_path = bbo_yes_files[-1]

    meta_path = meta_files[-1] if meta_files else None
    return yes_path, no_path, meta_path


def render_dashboard(network):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yes_path, no_path, meta_path = find_current_files(network, today)

    if not yes_path or not no_path:
        return (
            f"❌ No bbo data files found for {today} in {network}.\n"
            f"   Is hl_collector running?\n"
            f"   Check: pm2 list | grep hl_collector"
        )

    yes_bbo = tail_jsonl(yes_path)
    no_bbo = tail_jsonl(no_path)
    meta = tail_jsonl(meta_path) if meta_path else None

    target_price = None
    expiry_dt = None
    underlying = "?"
    period = "?"
    if meta and "outcomes" in meta and meta["outcomes"]:
        outcome_data = meta["outcomes"][0]
        desc = parse_outcome_description(outcome_data.get("description", ""))
        underlying = desc.get("underlying", "?")
        period = desc.get("period", "?")
        try:
            target_price = float(desc.get("targetPrice", 0))
        except (ValueError, TypeError):
            pass
        try:
            expiry_dt = parse_expiry(desc.get("expiry", ""))
        except (ValueError, TypeError):
            pass

    now = datetime.now(timezone.utc)
    time_left_str = "?"
    if expiry_dt:
        delta = expiry_dt - now
        total_sec = int(delta.total_seconds())
        if total_sec > 0:
            h = total_sec // 3600
            m = (total_sec % 3600) // 60
            s = total_sec % 60
            time_left_str = f"{h:02d}h {m:02d}m {s:02d}s"
        else:
            time_left_str = f"EXPIRED ({-total_sec}s ago)"

    out = []
    out.append("=" * 65)
    out.append(f"  Hyperliquid HIP-4 Outcome — Live Prices ({network.upper()})")
    out.append("=" * 65)
    out.append("")

    if target_price is not None and expiry_dt:
        out.append(f"  Market: {underlying} > ${target_price:,.0f}  (period: {period})")
        out.append(f"  Settles at: {expiry_dt.strftime('%Y-%m-%d %H:%M UTC')}")
        out.append(f"  Time left:  {time_left_str}")
        out.append("")

    if yes_bbo and "bid_px" in yes_bbo:
        bid_p = float(yes_bbo["bid_px"])
        bid_s = float(yes_bbo["bid_sz"])
        ask_p = float(yes_bbo["ask_px"])
        ask_s = float(yes_bbo["ask_sz"])
        spread = ask_p - bid_p
        spread_pct = (spread / bid_p * 100) if bid_p > 0 else 0
        latency = yes_bbo.get("latency_ms", 0)
        age_sec = time.time() - yes_bbo.get("ts_local", time.time())
        out.append(
            f"  YES ({yes_bbo.get('coin', '#?')}):  "
            f"{bid_p:.5f}  ({bid_s:>7.1f})  /  {ask_p:.5f}  ({ask_s:>7.1f})"
        )
        out.append(
            f"              spread {spread:.5f} ({spread_pct:.3f}%)  "
            f"| WS lat {latency:.0f}ms | age {age_sec:.1f}s"
        )
    else:
        out.append("  YES:  no data")

    if no_bbo and "bid_px" in no_bbo:
        bid_p_n = float(no_bbo["bid_px"])
        bid_s_n = float(no_bbo["bid_sz"])
        ask_p_n = float(no_bbo["ask_px"])
        ask_s_n = float(no_bbo["ask_sz"])
        spread_n = ask_p_n - bid_p_n
        spread_pct_n = (spread_n / bid_p_n * 100) if bid_p_n > 0 else 0
        out.append(
            f"  NO  ({no_bbo.get('coin', '#?')}):  "
            f"{bid_p_n:.5f}  ({bid_s_n:>7.1f})  /  {ask_p_n:.5f}  ({ask_s_n:>7.1f})"
        )
        out.append(
            f"              spread {spread_n:.5f} ({spread_pct_n:.3f}%)"
        )
    else:
        out.append("  NO:  no data")

    out.append("")

    if (yes_bbo and "bid_px" in yes_bbo and no_bbo and "bid_px" in no_bbo):
        yb = float(yes_bbo["bid_px"])
        ya = float(yes_bbo["ask_px"])
        nb = float(no_bbo["bid_px"])
        na = float(no_bbo["ask_px"])
        bid_sum = yb + nb
        ask_sum = ya + na
        prob_yes_pct = yb * 100
        out.append(f"  Pair sums:  bid_sum = {bid_sum:.5f}   ask_sum = {ask_sum:.5f}")
        out.append(f"  Implied probability YES: {prob_yes_pct:.1f}%")

        if bid_sum > 1.0005:
            out.append(f"  ⚠️  bid_sum > 1.0 — possible arbitrage")
        if ask_sum < 0.9995:
            out.append(f"  ⚠️  ask_sum < 1.0 — possible arbitrage")

    out.append("")
    out.append(f"  Updated: {now.strftime('%H:%M:%S UTC')}  (Ctrl+C to exit)")
    out.append("=" * 65)

    return "\n".join(out)


def main():
    network = "testnet" if "--testnet" in sys.argv else "mainnet"
    print("Starting Hyperliquid live price viewer...")
    print(f"  Network: {network}")
    print(f"  Refresh: 1 second")
    print(f"  Source:  {DATA_ROOT / network}")
    print()
    time.sleep(1)

    try:
        while True:
            print("\033[2J\033[H", end="")
            print(render_dashboard(network))
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nExited cleanly.")


if __name__ == "__main__":
    main()
