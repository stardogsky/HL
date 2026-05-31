# HL — Hyperliquid Outcome Markets

Попытка запустить ту же стратегию market making на бинарных рынках Hyperliquid (HIP-4 outcome markets). Стратегия из `grid_poly_mm` работает без изменений — разница только в адаптере данных.

Проект на паузе: Hyperliquid mainnet даёт только один рынок (BTC daily), стратегия нативна для 15-минутных рынков. Инфраструктура готова — ждёт появления подходящих рынков.

---

## Что здесь есть

**Коллектор** (`hl_collector/`) — daemon на pm2, подписывается на WebSocket HL, пишет JSONL по часам. Умеет переживать settlements без reconnect-шторма (решение задокументировано в `refactor_reports/`).

**Фидер** (`hl_feeder.py`) — читает JSONL, конвертирует формат HL в формат Polymarket, публикует на ZMQ:5575. Бот из `grid_poly_mm` подключается к нему вместо стандартного gateway:5555.

```
hl_collector → data/raw/<сеть>/<дата>/ → hl_feeder → ZMQ:5575 → grid_poly_mm бот
```

**Документация** (`doc/`) — 85+ страниц синхронизированного gitbook Hyperliquid: спецификации HIP-4, API, формулы mark price, контрактные параметры.

**Архив рефакторинга** (`refactor_reports/`) — 12 фаз: от первого запуска до постмортема заморозки фидера. Читается как дневник проекта.

---

## Результат

Один бумажный прогон: +$1.79 за 16 часов на депозите $400. Стратегия работает на HL без перекалибровки. Обнаружена adverse selection в окне settlement (T-45min до экспирации).

Основное препятствие — не код, а рынок: mainnet даёт только BTC daily, стратегия не оптимальна для 24-часового горизонта.

---

## Если хочешь продолжить

`00_HL_START_HERE.md` — точка входа, полный чеклист возврата к проекту.

`Calibration_Plan.md` — что нужно поменять в стратегии под daily рынки (оценка: 4-6 часов работы).

`Auto_Discovery_Design.md` — готовый дизайн auto-discovery фидера, который не зависает на каждом settlement.

---

## Структура

```
hl_feeder.py              ← ZMQ адаптер (HL → PM-совместимый формат)
hl_collector/             ← daemon сбора данных
doc/                      ← документация Hyperliquid (gitbook sync)
refactor_reports/         ← история 12 фаз рефакторинга
data/raw/                 ← собранные JSONL данные
Auto_Discovery_Design.md  ← дизайн auto-discovery (не реализован)
Calibration_Plan.md       ← план калибровки под HL
00_HL_START_HERE.md       ← точка входа при возврате к проекту
```

---

Стратегия: [grid_poly_mm](https://github.com/stardogsky/grid_poly_mm)
