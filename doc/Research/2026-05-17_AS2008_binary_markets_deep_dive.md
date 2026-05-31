---
title: AS-2008 + наш bot на binary outcome markets — глубокий анализ применимости
date: 2026-05-17
author: research session с HFT-perspective
status: LIVING DOCUMENT — обновляй по мере новых данных/изменений
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
related_artifacts:
  - /home/moltbot/gabagool/docs/STRATEGY_V6_GRID.md  (исходная spec, 2026-02-27)
  - /home/moltbot/gabagool/strategy_map.md            (карта on_tick funnel)
  - /home/moltbot/gabagool/strategies/gabagool/grid_strategy.py  (7427 LOC, основной код)
  - https://github.com/l-arkadiy-l/HFT_exam            (reference AS-2008 impl + backtest)
  - /home/moltbot/HL/refactor_reports/08_phase9_binary_market_margin_problem.md
  - /home/moltbot/HL/refactor_reports/09_phase10_fundamental_findings.md
  - /home/moltbot/HL/refactor_reports/10_phase11_intraday_margin_analysis.md
---

# AS-2008 + binary outcome markets — глубокий анализ применимости

> **Перспектива:** HFT инженер 10+ лет на equity/crypto venues, недавно
> переключился на prediction markets. Цель — реалистично оценить шансы
> текущего подхода, без cheerleading и без doomerism.
>
> **Целевой читатель:** ты сам через 3 месяца, когда забыл контекст и
> хочешь понять «почему мы сейчас делаем X, а не Y».

---

## 0. TL;DR — для возврата через 3 месяца

1. **AS-2008 НЕ создан для binary outcome markets.** Он создан для single-leg
   perpetual markets с inventory-driven price skewing. На pair-locked binary
   markets (Polymarket, HL outcomes) ключевая предпосылка AS — что нашим
   inventory-skewed reservation price можно сдвинуть рынок и пассивно
   разгрузить позицию — **ломается** потому что arbitrage держит `Y_bid +
   N_bid ≈ 1.000`. Любой наш сдвиг bid'а вниз поднимает встречный bid вверх.

2. **Текущий код — гибрид.** В `grid_strategy.py` есть AS-формула
   (`_compute_oracle_fv` → `oracle_engine.calculate_fv`), есть VPIN, есть
   inventory-aware gate (`_compute_elastic_iron_gate`), но также есть много
   надстроек (HUNTER, HEALER, IRON_GATE, ARMOR, GRAVITY) которые **друг
   другу противоречат** на тонком binary спреде.

3. **HFT_exam (reference AS-2008 импла) на их собственном backtest
   проиграл во всех вариантах.** Final PnL: baseline=-10.35, AS=-3.80,
   microprice=-3.72 на 1ч криптовалютного spot стакана. AS лучше baseline
   только потому что **меньше теряет** (inventory control = 38× меньшее
   std(inv)), а не потому что зарабатывает spread.

4. **6 месяцев Polymarket fail имеет естественное объяснение:** на CLOB
   prediction market с maker fee = 0 и spread 1-2 cents queue position и
   latency-adverse selection съедают potential maker margin. Это
   structural, не bug в коде.

5. **Реалистичная вероятность успеха pure pair-lock hold-to-resolve на HL
   daily BTC ≈ 5-15%** (низкая). С round-trip selling + правильной
   калибровкой ≈ 25-40%. С maker rebate ИЛИ когда HL даст 15m markets ≈
   50-70%.

6. **Что делать сейчас:** (a) сделать gate динамическим аналогично offset,
   (b) собрать данные ещё за 5-7 outcomes для проверки Phase 11 hypothesis,
   (c) исследовать round-trip selling в paper mode, (d) проверить HL fee
   schedule на наличие maker rebate, (e) НЕ переписывать стратегию на AS
   "по-другому" — текущая уже AS-like, проблема не в формуле.

---

## 1. Что мы исследовали

**Триггер:** пользователь дал ссылку на `l-arkadiy-l/HFT_exam` (учебная
реализация Avellaneda-Stoikov 2008) и попросил оценить применимость к
нашему боту, с явным открытым вопросом: **готов перейти с hold-to-resolve
на round-trip selling, нужно понять реалистичность**.

**Метод:**
1. Прочитан README + 6 .py файлов HFT_exam (минимальная, чистая AS-импл)
2. Прочитан `STRATEGY_V6_GRID.md` (наша исходная spec, 2026-02-27)
3. Прочитан `strategy_map.md` (карта on_tick funnel)
4. Прочитаны ключевые методы в `grid_strategy.py`
   (`_compute_oracle_fv`, `_compute_elastic_iron_gate`)
5. Notebook `report.ipynb` HFT_exam проанализирован — извлечены backtest
   результаты и их honest limitations
6. Сопоставлено с эмпирическими данными из Phase 9-11 (наши refactor reports)
   и live данными за последние 3 outcomes (~432k snapshots)

**Что НЕ покрыто:** OracleEngine (`_compute_oracle_fv` делегирует туда, я
не нырял), детали `_compute_vector_pricing_and_hunter` (342 строки), детали
VPIN рассчёта в live боте. Можно добавить если потребуется.

