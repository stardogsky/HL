---
tags: [hyperliquid, design, auto_discovery, state_machine, priority_2]
status: DESIGNED — implementation pending
last_updated: 2026-05-07
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
estimated_effort: "2-3 hours implementation + testing"
related:
  - HFT-Bot/Hyperliquid/00_HL_START_HERE.md
  - HFT-Bot/Refactor_Code/05_hl_feeder.md
  - HFT-Bot/ADR/2026-05-05_hl_collector_subscription_lifecycle_fix.md
---

# 🛠️ HL Feeder Auto-Discovery — Design

> **Priority 2 на возврате к HL работе.**
> Дизайн готов. Имплементация — нет.
> Цель: eliminate manual feeder patch на каждое settlement (mainnet daily) + готовая инфра для 15min markets когда HL их даст.

---

## Проблема

Текущий `~/HL/hl_feeder.py` имеет **hardcoded** `OUTCOME_ID`:

```python
OUTCOME_ID = 5  # mainnet BTC daily
YES_TOKEN_ID = "50"
NO_TOKEN_ID = "51"
YES_FILE_PREFIX = f"book_h{YES_TOKEN_ID}_"
# ...
```

После каждого settlement:
- Mainnet daily → **один раз в сутки** (06:00 UTC) — manual patch via sed
- Testnet HYPE 15m → **каждые 15 минут** — impractical вообще

Это **operational debt**:
- Recurring 5-minute task каждое утро
- Window vulnerability — если patch опоздает на 30 минут, bot накапливает no-data noise
- Не поддерживает 15min markets

---

## Решение — Phase-Gated State Machine

**Не cron polling.** Не "check every 60 seconds".
**Event-driven** — feeder знает когда current outcome expires (из `outcome_meta` description), активирует discovery только в окне ±2 минуты вокруг settlement.

### Phase diagram

```
                              ┌──────────────┐
                              │   STEADY     │ ← 99% времени
                              │  (sleep 2s)  │   стандартное чтение book/trades
                              └──────┬───────┘   no discovery checks
                                     │
                          T-30s до expiry
                                     │
                                     ▼
                              ┌──────────────┐
                              │ PRE_SETTLE   │ ← готовимся
                              │ (sleep 0.5s) │   быстрее обновления
                              └──────┬───────┘
                                     │
                            T = expiry (settlement)
                                     │
                                     ▼
                              ┌──────────────┐
                              │ TRANSITION   │ ← активный поиск нового outcome
                              │ (sleep 2s)   │   poll outcome_meta, find next
                              └──────┬───────┘
                                     │
                          new outcome found
                                     │
                                     ▼
                              ┌──────────────┐
                              │ POST_SETTLE  │ ← verify файлы новые growing
                              │ (sleep 2s)   │   check book_h<new>_*.jsonl exists
                              └──────┬───────┘
                                     │
                          files growing OK
                                     │
                                     ▼
                              ┌──────────────┐
                              │   STEADY     │ ← back to normal
                              └──────────────┘

Timeout fallbacks:
  TRANSITION > 120s → log error, fall back to STEADY (failsafe retry)
  POST_SETTLE > 180s → accept best-effort, log warning, fall back to STEADY
```

### Phase frequency table

| Phase | Sleep | When | What it does |
|---|---|---|---|
| STEADY | 2.0s | 99% времени | normal book/trades read, no discovery |
| PRE_SETTLE | 0.5s | T-30s до expiry | faster reads, готовимся к switch |
| TRANSITION | 2.0s | T+0..T+120s | poll outcome_meta каждые 2s, find new outcome |
| POST_SETTLE | 2.0s | After switch | verify new files writing, fallback to STEADY |

### State transitions logic

