---
tags: [archived, legacy, hyperliquid]
status: ARCHIVED — 2026-05-07
archived_reason: |
  Pre-implementation research notes from 2026-05-02.
  Research questions answered through actual deployment + paper run.
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
---

# 🗂️ ARCHIVED — Legacy Research Notes

> **Этот документ archived 2026-05-07.**
> Research questions resolved через actual deployment + paper run experience.
>
> **Не редактируй этот файл.**

---

## Что было здесь раньше

Pre-implementation research questions:
1. Используется ли формула mark price для outcome settlement? → **resolved**: см. `Docs/trading/contract-specifications.md` — линейная интерполяция mark price между t0 и t1
2. Точная схема fees для outcomes — **TBD** (не блокер для paper trading)
3. Asset ID format для outcomes — **resolved**: `coin = "#<10*outcome+side>"` (см. `Docs/for-developers/api/asset-ids.md`)
4. Tick / lot / min order BTC — **resolved**: tick=0.00001, depth ~$700-1200 на best bid/ask
5. Rate limits API — **resolved через empirical**: 30 new connections/min IP cap (см. [[../../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]])
6. Существуют ли outcomes < 24h — **resolved**: testnet HYPE 15m exists (но broken), mainnet only 1d as of 2026-05-07

## Где сейчас живут research findings

```
HFT-Bot/Hyperliquid/Docs/                          # synced HL gitbook (85+ pages)
HFT-Bot/Hyperliquid/Docs/_INDEX.md                 # annotated index

HFT-Bot/Hyperliquid/README.md                      # actual HL track status
HFT-Bot/Hyperliquid/Current_Deployment.md          # what's running
HFT-Bot/Hyperliquid/Calibration_Plan.md            # strategy calibration plan

HFT-Bot/Hypotheses/2026-05-05_hl_settlement_window_mode.md   # settlement window observation

HFT-Bot/Calibration/2026-05-05_paper_run_outcome_3.md        # paper run #1 baseline
HFT-Bot/Calibration/2026-05-05_baseline_hl_mainnet_microstructure.md  # microstructure
```

## Микроструктура live BTC observations (preserved here historically)

Из ордербука 2026-05-02 BTC up-or-down (testnet sample):
- Tick: **0.00001** (5 decimal digits, 1000× мельче Polymarket TICK 0.01) — **CONFIRMED on mainnet 2026-05-04**
- Spread: ~**0.00448** absolute = 0.785% relative — **mainnet wider/tighter depending on outcome**
- Depth top: 969-1348 contracts на best bid/ask = **~$700-1200** — **CONFIRMED**
- Уровни: смесь round-prices and FV-based — **CONFIRMED, several MM участников**

## Что делать с этой папкой

Empty placeholder. Can be removed.

## Связи

- **HL Docs (synced):** `Docs/_INDEX.md`
- **Active research findings:** [[../README]], [[../../Calibration/2026-05-05_paper_run_outcome_3]]
- **HL entry point:** [[../00_HL_START_HERE]]