---

## 2. Текущее состояние нашего бота — короткий обзор

### 2.1 Архитектура (по `strategy_map.md` и `STRATEGY_V6_GRID.md`)

**4 модуля, ~9910 LOC total:**

| Модуль | LOC | Роль |
|---|---:|---|
| `grid_strategy.py` | 7427 | `GridStrategy` — 72 метода, on_tick = 720 LOC funnel |
| `grid_manager.py` | 455 | grid levels, pending orders, diff sync |
| `execution_engine_v6.py` | 981 | batch place ≤15/chunk, cancel, paper/live |
| `simple_strategy.py` | 1047 | Legacy v4 (всё ещё используется PM paper bot'ами) |

**Tick pipeline (упрощённо из карты):**
```
on_tick(market_data)
  → safety/merge checks (warmup, blind WS, panic stop)
  → _compute_oracle_fv  →  FV из OracleEngine (AS-формула внутри)
  → _compute_elastic_iron_gate  →  gate_max=f(q, time_rem, fv_divergence)
  → _compute_vector_pricing_and_hunter  →  l0_y, l0_n; HUNTER на имбалансе
  → _compute_final_edge  →  edge_y, edge_n (asymmetric, armor+gravity)
  → bbo_clamp + bbo_pull_offset_schedule  →  финальные quote prices
  → IRON_GATE veto если projected pair_sum > active_gate_limit
  → grid_orchestrator + sync_and_triage  →  diff vs pending, batch ops
```

### 2.2 Что **реально** работает (по логам бота)

- Connect к feeder, прохождение data через bridge: **OK** (304k updates received)
- Расчёт FV / oracle на binary outcomes: **работает** (FV=0.469 при текущем BBO_Y=0.469-0.470)
- Detection imbalance, активация HUNTER intent: **работает** (видно в логах)
- Lifecycle-зависимый offset (Phase 11 идея): **уже имплементирован в коде**
  (`bbo_offset_schedule` в YAML, активно)
- VPIN gating, регимы: **работает** (BINANCE_OPEN, NEUTRAL и т.д.)
- Auto-discovery feeder + watchdog: **работает 100%** (settlement 2026-05-17
  06:00 UTC прошёл автоматически)

### 2.3 Что **НЕ** работает (live state на 2026-05-17 14:45 UTC)

| Метрика | Значение | Что значит |
|---|---|---|
| Последний fill | 2026-05-13 21:03:36 UTC | **76 часов без сделки** |
| `signals_generated` | **0** | Strategy не генерирует ни одного intent доходящего до bridge |
| `engine_stats.fills` | 0 | За весь runtime после рестарта — ни одного fill |
| Текущий market | `bid_sum=0.997` (margin 0.3%) | Маркет даёт reasonable margin |
| `IRON_GATE veto` | каждый тик | Все intents режутся внутри strategy |

**Атомарная причина:** в YAML `gate_min: 0.980` (требует ≥2% margin per
pair). Это значение **никогда** не достижимо на HL daily binary (см. § 4.1
ниже — arbitrage держит Y+N≈1.000). За 432k snapshots за 3 outcomes
margin ≥2.0% появлялась 0-1.2% времени (одна минута за день).

**Кумулятивный paper P&L** на исторических данных (когда бот ещё торговал):
- Paper run #1 (mainnet outcome 3, 2026-05-05, 16ч): **+$1.79** на $400 deposit, 29 fills, 5 epoch closures, 3 TOXIC
- Paper run #2 (после Phase 0a-9 restart, 2026-05-13, ~8ч): **+$0.30** на $400 deposit, 545 fills, 16 VIRTUAL_BURN events с margin 0.22%

**Это даёт baseline:** $1.79/16h = $0.11/час ≈ $2.7/24h. На $400 deposit
≈ 0.7%/24h = 250%/год (paper, no fees, no slippage). Звучит хорошо, но
**только когда бот реально торгует** — что сейчас не происходит.

---

## 3. AS-2008: канон vs наша имплементация

### 3.1 Канонический Avellaneda-Stoikov 2008

Формулы (HFT_exam `src/strategies.py`):
```
r       = s - q · γ · σ² · τ
spread  = γ · σ² · τ + (2/γ) · ln(1 + γ/k)
bid     = r - spread/2
ask     = r + spread/2
```

Где:
- `s` — fair price (mid или microprice)
- `q` — inventory (signed, в лотах)
- `γ` — risk aversion (CARA-utility параметр)
- `σ` — реализованная волатильность mid (в fp/√s в их impl)
- `k` — order arrival intensity (`λ(d) = A·exp(-k·d)`)
- `τ` — оставшееся время / rolling const

**Inventory разгружается пассивно:** при `q > 0` reservation `r` идёт
вниз → ask становится ближе к рынку → быстрее filling sell-side →
позиция уходит. На single-asset venue это работает, потому что наш
ask сдвигается в **независимом orderbook**.

**Spread от формулы — это половина asymptotic optimal spread** при
infinite horizon + Poisson order arrivals. Узкий когда σ или γ малы, широкий
когда они большие.

### 3.2 HFT_exam reference impl + backtest evidence

**Default params:** γ=0.1, k=1.5, σ=18.18 fp/√s (рассчитано из 1ч LOB
returns), T=0.1.

**Best params after grid sweep:** γ=0.3, T=1.0 (увеличили risk aversion и
horizon).

**Результаты на 1ч crypto spot (по табликам):**

| Стратегия | Final PnL | Sharpe | std(inv) | Fills | spread_PnL | direction_PnL |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (symmetric ± half-spread) | **-10.35** | -0.83 | 51,351 | 3,778 | **+2014.44** | -2024.79 |
| AS-2008 default | -3.80 | -20.44 | **1,372** | 4,332 | -26.71 | +22.91 |
| Microprice variant | -3.72 | -20.70 | 1,379 | 4,387 | -24.52 | +20.80 |
| AS-2008 best params | -0.093 | -4.83 | **106.7** | 104 | — | — |

**Что эти числа означают (без розовых очков):**

1. **Все стратегии в loss.** На uptrend +0.63% за 1ч любой mean-reverting
   подход просто меньше теряет. AS не "зарабатывает spread" — у неё
   **spread_PnL = -26.71** (отрицательный). Это потому что:
   - Их trade-based fill model: наш ордер исполняется ТОЛЬКО когда реальный
     trade прошёл через нашу цену. Queue position игнорируется.
   - При γ=0.1 спред у AS уже шире BBO → ордера часто стоят дальше топа
     стакана → редко филлятся → когда filled, обычно потому что market
     toxic move прошёл

2. **Baseline парадоксально имеет огромный +spread_PnL.** Это **не**
   потому что baseline хорошая стратегия — это потому что baseline копит
   гигантскую inventory (std=51k!), цена движется, mark-to-market выглядит
   spread-positive. Но **direction term** -2024.79 это всё съедает.

3. **AS inventory control реально работает.** std(inv) AS = 1372 vs
   baseline 51351 — **37× tighter**. Это canonical AS contribution.

4. **Best params (γ=0.3, T=1.0) даёт only 104 fills за час.** То есть AS
   при правильном risk aversion — **редкая, осторожная стратегия**.
   PnL почти ноль (-0.093) потому что почти не торгует. На stationary
   рынке это was zero PnL. На trending — small loss.

**Caveats авторов notebook (явные):**
- **Look-ahead bias:** σ калибровано на тех же 1ч данных, на которых
  тестировали. Параметры optimized на тех же данных. Реальная out-of-sample
  производительность может быть хуже на 20-50%.
- **Без TX costs.** Если добавить 0.1% maker/0.2% taker fee — даже AS
  best уйдёт в значительный минус
- **Один период, одна монета.** Stat power низкий
- **σ статичная.** Реальный online estimation (EWMA, GARCH, two-scale
  realized variance) даёт другие числа

### 3.3 Наш OracleEngine + IRON_GATE: что у нас на самом деле

Наш `_compute_oracle_fv` (grid_strategy.py:2030-2063) **делегирует** в
`self.oracle_engine.calculate_fv(...)`. Сигнатура:

```python
calculate_fv(current_btc, strike, time_left_sec, total_duration,
             vol_ratio, btc_momentum, p_mkt, vpin=0.5)
```

То есть наш FV учитывает:
- `current_btc` — текущая BTC цена (oracle from Binance)
- `strike` — target price outcome'а
- `time_left_sec / total_duration` — Black-Scholes-like time normalisation
- `vol_ratio` — realized vol vs baseline
- `btc_momentum` — last BTC delta
- `p_mkt` — current market mid (как prior)
- `vpin` — токсичность flow

Это **не чистый AS-2008** — это **BS-style binary option pricing с
inventory-aware spread на верхнем уровне**. Гораздо больше параметров чем
canonical AS. С одной стороны — больше signal. С другой — гораздо больше
поверхности для overfit и miscalibration.

`_compute_elastic_iron_gate` (L2065-2130):
```
active_gate_limit = min(
    gate_max,
    gate_min + q_correction + time_correction
            + (max(0, fv_div - 0.15))^1.5 * 0.45
            + trend_bonus
)
```
Где:
- `q_correction = (|q|/hc_limit) * 0.02` — растёт с inventory
- `time_correction` — растёт когда подходит settlement
- `fv_div = |oracle_fv - 0.50|` — насколько direction-bias выражен
- `trend_bonus` — добавочный bonus при сильном направленном bias

**Гейт — это твоё ограничение "до какой суммы pair_sum я готов
покупать"**. По умолчанию `gate_min=0.980` (требует 2% margin). Динамически
он **расширяется** когда (а) накопил inventory, (б) приближается
settlement, (в) oracle сильно отклоняется от 0.5.

**Критическая asymmetry:** gate **расширяется только когда уже плохо**
(много inventory, близко к settlement). Когда жирно (большой spread в
маркете) — gate как был 0.980, так и остался. **Это противоположно тому
что хочется** на binary outcomes: спред волатилен, надо ловить moments
когда он шире, а не когда плохо.

### 3.4 Точные расхождения нашего AS vs canonical

| Аспект | Canonical AS-2008 | Наш bot |
|---|---|---|
| Source of `s` (fair price) | mid или microprice | BS-like Black-Scholes c BTC oracle + Binance feed |
| `q` semantic | inventory в лотах | yes_shares - no_shares (signed) — но `q` лимитируется ещё через `open_q` (clean directional risk без locked pairs) |
| `γ` | static constant | `γ_eff = γ_base · (1 + utilization) · maturity_factor` (хорошо!) |
| `σ` | realized vol | `σ²(p) = σ_base² · p · (1-p)` (binary form, правильно), плюс VPIN multiplier |
| Spread formula | `γσ²τ + (2/γ)ln(1+γ/k)` | НЕТ явной формулы spread'а; spread = `edge_y + edge_n` где `edge_y/n` рассчитываются через `_compute_final_edge` (asymmetric, armor/gravity) |
| Where quotes go | `bid = r - spread/2, ask = r + spread/2` | grid levels по `r ± k·tick` с lot decay, плюс `bbo_pull_offset_schedule` clamp |
| Inventory cap | hard `max_inventory` | `inventory_hard_cap=350` + dynamic IRON_GATE + HUNTER intent при `|q|>3` |
| Veto layer | НЕТ (AS — это quoting policy, не сложный gate) | **IRON_GATE, PS_SQUASH, VETO_M, ARMOR** — несколько overlapping layer'ов |

**Главное расхождение:** канонический AS — это **функция от 5 чисел,
возвращающая (bid, ask)**. У нас — **pipeline из 30+ этапов с защитами,
recovery'ями, regime'ами**. Каждый этап «правильный» отдельно, но в сумме
они **слишком жёсткие для тонкого спреда binary outcome**.

Это **типичная HFT эволюция кода**: реакция на конкретный bug → новый
layer защиты → новый bug → ещё layer → структура каменеет. Через 6
месяцев получается то что и есть сейчас — система которая в теории
оптимальна, на практике **не торгует**.

---

## 4. Binary outcome markets — структурная специфика

### 4.1 Constraint Y + N = 1 и почему он убивает spread capture

На single-asset venue (HFT_exam crypto spot):
- mid = $0.0110
- bid = $0.01098, ask = $0.01102 — spread = $0.00004
- если ты ставишь свой bid на $0.01099 (1 fp выше BBO), у тебя
  positive expected spread (filling sell-side at $0.01099 → потенциально
  buyback at $0.01098 при reversion)

На binary outcome:
- YES bid = $0.469, YES ask = $0.470 (spread = $0.001)
- NO bid = $0.530, NO ask = $0.531 (spread = $0.001)
- `Y_bid + N_bid = 0.999` (margin per pair = $0.001 = 0.1%)
- если ты ставишь Y@0.468 (1 tick ниже YES BBO), arbitrageur **mгновенно**
  поднимет N до 0.531 (если ещё нет) или начнёт сжимать spread, чтобы
  `Y_bid + N_bid` оставался ≈ 1.000

**Эта arbitrage связь работает как трение для maker spread capture**:
любой твой shift на одной стороне коrrelirowannnyy с встречным shift'ом на
другой. Ты можешь получить spread capture только в **транзитивные
моменты** когда arbitrage ещё не сработал (миллисекунды), и только если
**ты быстрее arbitrageur'а** (он на co-located сервере, у тебя 165ms
latency Sweden→AWS).