```python
async def update_phase(self):
    now = time.time()
    
    if self.current_outcome is None:
        # Cold start — find any active outcome matching filter
        new_oc = self._discover_active_outcome()
        if new_oc:
            self._switch_to_outcome(new_oc)
            self.phase = Phase.POST_SETTLE
        return

    secs_to_expiry = self.current_outcome.expiry_ts - now
    
    if self.phase == Phase.STEADY:
        # Failsafe: occasional check каждые 60s in case missed transition
        if now - self.last_steady_discovery_ts > 60:
            self.last_steady_discovery_ts = now
            if secs_to_expiry < 0:
                # We're past expiry — should not be in STEADY, force TRANSITION
                logger.warning("⚠️ STEADY but expired — entering TRANSITION")
                self.phase = Phase.TRANSITION
                self.transition_started_ts = now
                return
        
        # Normal STEADY → PRE_SETTLE
        if 0 < secs_to_expiry < 30:
            logger.info(f"→ PRE_SETTLE: outcome expires in {secs_to_expiry:.0f}s")
            self.phase = Phase.PRE_SETTLE
    
    elif self.phase == Phase.PRE_SETTLE:
        if secs_to_expiry <= 0:
            logger.info("→ TRANSITION: searching for new outcome")
            self.phase = Phase.TRANSITION
            self.transition_started_ts = now
    
    elif self.phase == Phase.TRANSITION:
        new_oc = self._discover_active_outcome()
        if new_oc and new_oc.outcome_id != self.current_outcome.outcome_id:
            self._switch_to_outcome(new_oc)
            self.phase = Phase.POST_SETTLE
            self.post_settle_started_ts = now
        elif now - self.transition_started_ts > 120:
            logger.error(f"⚠️ TRANSITION timeout — no new outcome after 120s")
            self.phase = Phase.STEADY  # retry from STEADY
            self.last_steady_discovery_ts = now
    
    elif self.phase == Phase.POST_SETTLE:
        if self._are_files_growing():
            logger.info(f"→ STEADY: outcome {self.current_outcome.outcome_id} confirmed")
            self.phase = Phase.STEADY
        elif now - self.post_settle_started_ts > 180:
            logger.warning("⚠️ POST_SETTLE timeout — accepting best-effort")
            self.phase = Phase.STEADY
```

---

## Filter — какой outcome выбирать

Главный architectural choice — **filter criteria**.

### Подход 1 — Hardcoded для одного типа

```python
# Для mainnet BTC daily feeder:
TARGET_UNDERLYING = "BTC"
TARGET_PERIOD = "1d"
NETWORK = "mainnet"

# Для testnet HYPE 15m feeder (когда понадобится):
TARGET_UNDERLYING = "HYPE"
TARGET_PERIOD = "15m"
NETWORK = "testnet"
```

**Pros:** простой, безопасный, два разных файла feeder.
**Cons:** code duplication (~90% кода идентичен).

### Подход 2 — Параметризованный single feeder

```python
# Через CLI args или config
python3 ~/HL/hl_feeder_v2.py --network mainnet --underlying BTC --period 1d --port 5575
python3 ~/HL/hl_feeder_v2.py --network testnet --underlying HYPE --period 15m --port 5576
```

**Pros:** один файл, easier to maintain.
**Cons:** complex testing matrix, риск сломать mainnet при работе над testnet.

### Рекомендация: Подход 1 первым шагом, миграция к Подходу 2 после validation

**Causation:** хочется validation на real settlements (один за 24h на mainnet) перед тем как параметризовать. Если phase state machine работает на testnet HYPE 15m (4 settlements/час) — pattern ready для mainnet portирования.

**Sequence:**
1. Создать `~/HL/hl_feeder_hype15m.py` с hardcoded HYPE 15m filter — только для **infrastructure validation** на testnet (не для trading — testnet HYPE broken!)
2. Validate phase state machine за 4-8 settlements (1-2 часа real time)
3. Backport pattern в `~/HL/hl_feeder.py` (mainnet BTC) с hardcoded BTC 1d filter
4. Wait for next mainnet settlement (06:00 UTC) — validate без manual patch
5. После 2-3 successful settlements — refactor в parameterized single feeder

---

## Filter implementation

