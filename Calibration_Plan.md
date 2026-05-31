---
tags: [hyperliquid, calibration, plan, priority_1]
status: PLANNED — execute on return
last_updated: 2026-05-07
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
estimated_effort: "4-6 hours work + 24-48h validation"
related:
  - HFT-Bot/Hyperliquid/00_HL_START_HERE.md
  - HFT-Bot/Calibration/2026-05-05_paper_run_outcome_3.md
  - HFT-Bot/Architecture/Active_Code_Architecture.md
---

# 🎯 HL Strategy Calibration Plan

> **Priority 1 на возврате к HL работе.**
> План калибровки strategy под HL specifics.
> **NOT urgent** — выполняется только если/когда мы решаем engage daily markets.

---

## Контекст — что мы уже знаем

Из paper run #1 (mainnet outcome 3, 2026-05-05, 16h runtime):

```yaml
result: +$1.79 paper P&L on $400 deposit (+0.45%/16h)
fills: 29 total
realized_closures: 5 (Q→0 epoch closures)
toxic_events: 3
strategy_filter_dcs_kill: WORKED (venue-agnostic, blocked expensive side)

verdict: |
  Strategy works на HL daily но subоптимально. 
  Все hardcoded constants — Polymarket-tuned.
  При работе на HL — NOT критично для paper, но искажает метрики.
```

**Главная проблема для калибровки:** strategy была built and tuned для **15min markets с tick=0.01**.
HL даёт **24h markets с tick=0.00001**.
Разница в **time scale** (96x) и **price granularity** (1000x) → strategy thresholds существенно misaligned.

---

## Hardcoded constants для замены

| Константа | Где | PM value | HL value | Impact |
|---|---|---|---|---|
| `TICK_SIZE` | `strategies/gabagool/grid_strategy.py` L1209 | 0.01 | 0.00001 | quote granularity |
| `TICK_SIZE` | `strategies/gabagool/grid_manager.py` L69 | 0.01 | 0.00001 | quote granularity |
| `_MIN_MKT_LOT` | `strategies/gabagool/grid_strategy.py` L1772 | 5 | TBD via outcomeMeta | min lot constraint |
| `MIN_MKT_LOT` | `strategies/gabagool/grid_strategy.py` L5169 | 5 | TBD | duplicate |
| `market_duration_sec` | `configs/HL_Test.yaml` | 900 | 86400 (1d) | epoch timing |
| `market_duration_sec` | `strategies/gabagool/gabagool_strat.py` L2343 | 900 default | — | fallback |