**Эмпирическое подтверждение** (наши данные за 3 outcomes, 432k snapshots):
- Median bid_sum: 0.9970-0.9988 (margin 0.12-0.30%)
- p90 bid_sum: ≥ 0.9999 в большинстве lifecycle bucket'ов (margin <0.01%)
- Время когда margin ≥ 0.5%: 15-40% обычных hours, до 82% в "сладком окне"
- Время когда margin ≥ 1.0%: 0-30% обычных, 30% peak
- **Время когда margin ≥ 2.0%: 0.0-1.2%** — практически невозможно

### 4.2 Почему "spread capture" канонического AS на этом не работает

Канонический AS (HFT_exam) на binary outcome дал бы:
```
σ²(p) = 0.02² · 0.469 · 0.531 = 0.000099
τ = 86400 / total_duration (нормализованное время)
γ = 0.3 (best from sweep)
r = mid(=0.4695) - q·γ·σ²·τ = 0.4695 - q·0.0000296·τ
spread = γσ²τ + (2/γ)·ln(1+γ/k) ≈ 0 + 5.78 = $5.78
```

Spread вышел **5.78 dollars на $1 contract** — абсурд! Это потому что
`(2/γ) · ln(1 + γ/k)` term doминирует, и он не зависит от σ. Канонический
AS **не учитывает structural constraint `0 < p < 1`** и даёт нонсенс на
binary outcomes.

