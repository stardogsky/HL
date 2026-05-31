# Phase 0a — Feeder Revive

**Time:** 2026-05-13 18:03 UTC
**Duration:** 5 min

## Action

```bash
cp /home/moltbot/HL/hl_feeder.py /home/moltbot/HL/hl_feeder.py.bak.20260513_1803
sed -i 's|^OUTCOME_ID = .*$|OUTCOME_ID = 35|' /home/moltbot/HL/hl_feeder.py
pm2 restart hl_feeder bot_HL_Test
```

**Patch:** `OUTCOME_ID = 5` → `35` (matched current mainnet active outcome).

## Result

✅ Bot back online, receiving HL data:
- Market: `hl-btc-1d-80983-20260514-0600` (BTC daily, target $80,983, expires 06:00 UTC)
- T-42965s (~12h to expiry)
- BTC spot reading: $79,540 (Binance via feeder)
- Orderbook: YES bid=0.170, NO bid=0.830 (NO leading — BTC below target)

## Critical issues observed in first 30s of activity

### 1. THE FADE mode — ENDGAME WRONG (catastrophic)

```
🧠 [THETA_CORE] Progress: 0.05 | Time_Left: 43s
📉 [THE FADE] Эндшпиль! T-Factor: 0.18 | Уверенность: 0.33 | Limit Y:41 / N:62
```

**Root cause:** `market_duration_sec=900` in YAML, but actual HL daily duration = 86400s.
Strategy thinks every tick is end-of-market → activates "Эндшпиль" (Endgame) → tightens position limits to 41/62 shares.
This **kills** the strategy on day-1 markets.

### 2. DCS_KILL active (correct, but informational)

```
🎯 [DCS_KILL] Side:NO cold_start chasing | LotOrig:10 → 0 | FV:0.335 < Lower:0.450
```

Strategy correctly blocks NO opening because FV=0.335 (cheap side = YES per directional filter).
But this is using PM-tuned threshold; HL FV signals may have different distribution.

### 3. BTC velocity false spike (cosmetic)

```
🌊 [CROSSFIRE] BTC_V:67271.4$/s | Спред x1.5 (кроме хеджа)
```

Bootstrap artifact — first tick computes velocity vs $0 baseline. Self-corrects after 2-3 ticks.

### 4. StrikeFetcher returns garbage $4,261.48

```
🛰️ [STRIKE INIT] Phase 1 (Binance Open): $4,261.48
```

PM gamma-api called with HL slug returns wrong data. Display-only impact, not strategy-blocking.

### 5. MID_DIVERGENCE warning

```
🪦👻⚠️ [MID_DIVERGENCE] Diff: 0.330 | Mid_Y: 0.170 | Impl_Y (from NO): 0.500
```

YES side and NO side orderbooks arrive separately on HL feeder, can be transiently out of sync during cold start. Self-resolves within a few ticks.

## Verdict

✅ Bot alive. ❌ Strategy operating in wrong regime due to `market_duration_sec` mismatch.

**Immediate next step:** Phase 0b — YAML quick wins, especially `market_duration_sec: 86400`.
