#!/usr/bin/env python3
"""HL mainnet 2026-05-04 — fixed BBO and book parsers."""
import gzip, json, statistics
from collections import Counter
from pathlib import Path

DATA_DIR = Path.home() / "HL/data/raw/mainnet/2026-05-04"
TICK = 0.00001

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

# ─── BBO spread distribution ─────────────────────────────────────────
print("=== BBO SPREAD DISTRIBUTION (YES side) ===\n")
bbo_y = load_jsonl_gz("bbo_h20_")
print(f"Total BBO updates: {len(bbo_y)}")

spreads_ticks = []
spreads_cents = []
for b in bbo_y:
    bp = b.get('bid_px')
    ap = b.get('ask_px')
    if bp and ap:
        try:
            bp_f, ap_f = float(bp), float(ap)
            if ap_f > bp_f > 0:
                spread = ap_f - bp_f
                spreads_ticks.append(round(spread / TICK))
                spreads_cents.append(spread * 100)  # convert to cents
        except (ValueError, TypeError):
            pass

if spreads_ticks:
    dist = Counter(spreads_ticks)
    total = len(spreads_ticks)
    print(f"\nSpread distribution (in HL ticks of 0.00001):")
    print(f"{'ticks':>10}  {'price':>10}  {'count':>8}  {'pct':>6}  {'cum_pct':>8}")
    cum = 0
    for t in sorted(dist.keys())[:30]:
        c = dist[t]
        cum += c
        print(f"  {t:>8}  {t*TICK:>10.5f}  {c:>8}  {c/total*100:>5.1f}%  {cum/total*100:>7.1f}%")
    print(f"\nMedian: {statistics.median(spreads_ticks)} ticks ({statistics.median(spreads_ticks)*TICK:.5f})")
    print(f"Mean:   {statistics.mean(spreads_ticks):.1f} ticks ({statistics.mean(spreads_ticks)*TICK:.5f})")
    print(f"Min/Max: {min(spreads_ticks)} / {max(spreads_ticks)} ticks")

    # In CENTS for comparison with PM (PM tick = 0.01 = 1 cent)
    print(f"\nIn cents (PM-comparable):")
    print(f"  median spread: {statistics.median(spreads_cents):.4f}c")
    print(f"  mean spread:   {statistics.mean(spreads_cents):.4f}c")
    print(f"  >= 1c:         {sum(1 for s in spreads_cents if s>=1.0)/total*100:.1f}%")
    print(f"  < 0.1c:        {sum(1 for s in spreads_cents if s<0.1)/total*100:.1f}%")

# ─── L2 book depth ───────────────────────────────────────────────────
print("\n\n=== L2 BOOK DEPTH (mid-day sample) ===\n")
books_y = load_jsonl_gz("book_h20_")
print(f"Total book snapshots: {len(books_y)}")
if books_y:
    sample = books_y[len(books_y)//2]
    bids = sample.get('bids', [])
    asks = sample.get('asks', [])
    print(f"\nMid-day sample (bid/ask sides):")
    print(f"\nASKS top-5 (далекие → ближние):")
    for a in reversed(asks[:5]):
        try:
            print(f"  px={float(a.get('px',0)):.5f}  sz={float(a.get('sz',0)):>10.1f}  n={a.get('n',0)}")
        except (ValueError, TypeError):
            print(f"  raw: {a}")
    print(f"\nBIDS top-5:")
    for b in bids[:5]:
        try:
            print(f"  px={float(b.get('px',0)):.5f}  sz={float(b.get('sz',0)):>10.1f}  n={b.get('n',0)}")
        except (ValueError, TypeError):
            print(f"  raw: {b}")
    if bids and asks:
        try:
            spread_here = float(asks[0].get('px',0)) - float(bids[0].get('px',0))
            print(f"\n  spread here: {spread_here:.5f} = {spread_here/TICK:.0f} ticks = {spread_here*100:.2f}c")
        except (ValueError, TypeError):
            pass

# ─── BBO size depth at top ───────────────────────────────────────────
print("\n\n=== BBO SIZE AT BEST ===\n")
bid_sizes = [float(b.get('bid_sz', 0)) for b in bbo_y if b.get('bid_sz')]
ask_sizes = [float(b.get('ask_sz', 0)) for b in bbo_y if b.get('ask_sz')]
if bid_sizes:
    print(f"YES best-bid size: median={statistics.median(bid_sizes):.0f}  mean={statistics.mean(bid_sizes):.0f}  max={max(bid_sizes):.0f}")
if ask_sizes:
    print(f"YES best-ask size: median={statistics.median(ask_sizes):.0f}  mean={statistics.mean(ask_sizes):.0f}  max={max(ask_sizes):.0f}")

# ─── Latency check ────────────────────────────────────────────────────
print("\n\n=== LATENCY (HL exchange ts → our ts_local) ===\n")
trades_y = load_jsonl_gz("trades_h20_")
lats = [t.get('latency_ms') for t in trades_y if t.get('latency_ms') is not None and t.get('latency_ms') > 0]
if lats:
    print(f"trades latency_ms: median={statistics.median(lats):.0f}  mean={statistics.mean(lats):.0f}")
    print(f"  p95: {sorted(lats)[int(len(lats)*0.95)]:.0f}  p99: {sorted(lats)[int(len(lats)*0.99)]:.0f}")
    print(f"  max: {max(lats):.0f}")
    print(f"  trades within 1s latency: {sum(1 for l in lats if l<1000)/len(lats)*100:.1f}%")

bbo_lats = [b.get('latency_ms') for b in bbo_y if b.get('latency_ms') is not None and b.get('latency_ms') > 0]
if bbo_lats:
    print(f"\nbbo latency_ms: median={statistics.median(bbo_lats):.0f}  mean={statistics.mean(bbo_lats):.0f}")
    print(f"  p95: {sorted(bbo_lats)[int(len(bbo_lats)*0.95)]:.0f}  p99: {sorted(bbo_lats)[int(len(bbo_lats)*0.99)]:.0f}")
    print(f"  max: {max(bbo_lats):.0f}")

print("\n=== DONE ===")
