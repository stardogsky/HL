---
tags: [hyperliquid, roadmap, planning, paused]
date: 2026-05-07
status: PAUSED — next steps queued for return
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
---

# HL Roadmap — очередь работ при возврате

> **Status: PAUSED**
> Следующие шаги когда вернёмся к HL track. Иерархия по приоритету.

---

## 🔵 Priority 1 — Калибровка стратегии под HL

**Документ:** [[Calibration_Plan]]

**Why:** strategy работает на HL daily без re-калибровки (paper run #1: +$1.79/16h), но subоптимально. Hardcoded constants — Polymarket-tuned (15min markets, tick 0.01). HL = daily markets, tick 0.00001.

**Phases:**
1. Analyze paper run #1 (1-2h) — extract metrics
2. Backtester calibration (2-3h) — sweep params
3. Live paper validation (24-48h passive) — confirm

**Plus optional:** settlement window mode (4-6h после Phase 1-3 done) — если data shows settlement-window adverse selection pattern.

**Estimate:** 4-6 часов работы + 24-48 часов passive validation.

**Quick wins** (если нет времени на full calibration):
- `market_duration_sec: 86400` в YAML (5 минут)
- `tick_size` через market_info from feeder (30 минут)

---

## 🟡 Priority 2 — 15min infra (готова к запуску)

**Документ:** [[Auto_Discovery_Design]]

**Why:** 
- Eliminate manual feeder patch на каждое mainnet daily settlement
- Готова инфра для instant deployment когда HL даст 15min mainnet markets
- Может validatе на testnet HYPE 15m settlements (4/hour stress test) — даже несмотря на broken markets

**Implementation steps:**
1. Code feeder с phase state machine (60-90 min)
2. Validate на testnet HYPE 15m (1-2h passive — 4-8 settlements)
3. Backport pattern в mainnet feeder (30 min)
4. Wait для real mainnet settlement (06:00 UTC) — validate без manual patch

**Estimate:** 2-3 часа active work + passive observation.

---

## 🟢 Priority 3 — Мониторы

**Why:** последний приоритет. Сейчас есть `~/HL/monitor_btc_main.py` (working template).

**Tasks:**
1. Если работают 2 bots (BTC daily + HYPE 15m) — клонировать monitor для второго
2. Или integrate в gabagool-dashboard (он уже видит HL_Test через `live_state_HL_Test.json`)
3. Real-time graph fills / P&L / regime transitions

**Estimate:** 30-60 minutes.

---

## 🟣 Priority 4 (DEFERRED) — что отложено

### Settlement window FSM mode

**Trigger:** TOXIC events в settlement window observed в paper run #1. Wall+canyon pattern documented в [[../Hypotheses/2026-05-05_hl_settlement_window_mode]].

**Когда:** после Phase 1 calibration analysis — если data shows clear settlement-window adverse selection pattern.

**Estimate:** 4-6 hours.

### HL strike fetcher

**Why:** заменить garbage от Polymarket gamma-api (returns $4,261 для HL slug). Только cosmetic impact (display, not decisions).

**Implementation:** новый класс reads `targetPrice` из feeder market_info events.

**Estimate:** 1-2 hours.

### Phase 1 ABC рефакторинг (multi-venue framework)

**Документы:** [[../Refactor_Code/01_adapter_base]], [[../Refactor_Code/02_polymarket_adapter]], [[../Refactor_Code/03_venue_config_yaml]]

**Когда:** если/когда нужен 3-й venue одновременно с PM + HL.

**Estimate:** 8-13 working days (см. [[../Architecture/Multi_Venue_Refactor_Plan]]).

### Vocabulary refactor (yes/no → side-agnostic)

**Когда:** при multi-venue framework. См. [[../Architecture/Multi_Venue_Refactor_Plan]] Phase 4.

### Cross-venue arbitrage research

**Когда:** если/когда HL и PM дают одни и те же события (e.g. BTC daily) — есть ли spread?

**Estimate:** unknown, exploratory.

---

## 🔴 Triggers для resume HL track

При появлении любого из этих условий — resume этот roadmap:

1. **HL даёт 15min mainnet markets** для любого underlying (BTC / ETH / HYPE / SOL)
2. **HL даёт mainnet HYPE 1d outcomes** (или другие underlyings) — расширяет diversity
3. **HL fixes testnet HYPE 15m liquidity** — становится pригодным для validation
4. **Конкретная торговая возможность** обнаружена в HL data (specific edge worth pursuing)
5. **Calibration time** появляется — мы готовы делать Phase 1-3 даже без 15m markets

---

## ⚠️ Warning triggers (что может сломать current setup)

При обнаружении этих признаков — investigate immediately:

1. **Collector reconnect rate > 5/min** — может indicate новая lifecycle issue
2. **HL API breaking changes** — outcome_meta description format change, websocket protocol change
3. **Feeder freeze для outcome который ещё не settled** — bug в logic, не settlement
4. **Bot infinite loop** — repeated TIME_STOP / NUCLEAR_CANCEL без orderbook data

---

## Зафиксировать в новой сессии (procedure)

Когда возвращаешься к проекту:

1. **Прочитать [[00_HL_START_HERE]]** — карта обновлена
2. **Прочитать [[README]] + [[Current_Deployment]]** — статус HL
3. **Прочитать этот файл** (Roadmap) — что делать дальше
4. **Sanity check VPS:** `pm2 list | grep hl_`
5. **Проверить current outcome:** `tail -1 ~/HL/data/raw/mainnet/$(date -u +%Y-%m-%d)/outcome_meta_*.jsonl`
6. **Решение по приоритету:**
   - Calibration → [[Calibration_Plan]]
   - 15min infra → [[Auto_Discovery_Design]]
   - Что-то ещё → пересмотр Triggers выше

---

## Связи

- **Entry point:** [[00_HL_START_HERE]] ⭐
- **Status:** [[README]]
- **Deployment:** [[Current_Deployment]]
- **Calibration plan:** [[Calibration_Plan]]
- **Auto-discovery design:** [[Auto_Discovery_Design]]
- **Master passport:** [[../PROJECT_PASSPORT]]
