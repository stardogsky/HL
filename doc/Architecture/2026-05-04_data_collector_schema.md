tags: [architecture, data_collector, hl, schema, design, IMPLEMENTED]
date: 2026-05-04
status: IMPLEMENTED — collector deployed and running, this doc is historical reference only
parent: meta/2026-05-04_init_session_hl_track_activated.md
phase: 0 (Discovery & Data Collection)
implementation_notes: |
  Deployed 2026-05-04 morning to ~/HL/hl_collector/ on VPS.
  Patched 2026-05-05 12:45 UTC (subscription lifecycle fix — see ADR).
  Running clean since then. This doc preserved as design reference.

# 🗂️ HL Data Collector — Schema Design (IMPLEMENTED)

> **STATUS: IMPLEMENTED.** Этот документ — historical design reference.
> Real deployed code: `~/HL/hl_collector/` on VPS.
> Lifecycle fix applied 2026-05-05: [[../../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]]

## Цель

Полная фиксация структуры собираемых данных с Hyperliquid mainnet + testnet до написания кода. Цель — replay-quality логи: можем восстановить состояние любого outcome'а на любой момент времени.

## Решения по scope (consensus 2026-05-04)

| Решение | Выбор | Rationale |
|---|---|---|
| Endpoints | mainnet **+** testnet | Testnet имеет period:3m outcomes (HYPE example) — это HL roadmap, тестируем нашу framework на short windows ДО mainnet rollout |
| Address tracking | Записываем + per-address profile | Public `WsTrade.users[buyer,seller]` даёт уникальный edge: smart money detection, informed flow attribution. На Polymarket недоступно |
| Settlement watcher | Отдельный процесс с phase-based polling | Самый информативный момент в 24h окне — последние 30 минут перед 06:00 UTC. Без detailed capture упускаем golden data для FV модели |

## Critical findings из docs

1. **`outcomeMeta` помечен "(testnet-only)"** в spot.md — нужна эмпирическая проверка работает ли на mainnet. План: discovery script проверит первым делом
2. **Outcome side = ОТДЕЛЬНЫЙ coin** со своим orderbook. Encoding: `coin = "#<10*outcome+side>"`. На одну outcome-пару нужно 2 × {l2Book, trades, bbo}
3. **`WsBook` = full snapshot не diff** — pushes на каждом блоке (≥0.5s). Упрощает запись (не нужна reconstruction логика)
4. **`WsBbo` = change-driven** — экономно
5. **`WsTrade.tid` = 50-bit hash (buyer_oid, seller_oid)**. Глобально уникален в композиции `(block_time, coin, tid)`
6. **`WsTrade.users` = [buyer_addr, seller_addr]** — публичные ончейн адреса. Это структурный edge

## Архитектура слоёв данных

### Layer A: State Snapshots
| Stream | Source | Frequency | Storage est. (per coin/day, gz) |
|---|---|---|---|
| `l2Book` snapshots | WS subscription | ≥0.5s, change-driven | ~50 MB |
| `bbo` changes | WS subscription | change-driven (sparser) | ~5 MB |
| `allMids` poll | REST poll | 1-3s | ~3 MB |
| `activeAssetCtx` | WS subscription | per-block | ~10 MB |

### Layer B: Atomic Events
| Stream | Source | Critical fields |
|---|---|---|
| `trades` | WS subscription | `ts, side, px, sz, tid, hash, buyer, seller` |

### Layer C: Metadata
| Stream | Source | Frequency | Why |
|---|---|---|---|
| `outcomeMeta` | REST poll | 60s | Detection нового instance + targetPrice rotation |
| `spotMetaAndAssetCtxs` | REST poll | 5min | szDecimals (тики/лоты) могут меняться |

## JSONL Schema

### `trades_<coin>.jsonl.gz`
```json
{
  "ts_local": 1714834567.123456,
  "ts_exchange": 1714834567105,
  "coin": "#1230",
  "side": "B",
  "px": "0.5145",
  "sz": "100",
  "tid": 123456789012,
  "hash": "0x...",
  "buyer": "0x...",
  "seller": "0x..."
}
```