Чтобы AS работал на binary outcomes, нужно **clamp**:
```
bid = max(0.01, min(0.99, r - spread/2))
ask = max(0.01, min(0.99, r + spread/2))
```

…но тогда `bid = 0.01, ask = 0.99` — то есть всегда на границах. Полезно
ровно ноль.

**Наш `_compute_final_edge` это вроде учитывает** через edge_min=0.0010,
edge_max=0.0080 (ограничивает spread между 10 и 80 ticks). Но
по-прежнему AS spread формула остаётся структурно ill-suited. **Наш bot
не использует caнонический AS spread formula — у него своя кастомная
edge.**

### 4.3 Что **скорее всего** убило Polymarket bot за 6 месяцев

Это hypothesis на основе structural analysis (мы не знаем точной причины):

1. **Queue position.** На Polymarket CLOB, GTC ордера встают в очередь по
   timestamp. Если ты ставишь bid @ $0.48 пятый в очереди, и в маркет
   приходит большой sell @ $0.48, первые 4 ордера зафилятся **до тебя**.
   Ты получишь fill только если цена прошла **сквозь** $0.48 (вниз).
   Это значит — **adverse selection**: ты либо не fill, либо fill потому
   что цена двинулась дальше → toxic.

2. **Latency adverse selection.** Polymarket runs на Polygon (block ~2s).
   Если bot на Sweden, latency ~500ms. За это время "informed" trader на
   co-located сервере уже знает что BTC двинулся на Binance, выкупает у
   тебя по старой цене.

