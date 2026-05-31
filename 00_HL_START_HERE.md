---
tags: [hyperliquid, navigator, entry_point, hl_active]
status: ACTIVE — feeder auto-discovery deployed 2026-05-16
last_updated: 2026-05-16
parent: HFT-Bot/00_START_HERE.md
priority_on_return:
  - verify_2026-05-17_06_00_UTC_settlement_rotated_cleanly
  - decide_strategy_calibration_next_step
  - consider_burn_API_integration_or_HL_15m_markets
---

# 🎯 HL TRACK — START HERE ON RETURN

> **Это первый и единственный документ который надо открыть при возврате к HL работе.**
> Содержит полную ментальную карту: что running, что делать дальше.

---

## 🆕 2026-05-16 — Auto-discovery feeder shipped

**Что:** `hl_feeder.py` теперь сам ротируется через settlement. Hardcoded
`OUTCOME_ID` удалён, defense-in-depth (state machine + internal watchdog +
external health monitor) задеплоен. См. `refactor_reports/11_phase12_feeder_freeze_postmortem.md`.

**Что больше нельзя забыть:** ничего на mainnet settlement не требует
ручного действия. Если что-то идёт не так — `bash ~/HL/monitor_feeder.sh`
печатает статус одной строкой; `cat ~/HL/data/feeder_health.json` даёт
полный JSON snapshot.

**Что проверить на возврате:** прошёл ли settlement 2026-05-17 06:00 UTC
чисто. В логах должен быть SWITCH 50→55 (или whatever HL deploy):
```bash
pm2 logs hl_feeder --lines 200 --nostream | grep -E "SWITCH|TRANSITION|STEADY"
```

---

## 🟢 STATUS — ACTIVE

```yaml
status: ACTIVE
collector: RUNNING (lifecycle filter + GC, since 2026-05-05)
feeder:    RUNNING with auto-discovery (since 2026-05-16, port 5575)
           survives daily settlement без human action
bot:       RUNNING paper, receives fresh book data
           open issue: DCS_KILL gates NO side when FV<0.05 (strategy calibration, not infra)

infra_problem_status: RESOLVED
  - root cause: hardcoded OUTCOME_ID в feeder
  - fix: phase-gated state machine + internal watchdog + external monitor
  - verification: 5/5 unit tests pass, live deploy clean, bot receiving data

next_decision_points:
  - Wait for first auto-rotation 2026-05-17 06:00 UTC to validate end-to-end
  - Then resume strategy calibration discussion (Phase 10 finding: маркет ~0% margin
    without burn API; Phase 11 finding: time-adaptive offset by lifecycle)
  - Or: hunt for HL maker rebate / burn-tx API to unlock real positive EV
```

---

## 🎯 НА ВОЗВРАТЕ — 3 ЗАДАЧИ В ПРИОРИТЕТЕ

### Priority 1: Калибровка стратегии под HL

**Документ:** [[Calibration_Plan]] (полный пошаговый план)

**Краткое:** strategy работает на HL daily без re-калибровки, но subоптимально. Нужно адаптировать:
- `tick_size`: 0.01 (PM) → 0.00001 (HL native) — minor change in `grid_strategy.py` L1209 + `grid_manager.py` L69
- `market_duration_sec`: 900 (PM 15min) → 86400 (HL daily) — в YAML configs
- Edge thresholds под HL spread distribution (median 0.38c vs PM 1-2c)
- Refresh timeouts под HL block 0.075s vs PM 2s

**Estimate:** 4-6 часов работы + 24-48 часов validation на real settlements.

### Priority 2: Подготовить 15min infra (готова для запуска)

**Документ:** [[Auto_Discovery_Design]] (готовый дизайн state machine)

**Краткое:** написать **auto-discovery feeder** с phase-gated state machine. Дизайн готов, имплементация — нет. Нужен для:
- HL когда даст 15m mainnet markets — instant deployment
- Eliminate manual daily patch на mainnet (recurring problem)

**Estimate:** 2-3 часа на feeder + config + testing.

### Priority 3: Мониторы

**Краткое:** есть один `~/HL/monitor_btc_main.py` (working template). Адаптировать для второго bot когда будет 15m. Это **последний** приоритет.

**Estimate:** 30-60 минут.

---

## 📊 VPS STATE на момент паузы (2026-05-07 evening)

### Running pm2 processes

```
✅ hl_collector       — running clean since 2026-05-05 12:45 UTC (40h+ uptime)
                        subscription lifecycle fix deployed, handles settlements automatically
                        accumulating mainnet outcome 5 + testnet rotating HYPE/BTC outcomes
                        
🟡 hl_feeder          — running on outcome 5 (manually patched 17:17 UTC)
                        WILL FREEZE on next mainnet settlement (2026-05-08 06:00 UTC)
                        no auto-discovery — needs manual patch each day
                        
🟡 bot_HL_Test        — running, paper trading mainnet outcome 5
                        WILL receive no data after feeder freezes
                        DCS_KILL filter active blocking expensive side
```