### `book_<coin>.jsonl.gz`
```json
{
  "ts_local": 1714834567.123456,
  "ts_exchange": 1714834567105,
  "coin": "#1230",
  "bids": [{"px": "0.5144", "sz": "150", "n": 3}, ...],
  "asks": [{"px": "0.5146", "sz": "120", "n": 2}, ...]
}
```

### `bbo_<coin>.jsonl.gz`
```json
{
  "ts_local": 1714834567.123456,
  "ts_exchange": 1714834567105,
  "coin": "#1230",
  "bid_px": "0.5144", "bid_sz": "150", "bid_n": 3,
  "ask_px": "0.5146", "ask_sz": "120", "ask_n": 2
}
```

### `markprice.jsonl.gz`
```json
{
  "ts_local": 1714834567.123,
  "btc_mark": "78214.5",
  "btc_mid": "78212.0",
  "outcome_yes_mid": "0.5145",
  "outcome_no_mid": "0.4853",
  "yes_no_sum": "0.9998"
}
```

### `outcomemeta.jsonl.gz` (только при изменении)
```json
{
  "ts_local": 1714834567,
  "outcome_id": 123,
  "name": "Recurring",
  "description": "class:priceBinary|underlying:BTC|expiry:20260505-0600|targetPrice:78213|period:1d",
  "yes_coin": "#1230",
  "no_coin": "#1231",
  "settlement_ts_utc": 1714888800
}
```

### `settlement_<outcome>_<expiry>.json` (per settlement event)
```json
{
  "outcome_id": 123,
  "expiry_ts_utc": 1714888800,
  "underlying": "BTC",
  "target_price": 78213,
  "period": "1d",
  "settlement_event": {
    "ts_utc": 1714888800,
    "btc_mark_at_settlement": 78230.5,
    "btc_mark_t0": 78228.0,
    "btc_mark_t1": 78231.2,
    "interpolated_target_check": 78230.1,
    "winning_side": "Yes",
    "yes_payoff": 1.0,
    "no_payoff": 0.0
  },
  "pre_settlement_t_minus_60s": {...},
  "pre_settlement_t_minus_5min": {...},
  "pre_settlement_t_minus_30min": {...},
  "post_settlement_new_instance": {...}
}
```

## Settlement Watcher Phases

```
T-30min → T-10min:    TIGHT mode (book snapshot на каждое изменение, без decimation)
T-10min → T-5min:     CRITICAL mode (+ allMids poll каждые 100ms)
T-5min → T-1min:      LOCKDOWN (synchronous flush на каждое изменение)
T-1min → T:           FINAL_60S (snapshot каждые 50ms допустимо)
T = 0:                SETTLEMENT EVENT capture → settlement_<outcome>_<expiry>.json
T+1min → T+5min:      AFTER (detect новый instance deployment)
```

## Per-Address Profile (Layer 2 aggregation)

**Не часть realtime collector** — отдельный batch process (cron daily/hourly).

Из накопленных `trades_*.jsonl.gz` строит:

```python
AddressProfile {
  address: "0x...",
  
  # Volume
  total_volume_usdc, num_trades, trades_per_day,
  
  # Side preference
  pct_buyer_yes, pct_buyer_no, pct_seller_yes, pct_seller_no,
  
  # Maker/taker inferred
  pct_likely_maker, pct_likely_taker,
  
  # Settlement performance (THE EDGE)
  settlement_pnl_total, win_rate_at_settlement, pnl_per_trade,
  
  # Behavioral signature
  avg_holding_time_sec, trade_size_distribution,
  
  # Timing pattern
  trades_in_last_hour_before_settlement, trades_at_random_times,
}
```

**Edge источники:**
- Smart money: кто systematically выигрывает на settlement → их позиции = better FV
- Informed flow: кто торгует только последний час → potential insider mark price info
- MM competitors: кто доминирует в maker quotes → их стиль known
- Whales: кто двигает цену через большие лоты

**Этический фрейм:** публичные ончейн данные → анонимизированная статистическая модель. Не публикуем, не атакуем.

## Architecture diagram