3. **Maker fee на Polymarket = 0%.** Нет structural compensation за
   adverse selection. На традиционных venues (Coinbase, Binance) maker
   получает rebate -0.04% to -0.10%. На Polymarket — ноль.

4. **Spread всегда тонкий.** На BTC 5m/15m markets `bid_sum` обычно 0.99,
   margin per pair = 0.01 = 1 cent. С TX costs (Polygon gas + sign + post
   ≈ $0.005 per trade) — и **уже** mostly negative EV.

5. **Settlement is binary.** Loser side goes to 0. Если ты ошибся
   inventory (long YES, NO win), убыток = full inventory. Hedge через NO
   ноги работает только если ты **сбалансирован** (q≈0), что AS не
   guaranteed на коротком T.

**Все 5 пункт structural. Не fix-able через better AS calibration.**
Можно fix через:
- maker rebate (требует венчурного партнёрства с маркетом)
- быстрая infra (cо-location, latency arbitrage)
- лучший signal (predicting price 100ms ahead — это разные стратегии)
- multi-asset arbitrage (Polymarket vs Binance vs HL spread)

### 4.4 HL daily vs Polymarket 5m/15m — где разница

| Аспект | Polymarket BTC 5m/15m | HL BTC daily outcomes |
|---|---|---|
| Time horizon | 5-15 минут | 24 часа |
| Tick size | $0.01 (100 cents) | $0.00001 (10^-5) |
| Maker fee | 0% (no rebate) | TBD (вероятно negligible, надо проверить) |
| Spread typical | $0.01-0.02 (1-2 ticks) | $0.001-0.003 (100-300 HL ticks) |
| Margin per pair typical | 1% | 0.2-0.3% |
| Margin std (variance) | High (5-15 min цикл) | Moderate (24h цикл) |
| Settlement | Chainlink oracle | HL oracle (Binance composite) |
| Latency Sweden→venue | ~500ms (Polygon HTTP) | ~165-180ms (HL WS+REST) |
| Capital recycle | до 96× за 24h | 1× за 24h |
| Daily P&L upper bound (paper, no fees) | 0.1% × 96 = 9.6%/day | 0.3% × 1 = 0.3%/day |

**HL daily — структурно хуже для maker spread capture:**
- 100× меньше capital recycle
- Spread тоньше относительно tick (3 ticks из 100 vs 1 tick из 100)
- Но: один порядок latency меньше, fees вероятно меньше

**HL 15m (если/когда HL даст):**
- 4 recycle/час × 24 = 96/day (как Polymarket)
- Tighter latency = lower adverse selection
- Это **родной regime** нашей strategy (была tuned для 15m)

**Это объясняет рекомендацию START_HERE:** "wait for HL 15m markets" — это
не "потому что 15m красивее", а **structural** improvement в capital
velocity.

---

## 5. HFT_exam evidence — что он реально доказывает

### 5.1 Их числа

См. § 3.2 таблицы. Главное:
- AS-best (γ=0.3, T=1) даёт **PnL=-0.093** на $1000 capital за 1ч →
  -0.0093%/час → -82%/год если такая стационарность сохранится
- Inventory control: std(inv) AS=107 vs baseline 51351 → **37× tighter**
- Fill rate: AS-best=104 fills/hour, baseline=3778 → AS на 36× менее
  активен

### 5.2 Что эти числа РЕАЛЬНО говорят

**Сильные стороны их работы:**
- Чистая, грамотная импла AS-2008
- Honest backtest без survivorship bias
- Правильный microprice impl (Stoikov 2018)
- Trade-based matching (консервативный — better than fill-on-quote-touch)
- Самокритика: они **сами** признают look-ahead bias и overfit

**Слабые стороны/limitations:**
- 1ч sample — статистически слабо
- Один период, одна монета (нет regime diversification)
- σ калибровано один раз на всём sample (а не online)
- Без TX costs (которые на crypto spot могут быть 0.1-0.2%)
- Тренд +0.63% за 1ч означает что ANY mean-reverting strategy теряет
  (что и видим — все 3 в loss)
