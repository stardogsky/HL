"""
HL Collector — main entry point.

Orchestrates per network:
- WebSocket client (subscribes to dynamic outcome list)
- REST poller (allMids, outcomeMeta, spotMeta, latency)
- Settlement watcher (phase-based capture)
- Periodic discovery refresh (subscribe to new outcomes if found)
- Healthcheck logger

Usage:
  python3 main.py [--config config.yaml]

Output goes to <output_base>/raw/<network>/<YYYY-MM-DD>/...
"""
import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

import yaml

from discovery import filter_outcomes, OutcomeInfo
from poller import Poller
from settlement import SettlementWatcher
from writer import JsonlWriter, JsonFileWriter
from ws_client import WsClient


def setup_logging(level_str: str = "INFO"):
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


class NetworkContext:
    """Bundle all per-network components."""

    def __init__(self, network: str, cfg: dict, jsonl_writer: JsonlWriter, json_writer: JsonFileWriter):
        self.network = network
        self.cfg = cfg
        self.jsonl_writer = jsonl_writer
        self.json_writer = json_writer
        self.discovery_mode = cfg.get("discovery_mode", "all_real")

        self.ws = WsClient(
            network=network,
            ws_url=cfg["ws_url"],
            writer=jsonl_writer,
            reconnect_initial_delay=cfg["websocket"]["reconnect_initial_delay_sec"],
            reconnect_max_delay=cfg["websocket"]["reconnect_max_delay_sec"],
            ping_interval=cfg["websocket"]["ping_interval_sec"],
            ping_timeout=cfg["websocket"]["ping_timeout_sec"],
        )
        self.poller = Poller(
            network=network,
            rest_url=cfg["rest_url"],
            writer=jsonl_writer,
            all_mids_sec=cfg["polling"]["all_mids_sec"],
            outcome_meta_sec=cfg["polling"]["outcome_meta_sec"],
            spot_meta_sec=cfg["polling"]["spot_meta_sec"],
            latency_probe_sec=cfg["polling"]["latency_probe_sec"],
        )
        self.settlement = SettlementWatcher(
            network=network,
            poller=self.poller,
            json_writer=json_writer,
            jsonl_writer=jsonl_writer,
            pre_window_min=cfg["settlement"]["pre_window_minutes"],
            critical_window_min=cfg["settlement"]["critical_window_minutes"],
            poll_during_critical_sec=cfg["settlement"]["poll_during_critical_sec"],
            post_window_min=cfg["settlement"]["post_window_minutes"],
        )

        # Wire poller callback to discovery refresh
        self.poller.outcome_meta_callback = self._on_outcome_meta

        self._known_outcome_ids: set = set()
        self._subscribed_coins: set = set()

    async def _on_outcome_meta(self, network: str, outcomes_raw: list):
        """Called from poller when outcomeMeta is fetched. 
        Refresh subscriptions: add new active outcomes, remove settled ones.
        
        GC step (unsubscribe settled coins) is critical: leaving subscriptions
        to expired coins in ws_client._subscriptions causes silent disconnect on
        every reconnect. See Incidents/2026-05-05_hl_collector_reconnect_storm.md.
        """
        outcomes = filter_outcomes(outcomes_raw, mode=self.discovery_mode)

        # Update settlement watcher with current active outcomes
        await self.settlement.update_outcomes(outcomes)

        # Build set of currently ACTIVE coins (filter_outcomes already excluded expired)
        active_coins = set()
        for oc in outcomes:
            active_coins.add(oc.yes_coin)
            active_coins.add(oc.no_coin)

        # GC: unsubscribe from coins no longer active (settled / removed from outcomeMeta)
        coins_to_remove = self._subscribed_coins - active_coins
        for coin in coins_to_remove:
            for typ in ["l2Book", "bbo", "trades", "activeAssetCtx"]:
                await self.ws.unsubscribe({"type": typ, "coin": coin})
            self._subscribed_coins.discard(coin)
            logging.info(f"[{network}] GC: unsubscribed from settled coin {coin}")

        # Subscribe to new coins
        new_coins = []
        for oc in outcomes:
            for coin in (oc.yes_coin, oc.no_coin):
                if coin not in self._subscribed_coins:
                    new_coins.append(coin)
                    self._subscribed_coins.add(coin)

        for coin in new_coins:
            await self.ws.subscribe({"type": "l2Book", "coin": coin})
            await self.ws.subscribe({"type": "bbo", "coin": coin})
            await self.ws.subscribe({"type": "trades", "coin": coin})
            await self.ws.subscribe({"type": "activeAssetCtx", "coin": coin})

        # Track outcome IDs
        new_outcome_ids = set(o.outcome_id for o in outcomes) - self._known_outcome_ids
        if new_outcome_ids:
            logging.info(f"[{network}] new outcomes detected: {new_outcome_ids}")
            self._known_outcome_ids.update(new_outcome_ids)
        if new_coins:
            logging.info(f"[{network}] subscribed to {len(new_coins)} new coins: {new_coins}")

    async def initial_discovery(self):
        """One-shot discovery before main loops start — gives WS something to subscribe to."""
        outcomes_raw = await self.poller.fetch_outcome_meta_once()
        await self._on_outcome_meta(self.network, outcomes_raw)

    async def run_all(self):
        """Run all per-network tasks in parallel."""
        # Initial discovery first (so WS has subscriptions ready)
        await self.initial_discovery()

        await asyncio.gather(
            self.ws.connect_and_run(),
            self.poller.all_mids_loop(),
            self.poller.outcome_meta_loop(),
            self.poller.spot_meta_loop(),
            self.poller.latency_probe_loop(),
            self.settlement.watch_loop(),
            return_exceptions=False,
        )

    def get_stats(self) -> dict:
        return {
            "ws": self.ws.get_stats(),
            "poller": self.poller.get_stats(),
            "settlement": self.settlement.get_stats(),
            "subscribed_coins": len(self._subscribed_coins),
        }