### Recommended action ON RETURN

**If returning within 24h:** все три можно оставить running. Bot накапливает data на текущем outcome.

**If returning after 1+ day:** сначала **stop bot и feeder** (они frozen на settled outcome, генерируют noise):
```bash
pm2 stop hl_feeder bot_HL_Test
# collector keep running — он handles settlements автоматически
```

**Перезапуск** делается:
1. Patch `OUTCOME_ID` в `~/HL/hl_feeder.py` на текущий active outcome (см. процедуру ниже)
2. `pm2 restart hl_feeder bot_HL_Test`

### Files state на VPS

```
/home/moltbot/HL/
├── hl_collector/                          # patched 2026-05-05, running clean
├── hl_collector/backup_20260505/          # backup перед lifecycle fix
├── hl_feeder.py                           # currently OUTCOME_ID=5
├── hl_feeder.py.bak.20260505_outcome2_to_3   # backup
├── hl_feeder.py.bak.20260507_1717         # backup перед patch на outcome 5
├── monitor_btc_main.py                    # working monitor for bot_HL_Test
├── data/raw/mainnet/<date>/               # accumulating
├── data/raw/mainnet/settlements/          # 4+ settlement files (3, 4, 5, ...)
└── data/raw/testnet/settlements/          # 100+ HYPE 15m settlements (golden dataset)

/home/moltbot/gabagool/configs/
└── HL_Test.yaml                           # data_source: zmq://127.0.0.1:5575
                                            # market_duration_sec=900 (NOT calibrated for HL)
```

---

## 🧠 KEY LEARNINGS (3 дня работы 2026-05-04 → 2026-05-07)

### 1. Subscription lifecycle storm — RESOLVED

**Inцident:** 18-часовой reconnect storm 2026-05-04 17:40 → 2026-05-05 12:08 UTC. 41205 disconnects (37/min).

**Root cause:** subscribing to settled/expired outcome coin → HL silently closes connection (undocumented). Self-amplifying loop because reconnect rate exceeded HL `30 new connections/min` IP limit.

**Fix:** Variant A — Lifecycle filter + GC. 3 changes:
1. `discovery.py::filter_outcomes` — фильтр `seconds_until_expiry > 0`
2. `main.py::_on_outcome_meta` — GC step unsubscribe settled coins
3. `ws_client.py` — revert mistaken `asyncio.sleep(0.015)` throttle

**Result:** 37/min → 0/min reconnect rate (2200x reduction). Settlement handled automatically — testnet 6177→6182 transition validated.

См. [[../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]], [[../Incidents/2026-05-05_hl_collector_reconnect_storm]].

**Methodology lesson:** "Documentation Before Empirics" rule установлен. См. [[../meta/2026-05-05_retrospective_methodology_failure]].

### 2. Paper run #1 — strategy works on HL без re-калибровки

**Run:** mainnet outcome 3 (BTC 80930), 2026-05-05 13:08 → 2026-05-06 05:59 UTC (~16 часов)

**Result:**
- Final P&L: **+$1.79 paper** на $400 deposit (+0.45%/16h ≈ 230%/year annualized)
- 5 realized epoch closures (Q→0)
- 3 TOXIC events
- 29 fills total
- DCS_KILL filter v3.4.1 actively blocking expensive side при FV>0.55

**Strategy behavior:** работает корректно, но обнаружено:
- Settlement window adverse selection: TOXIC #3 (5:15:53 UTC) — Hunter NO 20@$0.110 в T-45min до expiry → PS 0.83→1.15 catastrophic
- Подтверждает wall+canyon hypothesis [[../Hypotheses/2026-05-05_hl_settlement_window_mode]]

См. [[../Calibration/2026-05-05_paper_run_outcome_3]].

### 3. Testnet HYPE 15m — broken для testing

**Discovery 2026-05-07:**
```
testnet HYPE perp:
  markPx:    28.52    ← всегда = targetPrice (degenerate)
  midPx:     30.75    ← wide spread
  oraclePx:  91.134   ← реальная HYPE цена с CEX
  openInterest: 50.84  ← almost zero liquidity
```

**Why:** testnet HYPE perp имеет нулевую ликвидность. Mark price formula degenerates когда нет orderbook activity. Settlement always YES (markPx=28.52 ≥ target=28.52).

**Implication:** testnet HYPE НЕ подходит для strategy validation. Можно использовать только для **infrastructure** validation (auto-discovery state machine).

### 4. Mainnet — only BTC 1d, no other outcomes

```bash
$ tail -1 ~/HL/data/raw/mainnet/<date>/outcome_meta_*.jsonl | python3 ...
outcome 5: class:priceBinary|underlying:BTC|expiry:20260508-0600|targetPrice:81041|period:1d
```