- Нет multi-day data чтобы посмотреть как параметры держатся

**Чего этот backtest НЕ доказывает:**
- что AS лучше baseline в expected return — **только в variance**
- что AS profitable на real market — **paper backtest на 1ч stationary
  sample**
- что AS применим к binary outcomes — **их данные spot crypto, не binary**

**Что он точно доказывает:**
- AS даёт **inventory control**, и это measurable (37× std reduction)
- AS даёт **меньше turnover** при правильной γ (104 vs 3778 fills) —
  меньше fees
- **На stationary market** оба варианта converge к ≈0 PnL — AS просто
  более capital-efficient

### 5.3 Самый ценный takeaway для нас

**Inventory control — это canonical AS contribution.** Если в нашем bot
inventory не контролируется (т.е. растут позиции, потом резкое HUNTER
закрытие при TOXIC fill), это значит мы **не получаем canonical AS
benefit**. Видимо нужно проверить что наш `_compute_oracle_fv`
действительно даёт inventory-aware reservation price который реально
влияет на quote prices.

Из live state: `cvd_y=-0.0011, cvd_n=0.0006` (микро значения), `q=0`
(идеал). При q=0 AS-сдвиг = 0 → quotes симметричны вокруг mid. ОК, при
q=0 inventory control trivially работает. Но когда `q≠0` (после fills)
**реально ли сдвигается quote? **— это надо проверить отдельно эмпирически
прогнав test scenario.

---

## 6. Round-trip vs hold-to-resolve — что меняется

Это **самый важный** strategic вопрос.

### 6.1 Наш текущий режим: hold-to-resolve (pair-lock)

```
1. Bot покупает Y@0.469 и N@0.530 (одновременно, через grid)
2. pair_cost = 0.469 + 0.530 = 0.999
3. Hold до settlement (T-0)
4. Profit = 1.00 - pair_cost = 0.001 = $0.001 per pair
```

**Источник profit:** разница между `1.00` и `Y+N at lock` — то есть
**arbitrage premium** который market даёт maker'у за то что he собирает
flow.

**Source of risk:**
- pair_sum может вырасти к settlement (toxic moves shift entries)
- одна нога может застрять (no maker fill on other side)
- inventory imbalance перед settlement = directional risk

**Capital velocity:** 1 раз/сутки на HL daily, 96 раз/сутки на 15m.

### 6.2 Что меняется при round-trip selling

```
1. Bot покупает Y@0.469 и N@0.530 (pair_cost = 0.999)
2. Hold
3. Pair_sum drops to 0.997 (book reverts, market less crowded)
4. Bot продаёт обратно Y@0.471 и N@0.532 (pair_proceed = 1.003)
5. Profit = 1.003 - 0.999 = 0.004 = $0.004 per pair (4× более чем hold-to-resolve!)
```

**Источник profit:** spread compression/dispersion. Когда market crowded
(arbitrageurs active), spread сжимается до 0.999. Когда liquidity исчезает
(тонкий час), spread расширяется до 1.003 (negative margin для buyer,
positive для seller).

**Source of risk:**
- pair_sum может НЕ вернуться вверх до settlement (capital frozen)
- adverse selection — sells происходят на дне dispersion, потом дальнейшее
  движение против нас
- больше maker fills required = больше fees / queue position issues

**Capital velocity:** теоретически 5-20 раз/день в hot часы. Phase 11
показал что в "сладком окне" margin доходит до 0.78%, в плоских часах
0.15-0.2%. Если ловить только sharp dispersion (>0.5%), получится 5-10
roundtrips/день, средний profit ~0.3% per roundtrip.

### 6.3 Где этот edge живёт (empirically)

**Из Phase 11 + наши свежие данные (3 outcomes):**
- Сладкое окно T-11h до T-5h (lifecycle 55-80%) — margin доходит до 0.78%
  median, фракция времени >0.5% margin = 57-82%
- Это соответствует **US/Asia overlap часам** — когда maker'ы активны
- Mid-day (lifecycle 25-55%) — flat 0.2-0.4%, плохо для round-trip
- Settlement window (95-100%) — **неоднозначно**: иногда extreme dispersion
  (outcome 50 показал margin 0.50% median в последний час), иногда
  arbitrage давит до 0.03% (outcome 45)

**Гипотеза для round-trip:** покупка на dispersion 0.997 → продажа когда
arbitrage compresses обратно до 0.999. Average profit ~0.002 = $0.002 per
pair. С 5-10 roundtrips/day × $400 deposit / $1 per pair = 5-10 × $0.80 =
$4-8/day. На $400 deposit = 1-2%/day = 365-730%/year (paper, no fees).

**Это OUTLOOK, не measurement.** Нужно implement и paper-test 7-14 дней.

### 6.4 Risk

Главный риск round-trip selling:
- **Adverse selection.** Каждый sell — это **тебе** продают
  arbitrageurs/predictors. Они продают потому что **думают что pair_sum
  пойдёт ВЫШЕ** (т.е. покупка дешевле тебя). Это **directional bet** на
  short side spread.