```
~/hl_research/data_collector/
├── config.yaml                # endpoints, outcomes, paths, polling intervals
├── collector.py               # WS event loop per endpoint
├── poller.py                  # REST polls per endpoint
├── settlement_watcher.py      # phase-based scheduler + golden data dump
├── healthcheck.py             # liveness + alerts
└── address_profiler.py        # batch aggregation (cron)

~/hl_research/data/raw/
├── mainnet/<YYYY-MM-DD>/
│   ├── trades_<coin>.jsonl.gz
│   ├── book_<coin>.jsonl.gz
│   ├── bbo_<coin>.jsonl.gz
│   ├── markprice.jsonl.gz
│   ├── outcomemeta.jsonl.gz
│   └── settlement_<outcome>_<expiry>.json
└── testnet/<YYYY-MM-DD>/
    └── ... (зеркало)

~/hl_research/data/profiles/
├── mainnet/address_profiles_<YYYY-MM-DD>.parquet
└── testnet/...
```

## Endpoints

- Mainnet WS: `wss://api.hyperliquid.xyz/ws`
- Mainnet REST: `https://api.hyperliquid.xyz/info`
- Testnet WS: `wss://api.hyperliquid-testnet.xyz/ws`
- Testnet REST: `https://api.hyperliquid-testnet.xyz/info`

## Storage budget

- Mainnet: ~100 MB/day compressed (1 outcome pair × 4 streams + metadata)
- Testnet: ~30-50 MB/day (zhuzhul'ный volume)
- 30 дней retention raw: ~3-5 GB total
- Profiles parquet: ~10-50 MB/month
- Settlement files: ~1 MB per settlement (1/day mainnet + N/day testnet)
- **Total VPS disk requirement: ~10 GB** (с запасом)

## Reconnect & gap handling

WS disconnect — periodic, без announcement (docs explicit). Стратегия:
1. Detect disconnect (no messages > 30s OR explicit close)
2. Reconnect with exponential backoff (1s, 2s, 4s, max 30s)
3. Resubscribe ALL streams
4. Treat next message с `isSnapshot: true` as new state (overwrite local)
5. Log gap event с timestamps в `gaps.jsonl.gz` (для downstream gap-aware processing)

## Запуск (планируется)

- VPS Vultr: pm2 process `hl_collector_mainnet`, `hl_collector_testnet`, `hl_settlement_watcher`
- Изоляция от production fleet: отдельные log files, отдельная directory
- Healthcheck: каждые 5min check rates per stream — alert если drop в 0

## Open implementation questions

1. **Async lib choice:** `aiohttp` + `websockets`, или Python SDK `hyperliquid-python-sdk`?
   - SDK даёт готовую WS обёртку с reconnect, но добавляет dependency
   - Manual = больше кода но полный контроль
2. **Compression strategy:** gzip каждый час при rotation, или streaming gzip writes?
   - Hourly = проще, atomic. Streaming = compact но complex.
3. **Schema versioning:** добавлять `schema_v: 1` в каждый JSONL line? (для будущих breaking changes)
4. **Rate limit для poller:** docs упоминают rate limits — нужно проверить лимиты для unauthenticated REST

## Related

- `meta/2026-05-04_init_session_hl_track_activated.md` — parent init
- `Architecture/2026-05-01_decision_multivenue_deferred.md` — старое DEFERRED, триггер сработал
- `Architecture/2026-05-01_multivenue_refactor_research_roadmap.md` — research roadmap (HL добавляется как новая платформа)
- `Hyperliquid/Docs/for-developers/api/websocket/subscriptions.md` — full WS spec
- `Hyperliquid/Docs/for-developers/api/asset-ids.md` — outcome encoding (`#<10*outcome+side>`)
- `Hyperliquid/Docs/for-developers/api/info-endpoint.md` — REST spec
- `Hyperliquid/Docs/trading/contract-specifications.md#recurring-outcomes` — settlement формула

## Next step

После consensus по этому документу — пишем `hl_discover.py` (one-shot REST dump) для эмпирической проверки:
1. Работает ли `outcomeMeta` на mainnet (или только testnet)
2. Реальные szDecimals / tick size текущего BTC daily
3. Реальная depth и spread distribution (one-shot snapshot)
4. Существуют ли testnet outcomes сейчас и какие periods