**Single outcome.** Никаких HYPE 1d, ETH 1d, или 15m markets на mainnet нет.

---

## 📁 Карта документов HL track (актуальная)

### Active reference (читать по теме):

| Документ | Когда читать |
|---|---|
| **[[00_HL_START_HERE]]** ⭐ | Этот файл — ВСЕГДА на возврате |
| [[README]] | Краткое описание track + хронология + связи |
| [[Current_Deployment]] | Что running на VPS (детально) |
| [[Roadmap]] | Очередь задач + estimates |
| [[Calibration_Plan]] | План калибровки (Priority 1) |
| [[Auto_Discovery_Design]] | Дизайн state machine (Priority 2) |
| [[../Refactor_Code/05_hl_feeder]] | DEPLOYED feeder code |
| [[../Calibration/2026-05-05_paper_run_outcome_3]] | Результат paper run #1 |

### Decision records:

| Документ | Что |
|---|---|
| [[../ADR/2026-05-04_pragmatic_hl_feeder_path]] | Почему feeder вместо ABC рефактора |
| [[../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]] | Collector storm fix |
| [[../Incidents/2026-05-05_hl_collector_reconnect_storm]] | Postmortem |

### Hypotheses (TODO для будущего HL work):

| Документ | Что |
|---|---|
| [[../Hypotheses/2026-05-05_hl_settlement_window_mode]] | Wall+canyon pattern в settlement window |

### Reference documentation:

| Документ | Что |
|---|---|
| `Docs/_INDEX.md` | Аннотированный индекс HL gitbook (85+ страниц) |
| `Docs/hypercore/oracle.md` | Как считается oracle price |
| `Docs/trading/robust-price-indices.md` | Mark price formula |
| `Docs/trading/contract-specifications.md` | Recurring outcomes settlement formula |
| `Docs/for-developers/api/info-endpoint/perpetuals.md` | Endpoint для metaAndAssetCtxs |

### Legacy (archived references — не редактировать):

- `Adapters/README.md` — pre-feeder concept (ARCHIVED, см. ADR/2026-05-04)
- `Architecture/README.md` — pre-implementation planning (ARCHIVED)
- `Architecture/2026-05-04_data_collector_schema.md` — design doc для collector (IMPLEMENTED, reference only)
- `Research/README.md` — early research notes (ARCHIVED)

---

## 🔄 RESUME CHECKLIST (когда возвращаешься)

```bash
# 1. SSH на VPS
ssh moltbot@<VPS_IP>

# 2. Sanity check pm2 status
pm2 list | grep -E "hl_|bot_HL"
# Expected: hl_collector online, hl_feeder/bot_HL_Test возможно frozen

# 3. Какой active outcome сейчас?
TODAY=$(date -u +%Y-%m-%d)
tail -1 ~/HL/data/raw/mainnet/$TODAY/outcome_meta_*.jsonl 2>/dev/null | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print([(o['outcome'], o['description']) for o in d['outcomes'] if o['description'].startswith('class:priceBinary')])"

# 4. Если приоритет = калибровка:
#    Открыть Calibration_Plan, начать с Phase 1 (analysis paper run #1)

# 5. Если приоритет = 15min infra:
#    Открыть Auto_Discovery_Design, начать с Phase 1 (skeleton + integration test)

# 6. Если просто продолжаем daily paper trading:
#    Patch feeder на текущий outcome:
NEW_ID=<from step 3>
cp ~/HL/hl_feeder.py ~/HL/hl_feeder.py.bak.$(date -u +%Y%m%d_%H%M)
sed -i "s|^OUTCOME_ID = .*$|OUTCOME_ID = $NEW_ID|" ~/HL/hl_feeder.py
pm2 restart hl_feeder bot_HL_Test
sleep 30
pm2 logs hl_feeder --lines 20 --nostream  # verify работает
```

---

## ⚠️ ВАЖНО — что НЕ делать на возврате

- ❌ **Не трогать** `~/gabagool/` (Polymarket production) при HL работе
- ❌ **Не лезть** в `Refactor_Code/01-04` (DEFERRED — Phase 1 ABC refactor)
- ❌ **Не пытаться** запускать second feeder для testnet HYPE 15m **для trading validation** — markets broken
- ❌ **Не калибровать** strategy под HL до того как прочитан весь paper run #1 (можно опустить detail)
- ❌ **Не работать** на сниппетах от `search_notes` — только полные `read_note` / `read_multiple_notes`

---

## Связи

- **Master entry point:** [[../00_START_HERE]]
- **Project passport:** [[../PROJECT_PASSPORT]]
- **Strategy semantic map:** [[../strategy_map]]
- **Last session journal:** [[../meta/sessions/2026-05-07_session_end_hl_pause]]