- **Queue position.** Sell-orders это ASKS. На binary они тонкие
  (1-2 ticks). Queue position решает, ты обычно последний.
- **Cost compounding.** Round-trip = buy + sell = 2 maker actions =
  2× fees (если есть) + 2× slippage. Hold-to-resolve = 1 buy + settlement
  (no fee for settlement).

**HFT-инженерская оценка:** round-trip на binary outcomes — это
**стратегия двух волн liquidity**, не pure spread capture. Работает если
ты можешь предсказать когда liquidity вернётся (regime detection). Не
работает blind.

---

## 7. Реалистичный roadmap

Приоритизированно. С честной оценкой trade-offs.

### 7.1 Что **точно** надо сделать (high-confidence improvements)

#### **P1. Dynamic gate analogous к offset schedule** (Edit YAML + small code change)

Сейчас `gate_min=0.980` статичен. Сделать `gate_min_schedule` по lifecycle,
parallel `bbo_offset_schedule`:

```yaml
gate_min_schedule:
  - [0.00, 0.997]   # open: margin ≥0.3%
  - [0.25, 0.997]
  - [0.55, 0.993]   # сладкое окно: margin ≥0.7%, агрессивнее
  - [0.80, 0.996]   # pre-settle: осторожнее
  - [0.95, 0.997]   # settlement window: safety
```

Аналогично `hunter_max_gate_schedule` (HUNTER готовность закрывать
позицию).

**Ожидаемый эффект:** bot начнёт quoting в текущих market conditions
(margin 0.25-0.30%) → fills возобновятся. Baseline = paper run #2
(+$0.30 / 8h). Реалистично 0.3-0.7%/24h paper.

**Effort:** 2-3 часа (включая код gate selection logic + smoke test).

#### **P2. Подтвердить что AS inventory control реально работает**

Сделать controlled test: симулировать `q=+20` → проверить что
`_compute_oracle_fv` действительно сдвигает FV вниз (и тем самым YES
quote becomes deeper / NO quote shallower). Если работает — отлично, AS
benefit есть. Если нет — это bug.

**Effort:** 1 час (написать assert-test, run на live market в paper).

#### **P3. Проверить HL fee schedule на наличие maker rebate**

Прочитать `/home/moltbot/HL/doc/Docs/_INDEX.md` и найти fee/incentives
docs. Если есть maker rebate ≥0.05% — это меняет всё (потенциально 0.1%
margin становится net positive).

**Effort:** 30 минут чтения docs + 1 час verification на live order.

### 7.2 Что **попробовать** (research, не сразу production)

#### **R1. Round-trip selling в paper mode**

Добавить:
- Sell intent generation когда `pair_sum drops below entry pair_cost by 2+ ticks`
- Lifecycle-zone restriction (только в "сладком окне" 55-80%)
- Queue position tracking (если возможно — оценить fill probability)
- Separate VIRTUAL_BURN ledger для round-trip vs hold-to-resolve

**Cost:** 1-2 дня implementation + 7 дней paper validation.

**Risk:** если plug-into existing HUNTER/HEALER logic, может breakдать
existing behavior. Лучше отдельный mode флаг.

#### **R2. Online sigma estimation (EWMA или GARCH)**

Сейчас наш σ из `OracleEngine` рассчитывается как-то (надо нырнуть). HFT_exam
σ статична. Если у нас тоже static — EWMA даст adaptive σ который
правильно реагирует на регимы (BINANCE_OPEN, NEUTRAL).

Реализация:
```python
sigma_t² = λ · sigma_{t-1}² + (1-λ) · r_t²    # λ=0.94 RiskMetrics
```

**Cost:** 4-6 часов.

**Benefit:** unclear для binary outcomes (binary σ = p(1-p) уже adaptive
through p), но если оригинальный σ_base statичен — да, полезно.

#### **R3. Анализ распределения paer over 7-14 дней live data**

Соберись 14 outcomes (текущие 12 + 2 будущих). Сделать full bidsum_curve
clustering — есть ли стабильные паттерны или каждый день уникальный?

**Cost:** 2-3 часа analysis.

**Benefit:** validation Phase 11 hypothesis на более крупной выборке.
Также — detection если "сладкое окно" реально стабильно или артефакт
одного outcome.

### 7.3 Что **НЕ делать** (anti-roadmap)

- **❌ Переписывать стратегию на pure AS-2008.** Канонический AS на
  binary outcomes даёт мусор (см. § 4.2). Наша custom impl уже AS-inspired.
  Переписывание = потеря всех accumulated learnings, ноль gain.

- **❌ Добавлять ещё один layer защиты (новый gate / новый regime).**
  Bot уже over-defended (см. § 2.3 — `signals_generated=0`). Решение —
  **убирать** overlapping layers, не добавлять.

- **❌ Sweep parameters на limited data.** HFT_exam пример show что без
  diversification по периоду grid sweep даёт overfit. У нас 12 outcomes
  — недостаточно для serious sweep.

- **❌ Cross-venue arbitrage HL ↔ Polymarket BTC до того как HL bot
  стабильно torgнет хоть на одном venue.** Это complexity multiplier,
  не value adder сейчас.