async def healthcheck_loop(contexts: list[NetworkContext], writer: JsonlWriter, interval_sec: float):
    """Periodic stats report — printed to stdout AND written to log."""
    while True:
        await asyncio.sleep(interval_sec)
        try:
            for ctx in contexts:
                stats = ctx.get_stats()
                writer_stats = writer.get_stats()
                report = {
                    "ts_local": time.time(),
                    "network": ctx.network,
                    "stats": stats,
                }
                await writer.write(ctx.network, "healthcheck", report)
                logging.info(f"[{ctx.network}] HEALTH: ws_msgs={stats['ws']['msg_count']} "
                             f"connected={stats['ws']['connected']} "
                             f"subs={stats['subscribed_coins']} "
                             f"polls={stats['poller']} "
                             f"tracked={stats['settlement']['tracked_count']}")
        except Exception as e:
            logging.error(f"healthcheck error: {e}", exc_info=True)


async def amain(config_path: str):
    # Load config
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    setup_logging(cfg.get("logging", {}).get("level", "INFO"))
    logging.info(f"HL Collector starting with config: {config_path}")

    output_base = cfg["output_base"]
    Path(output_base).mkdir(parents=True, exist_ok=True)

    jsonl_writer = JsonlWriter(
        base_dir=output_base,
        gzip_after_close=cfg["storage"].get("gzip_after_close", True),
    )
    json_writer = JsonFileWriter(base_dir=output_base)

    contexts = []
    for network_name, net_cfg in cfg["networks"].items():
        if not net_cfg.get("enabled", True):
            logging.info(f"network '{network_name}' disabled in config — skipping")
            continue
        merged = {
            "ws_url": net_cfg["ws_url"],
            "rest_url": net_cfg["rest_url"],
            "discovery_mode": cfg["discovery"]["mode"],
            "polling": cfg["polling"],
            "settlement": cfg["settlement"],
            "websocket": cfg["websocket"],
        }
        ctx = NetworkContext(network_name, merged, jsonl_writer, json_writer)
        contexts.append(ctx)
        logging.info(f"network '{network_name}' configured")

    if not contexts:
        logging.error("no networks enabled — nothing to do")
        return 1

    health_interval = cfg["logging"].get("health_report_sec", 300)

    # Graceful shutdown
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def signal_handler():
        logging.info("shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass  # Windows

    main_tasks = [asyncio.create_task(ctx.run_all()) for ctx in contexts]
    main_tasks.append(asyncio.create_task(
        healthcheck_loop(contexts, jsonl_writer, health_interval)
    ))

    # Wait for shutdown signal OR a task crash
    done, pending = await asyncio.wait(
        main_tasks + [asyncio.create_task(stop_event.wait())],
        return_when=asyncio.FIRST_COMPLETED,
    )

    logging.info("shutting down...")

    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Close writers + sessions
    await jsonl_writer.close()
    for ctx in contexts:
        await ctx.poller.close()

    # Surface any task exceptions
    for task in done:
        if task.done() and not task.cancelled():
            exc = task.exception()
            if exc:
                logging.error(f"task crashed: {exc}", exc_info=exc)
                return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Hyperliquid market data collector")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    args = parser.parse_args()

    try:
        rc = asyncio.run(amain(args.config))
    except KeyboardInterrupt:
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
