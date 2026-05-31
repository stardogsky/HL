#!/usr/bin/env python3
"""Baseline numbers from HL mainnet 2026-05-04 dataset.
Reads gzipped JSONL, prints microstructure stats."""
import gzip, json, statistics
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path.home() / "HL/data/raw/mainnet/2026-05-04"

def load_jsonl_gz(prefix):
    out = []
    for f in sorted(DATA_DIR.glob(f"{prefix}*.jsonl.gz")):
        with gzip.open(f, 'rt') as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return out

print(f"=== Loading data from {DATA_DIR} ===\n")

# ─── Trades ──────────────────────────────────────────────────────────
print("=== TRADES ===")
trades_y = load_jsonl_gz("trades_h20_")
trades_n = load_jsonl_gz("trades_h21_")
print(f"YES trades: {len(trades_y)}  |  NO trades: {len(trades_n)}")

if trades_y:
    sample = trades_y[0]
    print(f"Sample fields: {list(sample.keys())}")
    print(f"Sample trade: {sample}")

    # Sizes
    sz_y = [float(t.get('sz', 0)) for t in trades_y]
    sz_n = [float(t.get('sz', 0)) for t in trades_n]
    print(f"\nYES sz   median={statistics.median(sz_y):>8.1f}  mean={statistics.mean(sz_y):>8.1f}  max={max(sz_y):>8.0f}")
    print(f"NO  sz   median={statistics.median(sz_n):>8.1f}  mean={statistics.mean(sz_n):>8.1f}  max={max(sz_n):>8.0f}")

    # Price range
    px_y = [float(t.get('px', 0)) for t in trades_y]
    px_n = [float(t.get('px', 0)) for t in trades_n]
    print(f"\nYES px   range={min(px_y):.4f} - {max(px_y):.4f}  median={statistics.median(px_y):.4f}")
    print(f"NO  px   range={min(px_n):.4f} - {max(px_n):.4f}  median={statistics.median(px_n):.4f}")

    # Side distribution (A=ask hit/taker buy, B=bid hit/taker sell)
    sides_y = Counter(t.get('side') for t in trades_y)
    sides_n = Counter(t.get('side') for t in trades_n)
    print(f"\nYES sides: {dict(sides_y)}  |  NO sides: {dict(sides_n)}")

    # CVD (signed flow)
    cvd_y = sum(float(t.get('sz', 0)) if t.get('side')=='A' else -float(t.get('sz', 0)) for t in trades_y)
    cvd_n = sum(float(t.get('sz', 0)) if t.get('side')=='A' else -float(t.get('sz', 0)) for t in trades_n)
    print(f"YES cumulative flow (A-B):  {cvd_y:+.0f}  |  NO: {cvd_n:+.0f}")

    # Trade rate per hour
    if trades_y:
        ts_first = min(t.get('ts_local', 0) for t in trades_y)
        ts_last = max(t.get('ts_local', 0) for t in trades_y)
        duration_h = (ts_last - ts_first) / 3600 if ts_last > ts_first else 1
        print(f"\nYES trade rate: {len(trades_y)/duration_h:.1f}/hour  ({duration_h:.1f}h window)")

    # Unique buyers/sellers (concentration)
    buyers = Counter(t.get('buyer', '') for t in trades_y if t.get('buyer'))
    sellers = Counter(t.get('seller', '') for t in trades_y if t.get('seller'))
    print(f"\nYES unique buyers: {len(buyers)}  |  unique sellers: {len(sellers)}")
    if buyers:
        top_b = buyers.most_common(5)
        top_s = sellers.most_common(5)
        total_b = sum(buyers.values())
        print(f"Top-5 buyers concentration: {sum(c for _,c in top_b)/total_b*100:.1f}% of trades")
        print(f"Top-5 sellers concentration: {sum(c for _,c in top_s)/total_b*100:.1f}% of trades")

# ─── BBO ─────────────────────────────────────────────────────────────
print("\n\n=== BBO (best bid/offer) ===")
bbo_y = load_jsonl_gz("bbo_h20_")
bbo_n = load_jsonl_gz("bbo_h21_")
print(f"YES BBO updates: {len(bbo_y)}  |  NO BBO updates: {len(bbo_n)}")

if bbo_y:
    sample = bbo_y[0]
    print(f"Sample BBO: {sample}")

    # Spread distribution YES
    spreads_y = []
    for b in bbo_y:
        bbo_arr = b.get('bbo', [])
        if isinstance(bbo_arr, list) and len(bbo_arr) == 2:
            bid = bbo_arr[0]
            ask = bbo_arr[1]
            if bid and ask:
                try:
                    bp = float(bid.get('px', 0))
                    ap = float(ask.get('px', 0))
                    if bp > 0 and ap > bp:
                        spreads_y.append(ap - bp)
                except (ValueError, AttributeError):
                    pass

    if spreads_y:
        # In HL units, tick=0.00001, so spread/0.00001 = ticks
        ticks = [round(s / 0.00001) for s in spreads_y]
        tick_dist = Counter(ticks)
        total = len(ticks)
        print(f"\nYES spread distribution (in ticks of 0.00001):")
        for t, c in sorted(tick_dist.items())[:10]:
            print(f"  {t:>4} ticks  ({t*0.00001:.5f}):  {c:>5} ({c/total*100:.1f}%)")
        print(f"YES spread median ticks: {statistics.median(ticks)}, mean: {statistics.mean(ticks):.1f}")

# ─── L2 Book depth ───────────────────────────────────────────────────
print("\n\n=== L2 BOOK SAMPLE ===")
books_y = load_jsonl_gz("book_h20_")
print(f"YES book snapshots: {len(books_y)}")
if books_y:
    sample = books_y[len(books_y)//2]  # mid-day sample
    levels = sample.get('levels', [])
    if isinstance(levels, list) and len(levels) == 2:
        bids = levels[0][:5] if isinstance(levels[0], list) else []
        asks = levels[1][:5] if isinstance(levels[1], list) else []
        print(f"Mid-day YES book top-5:")
        print(f"  ASKS:")
        for a in reversed(asks):
            print(f"    {float(a.get('px',0)):.5f}  sz={float(a.get('sz',0)):>10.1f}  n={a.get('n',0)}")
        print(f"  BIDS:")
        for b in bids:
            print(f"    {float(b.get('px',0)):.5f}  sz={float(b.get('sz',0)):>10.1f}  n={b.get('n',0)}")

print("\n\n=== DONE ===")