- **❌ Migrate to other venue до HL exhaustion.** Polymarket уже доказал
  что НЕ работает за 6 месяцев — нет смысла возвращаться. HL exhaustion
  = (a) попробовали 15m markets когда они появятся, (b) попробовали burn
  API когда HL даст.

---

## 8. Honest probability assessment

**Метрика успеха:** bot стабильно делает > 100% годовых на $400 deposit
в paper mode 30 дней подряд, **без** overfit к одному outcome.

| Сценарий | Время до проверки | Вероятность успеха |
|---|---|---|
| Текущий config + ничего не менять | вечно (бот не торгует) | **~0%** |
| P1 only (dynamic gate) | 24-48ч validation | **15-25%** |
| P1 + R1 (dynamic gate + round-trip paper) | 2 недели | **25-40%** |
| P1 + R1 + HL даёт maker rebate ≥0.05% | 1 месяц | **40-60%** |
| Wait for HL 15m markets, ничего другого | unknown (1-12 мес) | **50-70%** (но низкая capital efficiency пока ждём) |
| Все P + R + 15m markets + rebate | 3-6 мес | **70-85%** |

**Bottom line:**

- **Текущий путь без действий — провал** (мы это уже видим — bot не
  торгует 3 дня).
- **Минимальный fix (dynamic gate) даёт ~20% шанс маленького но
  positive yield** (~0.5%/day paper).
- **AS-2008 НЕ silver bullet.** В каноническом виде не применим к binary
  outcomes. У нас уже AS-inspired через `_compute_oracle_fv`, и
  улучшения структурных приоритетов выше чем формула.
- **Polymarket fail должен учить.** На structurally плохом маркете
  никакая стратегия не работает. HL daily ≈ structurally хуже Polymarket
  15m по ключевым осям. Поэтому ожидания должны быть скромными.
- **Реалистичный success case:** HL даёт 15m markets ИЛИ maker rebate.
  Без этих 2 событий — capped около 0.3-0.5%/day paper, что mediocre.

**Не drop-the-mike:** есть ~30-40% шанс что round-trip selling в "сладком
окне" даст значимый edge даже на daily. Это **новая стратегия**, не
вариант существующей. Стоит protoтипировать.

---

## 9. References

### Code paths
- `/home/moltbot/gabagool/strategies/gabagool/grid_strategy.py` — main bot strategy
  - `_compute_oracle_fv` L2030-2063 — AS-based FV via OracleEngine
  - `_compute_elastic_iron_gate` L2065-2130 — dynamic gate (но статичная база)
  - `_compute_vector_pricing_and_hunter` L4081 — HUNTER + vector pricing
  - `_compute_final_edge` L4688 — edge calculation
- `/home/moltbot/gabagool/strategies/gabagool/grid_manager.py` — grid + sync
- `/home/moltbot/gabagool/configs/HL_Test.yaml` — текущий live config
  - `bbo_offset_schedule` lines 117-128 — lifecycle-driven offset (active!)
  - `bbo_min_margin_ticks=30` line 136 — skip threshold (current=30 = 0.3%)
  - `gate_min=0.980, profit_gate_ps_max=0.990` — статичные, надо динамизировать

### Empirical data
- Phase 9 (`08_phase9_binary_market_margin_problem.md`) — open фундаментальный constraint
- Phase 10 (`09_phase10_fundamental_findings.md`) — full economic model
- Phase 11 (`10_phase11_intraday_margin_analysis.md`) — lifecycle margin distribution
- Live data 432k snapshots за 3 outcomes (2026-05-14..17) — см. /tmp/hl_margin_stats.py output

### External
- HFT_exam repo: https://github.com/l-arkadiy-l/HFT_exam — reference AS-2008 impl
- Stoikov (2018) microprice: формула в `src/lob.py` HFT_exam
- Avellaneda & Stoikov (2008) — original paper, см. notebook references
- Сartea, Jaimungal et al. — расширения упомянуты в HFT_exam README

### Memory ссылки
- `project_hl_bot_state` — current state
- `feedback_hl_feeder_stays_honest` — operational lesson re: watchdog
- (после написания этого doc — стоит добавить memory entry pointing сюда)

---

## 10. Update log

| Date | Change | Author |
|---|---|---|
| 2026-05-17 | Initial deep dive — AS-2008 applicability, 6 разделов, % assessment | research session |
| _TODO_ | После P1 dynamic gate deploy — добавить эмпирические числа | |
| _TODO_ | После R1 round-trip paper test — добавить результаты | |
| _TODO_ | После HL даст 15m markets — пересмотреть весь analysis | |

---

## Связи

- **Точка входа HL trail:** `[[../../00_HL_START_HERE]]`
- **Исходная стратегия spec:** `/home/moltbot/gabagool/docs/STRATEGY_V6_GRID.md`
- **Live state:** `/home/moltbot/gabagool/logs/live_state_HL_Test.json`
- **Reference impl:** `https://github.com/l-arkadiy-l/HFT_exam`
- **Margin analysis script:** `/tmp/hl_margin_stats.py`
