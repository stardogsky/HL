---
tags: [hyperliquid, deployment, vps, pm2, current_state]
date: 2026-05-17
status: ACTIVE — auto-discovery feeder deployed, daily rotation automatic
last_verified: 2026-05-17T00:00:00Z
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
---

## ⚡ 2026-05-16 update — feeder rewrite

**Feeder больше не hardcoded на OUTCOME_ID.** Заменён на auto-discovery
с phase-gated state machine + watchdog + health file. Подробно см.
`refactor_reports/11_phase12_feeder_freeze_postmortem.md`.

**Recovery procedure теперь не нужна** — на settlement feeder сам
переключается через PRE_SETTLE → TRANSITION → POST_SETTLE → STEADY.

**Если что-то всё-таки пойдёт не так:**
```bash
bash ~/HL/monitor_feeder.sh           # one-line status check
cat ~/HL/data/feeder_health.json      # full snapshot
pm2 logs hl_feeder --lines 80 --nostream | grep -E "SWITCH|CRITICAL|WATCHDOG"
```

Старая Recovery procedure (sed OUTCOME_ID + pm2 restart) ниже в этом
документе — оставлена как fallback на случай если auto-discovery
сломается. Не должно понадобиться.

---

# HL Current Deployment — что running на VPS

> Snapshot текущего deployment HL infrastructure на 2026-05-07 evening.
> При возврате — обновить этот файл если что-то изменилось.

---

## Сводка pm2 processes

| Component | Status | pm2 name | Port / File | Uptime |
|---|---|---|---|---|
| HL collector | ✅ RUNNING clean | `hl_collector` | writes to `~/HL/data/raw/` | 7h+ since reset |
| HL feeder | 🟡 RUNNING (manual mode) | `hl_feeder` | publishes ZMQ tcp://127.0.0.1:5575 | 11m (just patched) |
| HL test bot | 🟡 RUNNING (paper) | `bot_HL_Test` | uses `configs/HL_Test.yaml` | 10m (just restarted) |

**Total pm2 processes:** 28 (26 PM-related + 2 HL-related). Все non-stopped процессы `online`.

**Active HL outcome:** mainnet #5 (BTC daily, target $81,041, expires 2026-05-08 06:00 UTC).

---

## Что произойдёт после next mainnet settlement

```
2026-05-08 06:00 UTC settlement:
  ✅ collector handles automatically (lifecycle filter + GC)
  🟡 feeder will FREEZE (hardcoded OUTCOME_ID=5, no auto-discovery)
  🟡 bot will receive NO DATA after freeze
  
Manual recovery procedure:
  1. Find new OUTCOME_ID via outcome_meta tail
  2. sed -i "s|OUTCOME_ID = 5|OUTCOME_ID = <new>|" ~/HL/hl_feeder.py
  3. pm2 restart hl_feeder bot_HL_Test
  
Time to recovery: ~5 min if action taken at 06:01 UTC
```

---

## Files на VPS

### Working files

```
/home/moltbot/HL/hl_feeder.py                       # OUTCOME_ID=5 (hardcoded)
/home/moltbot/HL/monitor_btc_main.py                # working monitor for bot_HL_Test
/home/moltbot/gabagool/configs/HL_Test.yaml         # data_source: zmq://127.0.0.1:5575
                                                     # market_duration_sec=900 (NOT calibrated)
```

### Backup files

```
/home/moltbot/HL/hl_feeder.py.bak.20260505_outcome2_to_3      # storm fix era
/home/moltbot/HL/hl_feeder.py.bak.20260507_*                  # before patch to outcome 5
/home/moltbot/HL/hl_collector/backup_20260505/                # collector backup pre-lifecycle-fix
/home/moltbot/gabagool/configs/HL_Test.yaml.bak.*             # if calibration starts
```

### Data accumulation

```
/home/moltbot/HL/data/raw/mainnet/<YYYY-MM-DD>/     # daily JSONL streams
/home/moltbot/HL/data/raw/mainnet/settlements/      # settlement_3_*, settlement_4_*, settlement_5_* (pending)
/home/moltbot/HL/data/raw/testnet/<YYYY-MM-DD>/     # testnet daily streams
/home/moltbot/HL/data/raw/testnet/settlements/      # 100+ HYPE 15m settlements (golden archive)
```

---

## `hl_feeder.py` — current behavior

**Hardcoded на:**
- `OUTCOME_ID = 5` (mainnet BTC daily)
- `YES_TOKEN_ID = "50"` / `NO_TOKEN_ID = "51"`
- File prefixes: `book_h50_`, `book_h51_`, `trades_h50_`, `trades_h51_`, `outcome_meta_`

**Конвертация форматов:**

| HL format | → | Polymarket format |
|---|---|---|
| `coin: "#50"` | → | `is_yes: true`, `asset_id: "50"` |
| `coin: "#51"` | → | `is_yes: false`, `asset_id: "51"` |
| `bids: [{px, sz, n}]` | → | `bids: [{price, size}]` |
| `side: "A"` (ask hit) | → | `side: "BUY"` |
| `side: "B"` (bid hit) | → | `side: "SELL"` |
| `outcome_meta` | → | `market_info` (slug synthetic, expiry → window_end) |

