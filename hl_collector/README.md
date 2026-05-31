# HL Collector — Deployment Guide

## Что это

Параллельный процесс который собирает все publically доступные данные с Hyperliquid (mainnet + testnet) для последующего построения симулятора и торговой стратегии. Не торгует. Только пишет.

## Что собирается

**На каждый активный outcome (BTC mainnet daily, BTC/HYPE testnet, и любые новые когда появятся):**

| Файл | Что внутри |
|---|---|
| `book_<coin>_<HH>.jsonl.gz` | L2 orderbook snapshots (top 20 levels с обеих сторон), на каждый push (~0.5s) |
| `bbo_<coin>_<HH>.jsonl.gz` | Best bid/ask на каждое изменение |
| `trades_<coin>_<HH>.jsonl.gz` | Все сделки с buyer/seller addresses, hash, tid |
| `asset_ctx_<coin>_<HH>.jsonl.gz` | mark price, daily volume context |
| `all_mids_rest_<HH>.jsonl.gz` | Mid prices всех монет, snapshot каждую секунду |
| `outcome_meta_<HH>.jsonl.gz` | Метаданные outcomes (детект новых instances + targetPrice rotation) |
| `latency_<HH>.jsonl.gz` | RTT measurements каждую минуту |
| `healthcheck_<HH>.jsonl.gz` | Stats snapshots каждые 5 мин |
| `gaps_<HH>.jsonl.gz` | Маркеры WebSocket disconnect periods |
| `settlements/settlement_<id>_<expiry>.json` | Per-event golden data на каждый settlement |

Данные пишутся в `<output_base>/raw/<network>/<YYYY-MM-DD>/` с hourly rotation + gzip.

## Установка на VPS

### 1. Скопируй файлы через FileZilla

В `/home/moltbot/hl_collector/`:
```
config.yaml
discovery.py
ecosystem.config.js
main.py
poller.py
README.md
requirements.txt
settlement.py
writer.py
ws_client.py
```

### 2. Установи зависимости

```bash
ssh moltbot@<vps>
cd ~/hl_collector
pip3 install -r requirements.txt
```

Если Python 3.10+ не установлен:
```bash
sudo apt update && sudo apt install python3.10 python3-pip -y
```

### 3. Создай output директории

```bash
mkdir -p ~/hl_research/data/raw
```

### 4. Smoke test (запуск на 30 секунд для проверки)

```bash
cd ~/hl_collector
python3 main.py --config config.yaml
```

Должно появиться примерно такое:
```
2026-05-04 ... [INFO] root: HL Collector starting with config: config.yaml
2026-05-04 ... [INFO] root: network 'mainnet' configured
2026-05-04 ... [INFO] root: network 'testnet' configured
2026-05-04 ... [INFO] root: [mainnet] new outcomes detected: {2}
2026-05-04 ... [INFO] root: [mainnet] subscribed to 2 new coins: ['#20', '#21']
2026-05-04 ... [INFO] root: [mainnet/settlement] tracking outcome #2 (BTC 1d, expiry 20260505-0600)
2026-05-04 ... [INFO] ws_client: [mainnet] connecting to wss://api.hyperliquid.xyz/ws
2026-05-04 ... [INFO] ws_client: [mainnet] connected, 8 subscriptions resubscribed
...
```

Через ~30 сек `Ctrl+C` для остановки. Проверь что появились файлы:
```bash
ls -la ~/hl_research/data/raw/mainnet/$(date -u +%Y-%m-%d)/
ls -la ~/hl_research/data/raw/testnet/$(date -u +%Y-%m-%d)/
```

Должны быть несколько `.jsonl` файлов (без `.gz` пока — gzip только при rotation).

### 5. Запусти под pm2

```bash
cd ~/hl_collector
pm2 start ecosystem.config.js
pm2 save                    # сохранить чтобы автостарт после reboot
pm2 logs hl_collector       # смотреть live
pm2 status                  # проверить health
```

### 6. Мониторинг

Tail основного лога:
```bash
pm2 logs hl_collector --lines 100
```

Просмотр последних healthcheck'ов:
```bash
ls -lh ~/hl_research/data/raw/mainnet/$(date -u +%Y-%m-%d)/
tail -1 ~/hl_research/data/raw/mainnet/$(date -u +%Y-%m-%d)/healthcheck_*.jsonl
```

Размер накопленных данных:
```bash
du -sh ~/hl_research/data/
```

Считать примерно ~50-100 MB/day mainnet + ~100-200 MB/day testnet (HYPE 15m даёт много trades).

## Нюансы

### outcomeMeta polling каждую минуту
Если HL раскатает новый outcome (например BTC 1h окно или ETH daily) — collector подхватит автоматически в течение 60 секунд и начнёт subscribe.

### Settlement автодетект
Watcher парсит expiry из description и сам переключается в режим CRITICAL за 5 минут до настоящего settlement, делает snapshots на отметках T-30, T-15, T-10, T-5, T-2, T-1 минуты. На testnet HYPE 15m это происходит ~96 раз в день.

### WebSocket reconnect
При обрыве пишется `gaps` event. Backoff 1s → 2s → 4s → ... → 30s max. Все subscriptions автоматически восстанавливаются.

### Что делать если нужно остановить

```bash
pm2 stop hl_collector
```

Все открытые .jsonl файлы корректно закроются и заархивируются. Никаких потерь данных.

### Что делать если нужно изменить параметры

Отредактируй `config.yaml`:
```bash
nano ~/hl_collector/config.yaml
pm2 restart hl_collector
```

Изменения вступят в силу сразу.

### Логи pm2

```bash
~/.pm2/logs/hl_collector-out.log    # stdout
~/.pm2/logs/hl_collector-err.log    # stderr
```

Ротируются автоматически pm2.

## Что делать когда накопится 1-3 дня данных

Скинь мне output этой команды:
```bash
ls -R ~/hl_research/data/raw/mainnet/$(date -u +%Y-%m-%d)/ | head -50
ls -R ~/hl_research/data/raw/testnet/$(date -u +%Y-%m-%d)/ | head -50
du -sh ~/hl_research/data/
tail -3 ~/hl_research/data/raw/mainnet/$(date -u +%Y-%m-%d)/healthcheck_*.jsonl
```

Я напишу analysis скрипты которые ответят на твои вопросы:
- "что сейчас происходит на рынке"
- "насколько конкурентная среда"
- "какой потенциальный edge"
- "как зарабатывать прямо сейчас"

И параллельно начнём строить replay engine для симуляции.

## Troubleshooting

**Не запускается, ImportError websockets:**
```bash
pip3 install --upgrade websockets aiohttp PyYAML
```

**Permission denied при создании папок:**
Проверь что `output_base` в `config.yaml` указывает на путь куда у moltbot есть write rights.

**pm2 не видит python3:**
```bash
which python3
# отредактируй ecosystem.config.js: interpreter: "/usr/bin/python3" (полный путь)
```

**WS сразу обрывается:**
Скорее всего firewall. Проверь:
```bash
curl -v https://api.hyperliquid.xyz/info -X POST -d '{"type":"allMids"}' -H 'Content-Type: application/json'
```
Должен вернуть JSON с ценами.

**Большой объём данных:**
Если `du -sh ~/hl_research/data/` показывает > 5 GB и хочешь освободить:
```bash
# архив старых дней
cd ~/hl_research/data/raw/mainnet
tar -czf old_$(date -u +%Y%m%d).tar.gz $(ls | head -7)  # архив старых 7 дней
rm -rf $(ls | head -7)                                   # удалить
```