```python
def parse_outcome(outcome_data: dict) -> Optional[OutcomeInfo]:
    """Parse outcome dict from outcome_meta. Returns None if not valid."""
    desc = outcome_data.get('description', '')
    
    # CRITICAL filter — отвергает joke testnet outcomes (Akami, Tuna, Recurring Fallback)
    if not desc.startswith('class:priceBinary'):
        return None
    
    parsed = {}
    for part in desc.split('|'):
        if ':' in part:
            k, v = part.split(':', 1)
            parsed[k.strip()] = v.strip()
    
    if parsed.get('underlying') != TARGET_UNDERLYING:
        return None
    if parsed.get('period') != TARGET_PERIOD:
        return None
    
    try:
        target_price = float(parsed.get('targetPrice', 0))
        expiry_str = parsed.get('expiry', '')
        expiry_dt = datetime.strptime(expiry_str, '%Y%m%d-%H%M').replace(tzinfo=timezone.utc)
        expiry_ts = expiry_dt.timestamp()
        outcome_id = int(outcome_data.get('outcome', 0))
    except (ValueError, KeyError, TypeError):
        return None
    
    return OutcomeInfo(
        outcome_id=outcome_id,
        underlying=parsed.get('underlying', ''),
        period=parsed.get('period', ''),
        target_price=target_price,
        expiry_str=expiry_str,
        expiry_ts=expiry_ts,
        raw_description=desc,
    )


def find_active_outcome(meta_data: dict) -> Optional[OutcomeInfo]:
    """Find active outcome matching filter (expiry > now). 
    If multiple match — pick earliest expiry (current cycle, not future)."""
    candidates = []
    for outcome_data in meta_data.get('outcomes', []):
        oc = parse_outcome(outcome_data)
        if oc is None:
            continue
        if (oc.expiry_ts - time.time()) > 0:
            candidates.append(oc)
    
    if not candidates:
        return None
    
    # Earliest expiry first (current cycle)
    candidates.sort(key=lambda o: o.expiry_ts)
    return candidates[0]
```

---

## OutcomeInfo dataclass

```python
@dataclass
class OutcomeInfo:
    outcome_id: int
    underlying: str            # "BTC", "HYPE", etc
    period: str                # "1d", "15m", "1h"
    target_price: float
    expiry_str: str            # "20260508-0600"
    expiry_ts: float           # epoch seconds (UTC)
    raw_description: str
    
    @property
    def yes_token_id(self) -> str:
        return str(self.outcome_id * 10)  # outcome 5 → "50"
    
    @property
    def no_token_id(self) -> str:
        return str(self.outcome_id * 10 + 1)  # outcome 5 → "51"
    
    @property
    def yes_book_prefix(self) -> str:
        return f"book_h{self.yes_token_id}_"
    
    @property
    def no_book_prefix(self) -> str:
        return f"book_h{self.no_token_id}_"
    
    @property
    def yes_trades_prefix(self) -> str:
        return f"trades_h{self.yes_token_id}_"
    
    @property
    def no_trades_prefix(self) -> str:
        return f"trades_h{self.no_token_id}_"
    
    @property
    def slug(self) -> str:
        return f"hl-{self.underlying.lower()}-{self.period}-{int(self.target_price)}-{self.expiry_str}"
```

---

## Switch logic

```python
def _switch_to_outcome(self, new_outcome: OutcomeInfo):
    """Switch tailers and active state to new outcome."""
    old_id = self.current_outcome.outcome_id if self.current_outcome else None
    self.current_outcome = new_outcome
    
    # Re-attach tailers to new files
    targets = {
        'book_yes': new_outcome.yes_book_prefix,
        'book_no': new_outcome.no_book_prefix,
        'trades_yes': new_outcome.yes_trades_prefix,
        'trades_no': new_outcome.no_trades_prefix,
    }
    for key, prefix in targets.items():
        path = self._latest_file(prefix)
        if path:
            t = JsonlTailer(path)
            t.reset_to_end()  # skip historical, only new lines
            self.tailers[key] = t
            logger.info(f"📂 [{key}] {path.name}")
        else:
            logger.warning(f"⚠️ no file for {key} (prefix '{prefix}')")
            self.tailers[key] = JsonlTailer(None)
    
    self.stats['switches'] += 1
    logger.info(
        f"🎯 SWITCH: {old_id} → {new_outcome.outcome_id} "
        f"({new_outcome.slug}) | strike=${new_outcome.target_price:.2f} | "
        f"expires_in={new_outcome.expiry_ts - time.time():.0f}s"
    )
    
    # market_info_loop will pick up new_outcome and publish slug change
    # Bridge will detect market_switch event и trigger strategy reset
```

---

## Critical interaction with bridge

**Когда меняется outcome → меняется slug → bridge видит market_switch event.**

Strategy expected behavior:
1. Force close all open paper positions (P&L locked)
2. Reset state (Q=0, no fills, no toxic)
3. Start fresh on new outcome

Это **уже встроено** в bridge (тестировалось при manual patch). Никаких изменений в bridge не требуется.

---

## Critical edge cases