**Edge thresholds** (из paper run #1 наблюдений):

| Параметр | PM 15min baseline | HL daily observed | Action |
|---|---|---|---|
| Median spread | 1-2¢ | 0.38¢ (5x tighter) | thresholds на edge_min нужно scale down |
| Block time | 2s (Polygon) | 0.075s (HL) | refresh_timeout уменьшить |
| Latency Sweden→AWS | ~500ms (Polymarket) | ~165-180ms place→ack (HL projected) | тот же refresh budget |
| Top depth | хвостовой | ~$700-1200 на best bid/ask | lot sizing — больше пространства |

---

## Phase 1 — Analyze Paper Run #1 (1-2 часа)

**Цель:** извлечь полный набор metrics из paper run #1 чтобы понять что именно subоптимально.

### Шаги:

```bash
# 1. Найти log файл бота
ls ~/.pm2/logs/bot-HL-Test*.log

# 2. Extract все fills с timestamps + price + size + side
grep -E "FILL|FILLED" ~/.pm2/logs/bot-HL-Test-out.log > /tmp/hl_fills.log

# 3. Extract все epoch transitions
grep "EPOCH" ~/.pm2/logs/bot-HL-Test-out.log > /tmp/hl_epochs.log

# 4. Extract все TOXIC events
grep -E "TOXIC|toxicity" ~/.pm2/logs/bot-HL-Test-out.log > /tmp/hl_toxic.log

# 5. Extract regime transitions
grep -E "regime|REGIME|TORPEDO|HEALER|HUNTER" ~/.pm2/logs/bot-HL-Test-out.log > /tmp/hl_regime.log
```

### Метрики которые надо посчитать:

1. **Fill latency distribution** — от intent до actual fill (если bridge logs дают это)
2. **Spread at fill** distribution — насколько tight был spread когда заполнили
3. **Time-to-close** epochs — сколько времени Q≠0 → Q=0
4. **Toxic fill rate** — % от fills которые были toxic
5. **DCS_KILL trigger frequency** — % времени filter active
6. **PS (price shift) distribution** при closure — насколько разъезжается book vs entry

### Output Phase 1:

`Calibration/2026-05-XX_hl_paper_run1_analysis.md` со всеми метриками выше.

---

## Phase 2 — Backtester Calibration (2-3 часа)

**Цель:** прогнать strategy через backtester на HL data с разными параметрами, найти sweet spot.

### Pre-requisites:

1. **Backtester data loader для HL JSONL** — может не существовать. Проверить:
   ```bash
   grep -r "hl_" ~/gabagool/backtester/ | head -20
   ```
2. Если нет — написать adapter `backtester/loaders/hl_loader.py` который читает `~/HL/data/raw/mainnet/<date>/book_h*.jsonl` и feed в backtester engine.
3. **Иметь хотя бы 7 дней HL mainnet data** для baseline. Сейчас (2026-05-07) у нас 4 дня (с 4 мая).

### Sweep grid:

```yaml
# Параметры для grid search через backtester optimizer
tick_size: [0.01, 0.001, 0.00001]  # validate impact
market_duration_sec: [86400]  # fixed для daily
edge_min_ticks: [1, 2, 3, 5]    # threshold for opening intent
refresh_timeout_ms: [200, 500, 1000, 2000]
hunter_min_lot: [5, 10, 20]
healer_aggression: [conservative, moderate, aggressive]
```

### Acceptance:

Лучшая комбинация даёт:
- Sharpe > 1.0 на 7-day backtest
- Drawdown < 20% от deposit
- Toxic fill rate < 15% от total fills
- Average epoch close time < 3 hours (для daily)

### Output Phase 2:

- `Calibration/2026-05-XX_hl_param_sweep_results.md` с топ-5 configs
- Updated `configs/HL_Test_calibrated.yaml` с winning параметрами

---

## Phase 3 — Live Paper Validation (24-48 часов)

**Цель:** прогнать calibrated config на real mainnet data, validate что backtester не overfitted.

### Шаги:

1. **Backup существующий config:**
   ```bash
   cp ~/gabagool/configs/HL_Test.yaml ~/gabagool/configs/HL_Test.yaml.bak.pre_calibration
   ```

2. **Apply calibrated config:**
   ```bash
   cp ~/gabagool/configs/HL_Test_calibrated.yaml ~/gabagool/configs/HL_Test.yaml
   pm2 restart bot_HL_Test
   ```

3. **Patch tick_size в коде** (если решили менять):
   ```bash
   cp ~/gabagool/strategies/gabagool/grid_strategy.py ~/gabagool/strategies/gabagool/grid_strategy.py.bak.pre_calibration
   sed -i "s|TICK_SIZE = 0.01|TICK_SIZE = 0.00001|" ~/gabagool/strategies/gabagool/grid_strategy.py
   sed -i "s|TICK_SIZE = 0.01|TICK_SIZE = 0.00001|" ~/gabagool/strategies/gabagool/grid_manager.py
   pm2 restart bot_HL_Test
   ```
   
   **⚠️ Важно:** это изменит behavior **PM ботов тоже** если они используют те же файлы. Альтернатива — config-driven tick_size (Phase 2 полного refactor [[Architecture/Multi_Venue_Refactor_Plan]]). Но это большая работа.
   
   **Pragma альтернатива:** делаем bot-specific override — в feeder publish `tick_size` в `market_info` event, bridge применяет к strategy на market_switch.

4. **Run 48 hours**, observe:
   - Daily P&L (paper)
   - Fill quality (toxic rate)
   - Epoch behavior

5. **Compare** с paper run #1 baseline (+$1.79/16h):
   - Better → calibration works, deploy permanently
   - Same → marginal improvement, не worth complexity
   - Worse → backtester overfitted, revert

### Output Phase 3:

`Calibration/2026-05-XX_hl_calibration_validation.md` с результатами.

---

## Phase 4 (Optional) — Settlement Window Mode

**Цель:** добавить отдельную mode стратегии для T-30min до settlement.

**Trigger:** после Phase 1 анализа paper run #1 — если TOXIC events концентрируются в settlement window (TOXIC #3 в 5:15:53 UTC, T-45min до 06:00).

**Дизайн:** см. [[../Hypotheses/2026-05-05_hl_settlement_window_mode]] — wall+canyon pattern observation.

**Architecture:**
- New FSM state `SETTLEMENT_WINDOW` вместо/parallel с TORPEDO/HEALER
- Detection: `T-X minutes` AND `|FV - target_mid| > threshold` (mathematical determinacy)
- Behavior options:
  - **Defensive** — pause quoting (kill switch)
  - **Predator** — quote только за wall (joining the wall)
  - **Informational** — gap geometry as toxicity signal

**Estimate:** 4-6 часов после Phase 1-3 done.

**Skip if:** TOXIC events не показывают clear settlement-window pattern в данных.

---

## Decision Tree — что делать когда

```
Возвращаемся к HL?
├─ Нет 15min markets на mainnet
│  ├─ Хотим калибровать под daily?
│  │  ├─ Yes → Phase 1 → 2 → 3 (4-6h work + 48h validation)
│  │  └─ No  → откладываем калибровку, focus на 15min infra (Auto_Discovery_Design)
│  └─ Хотим просто paper trading?
│     └─ Manual feeder patch на новый outcome, run as-is
│
└─ HL дал 15min markets!
   ├─ Calibration уже сделан?
   │  ├─ Yes → instant deploy на 15min market (Auto_Discovery feeder + bot)
   │  └─ No  → Phase 1-3 первым приоритетом, потом deploy
   └─ Calibration НЕ сделан, но 15min markets есть
      └─ Это **родной regime** strategy — paper trading может работать БЕЗ calibration
         Phase 1-3 после первого 24h naked run
```

---

## Quick wins (если нет времени на full calibration)

Можно сделать **только** эти два изменения за 30 минут — большая часть mismatch будет fixed:

1. **`market_duration_sec: 86400`** в HL_Test.yaml — strategy будет правильно cчитать time-to-expiry, eliminate TIME_STOP false alarms на старте
2. **Передача `tick_size` через market_info** — feeder читает `period`/`underlying` из meta и publish `tick_size: 0.00001`. Bridge применяет к strategy. Это **не нужен code change** в gabagool, просто handler в bridge.

После этого strategy thresholds остаются PM-tuned, но base mechanics работают correctly.

---

## Зависимости

- **Phase 1** требует доступ к bot logs (есть в `~/.pm2/logs/`)
- **Phase 2** требует HL data loader для backtester (нужно написать)
- **Phase 3** требует stable HL infrastructure (есть)

---

## Связи

- **Entry point:** [[00_HL_START_HERE]]
- **Active code architecture:** [[../Architecture/Active_Code_Architecture]]
- **Strategy semantic map:** [[../strategy_map]]
- **Paper run baseline:** [[../Calibration/2026-05-05_paper_run_outcome_3]]
- **Settlement window hypothesis:** [[../Hypotheses/2026-05-05_hl_settlement_window_mode]]
- **Multi-venue refactor (DEFERRED):** [[../Architecture/Multi_Venue_Refactor_Plan]]