**Trade price/size — float**, not str (важно — bridge `ZmqMarketSubscriber.run()` does direct numeric comparison `if size >= 1.0`).

**BTC oracle:** feeder fetches Binance BTC каждую секунду, publishes как `btc_update`. Не зависит от Polymarket gateway.

---

## `HL_Test.yaml` — bot config (current state)

Скопирован из `Control_Baseline.yaml` 2026-05-04. В начало добавлены:

```yaml
bot_id: HL_Test
data_source: zmq://127.0.0.1:5575
emergency_dump_enabled: false
```

**NOT calibrated** для HL specifics:
- `market_duration_sec: 900` (PM 15min default) — не подходит для HL daily 86400s
- остальные thresholds (`cvd_skew`, `hunter`, `healer`) — PM Control_Baseline values
- TICK_SIZE через strategy code = 0.01 (hardcoded in `grid_strategy.py`)

При калибровке — см. [[Calibration_Plan]].

---

## pm2 commands (для reference)

### Status check

```bash
pm2 list | grep -E "hl_|bot_HL"
pm2 logs hl_collector --lines 50 --nostream
pm2 logs hl_feeder --lines 50 --nostream
pm2 logs bot_HL_Test --lines 50 --nostream
```

### Stop bot/feeder (если возвращаемся after frozen state)

```bash
pm2 stop hl_feeder bot_HL_Test
# collector keep running — handles settlements automatically
```

### Restart with new outcome (manual procedure)

```bash
TODAY=$(date -u +%Y-%m-%d)
NEW_ID=$(tail -1 ~/HL/data/raw/mainnet/$TODAY/outcome_meta_*.jsonl | \
  python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(next(o['outcome'] for o in d['outcomes'] if o['description'].startswith('class:priceBinary')))")

cp ~/HL/hl_feeder.py ~/HL/hl_feeder.py.bak.$(date -u +%Y%m%d_%H%M)
sed -i "s|^OUTCOME_ID = .*$|OUTCOME_ID = $NEW_ID|" ~/HL/hl_feeder.py
pm2 restart hl_feeder bot_HL_Test
sleep 30
pm2 logs hl_feeder --lines 20 --nostream  # verify
```

### Original deployment commands (для reference при re-deploy)

**Collector:**
```bash
# Уже configured в pm2 save, см. ~/HL/hl_collector/config.yaml
pm2 start hl_collector
```

**Feeder:**
```bash
pm2 start ~/HL/hl_feeder.py \
  --name hl_feeder \
  --interpreter python3 \
  --cwd /home/moltbot/HL \
  --restart-delay 3000 \
  --max-memory-restart 256M
```

**Bot:**
```bash
pm2 start /home/moltbot/gabagool/main.py \
  --name bot_HL_Test \
  --interpreter /home/moltbot/gabagool/venv/bin/python \
  --cwd /home/moltbot/gabagool \
  --restart-delay 5000 \
  --max-memory-restart 384M \
  -- -c configs/HL_Test.yaml paper --strategy grid
```

---

## Подтверждённые observations

✅ **Feeder работает:** typical heartbeat `OB Y/N: 112/112 | TR Y/N: 45/45 | MI: 60 | BTC: $80,335`

✅ **ZMQ pipe valid:** все 4 типа сообщений долетают (orderbook, trade, market_info, btc_update)

✅ **Bot bridge works:** `[BRIDGE] Status | Market: hl-btc-1d-... | T-XXXXs | Pos: Y0/N0 | P&L: 0.0000`

✅ **Strategy receives HL data:** `[TICK] BTC=$80,362 | YES=0.605(46)/0.605 NO=0.395(50)/0.395 | bid_sum=1.00 ask_sum=1.00`

✅ **DCS_KILL filter works:** v3.4.1 actively blocks expensive side at FV>0.55 / FV<0.45

✅ **Paper run #1 result:** +$1.79 paper P&L over 16 hours on outcome 3

---

## Известные quirks

См. [[README]] раздел "Issues & known quirks" для actual list.

Главные:
- `market_duration_sec=900` mismatch с HL daily — quick fix in YAML
- TIME_STOP false alarm на старте — cosmetic, исчезает после first orderbook
- StrikeFetcher returns garbage — display only, не блокер

---

## Связи

- **Entry point:** [[00_HL_START_HERE]]
- **HL status:** [[README]]
- **Roadmap:** [[Roadmap]]
- **Auto-discovery design (Priority 2):** [[Auto_Discovery_Design]]
- **Calibration plan (Priority 1):** [[Calibration_Plan]]
- **Feeder code:** [[../Refactor_Code/05_hl_feeder]]
- **ADR:** [[../ADR/2026-05-04_pragmatic_hl_feeder_path]]