### Edge 1 — Multiple matching outcomes

Если HL начнёт выпускать 1d markets для нескольких underlying (BTC + ETH + HYPE) одновременно — `find_active_outcome` будет возвращать только earliest expiry. Это **может быть не тот outcome**.

**Mitigation:** filter использует `TARGET_UNDERLYING` — гарантирует выбор правильного актива.

### Edge 2 — Settlement gap (no new outcome)

Если HL по каким-то причинам не deploy новый outcome immediately after settlement — `TRANSITION` будет timeout через 120s. Это **expected behavior** (lifecycle filter в collector работает аналогично).

**Mitigation:** failsafe retry в STEADY каждые 60s. Bot будет no-data до появления нового outcome.

### Edge 3 — Hour rollover внутри outcome

HL collector пишет файлы по часам (`book_h50_22.jsonl`, `book_h50_23.jsonl`). Если outcome живёт 24 часа — файлов 24 за день.

**Mitigation:** `file_refresh_loop` runs каждые 60s, re-attaches tailers если появился newer file для current outcome's prefix.

### Edge 4 — Reset position в TRANSITION

Когда feeder в TRANSITION (старый outcome expired, новый ещё не найден), tailers указывают на старые файлы. Они **не растут** (HL прекратил writing к ним). Поэтому `book_loop` и `trades_loop` ничего не публикуют — это правильное behavior.

---

## Validation strategy

### Step 1 — Smoke test (testnet HYPE 15m)

**Не для trading** — только для infrastructure validation. Testnet HYPE markets broken (см. [[00_HL_START_HERE]]) но settle каждые 15 мин — perfect stress test.

```bash
# Deploy testnet feeder
python3 ~/HL/hl_feeder_hype15m.py &

# Watch для phase transitions через первые 4 settlements (60 мин)
pm2 logs hl_feeder_hype --lines 100 --follow
```

**Expected log sequence на каждые 15 мин:**
```
HH:14:30 → PRE_SETTLE: outcome 7218 expires in 30s
HH:15:01 SETTLED outcome #7218 (in collector log)
HH:15:01 → TRANSITION: searching for new outcome
HH:15:02 🎯 SWITCH: 7218 → 7223
HH:15:02 → POST_SETTLE
HH:15:04 → STEADY: outcome 7223 confirmed
```

### Step 2 — Mainnet validation (после 2-3 successful testnet settlements)

Backport pattern в `~/HL/hl_feeder.py`. Testing на real mainnet 06:00 UTC settlement.

**Expected на 06:00 UTC:**
```
05:59:30 → PRE_SETTLE: outcome 5 expires in 30s
06:00:00 SETTLED outcome #5 (in collector log)
06:00:00 → TRANSITION
06:00:30-90 🎯 SWITCH: 5 → 6 (depends на HL deployment timing)
06:00:31 → POST_SETTLE
06:00:35 → STEADY: outcome 6 confirmed
```

**No manual patch required.** Это успех.

### Step 3 — Long-term observation

После 7+ successful daily transitions без manual intervention — pattern proven. Можно запускать второй feeder для 15m markets когда HL их даст.

---

## Implementation reference — full code

Full code skeleton (28930 bytes) был набросан в session 2026-05-07 evening. См. transcript `2026-05-07-18-45-17-hl-track-pause-vault-reorg.txt`. На VPS лежит как `/tmp/hl_feeder_hype15m.py` (если не очищен).

**На imp следует:**
1. Recreate code from transcript / скрап design выше
2. Adapt filter for `BTC 1d mainnet` версии
3. Test на testnet first (если testnet HYPE возрождается)
4. Backport на mainnet

---

## Estimate

| Phase | Time |
|---|---|
| Code feeder (BTC mainnet variant) | 60-90 min |
| Local testing (smoke) | 15 min |
| Deploy + monitor | 15 min |
| Wait для real settlement | 18-24h (passive) |
| Validation + bug fix | 30-60 min |
| **Total work** | **2-3 hours active** |

---

## Связи

- **Entry point:** [[00_HL_START_HERE]]
- **Existing feeder code:** [[../Refactor_Code/05_hl_feeder]]
- **Calibration plan:** [[Calibration_Plan]]
- **Settlement window observation (related):** [[../Hypotheses/2026-05-05_hl_settlement_window_mode]]
- **Subscription lifecycle ADR:** [[../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]]
