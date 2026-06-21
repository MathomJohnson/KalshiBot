"""
KalshiBot worker entry point.

Runs three concurrent loops (fetcher, strategy, executor) plus optional WebSocket mode.
Designed as a long-running Railway process.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import threading
import time
from typing import Any

from bot.clients.kalshi_rest import KalshiRestClient
from bot.clients.kalshi_ws import KalshiWebSocketClient
from bot.clients.odds_api import OddsApiClient
from bot.clients.supabase_client import create_supabase_client
from bot.config import Settings, get_settings
from bot.loops.executor import ExecutorLoop
from bot.loops.fetcher import FetcherLoop
from bot.loops.strategy import StrategyLoop
from bot.repositories.db import Repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("bot.main")


class BotWorker:
    """Orchestrates fetcher, strategy, and executor loops."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._running = True
        self._ws_client: KalshiWebSocketClient | None = None
        self._ws_thread: threading.Thread | None = None

        supabase = create_supabase_client(settings)
        self._repo = Repository(supabase)
        self._kalshi = KalshiRestClient(settings)
        self._odds = OddsApiClient(settings)

        self._fetcher = FetcherLoop(
            self._repo, self._kalshi, self._odds,
            settings.worker_id, settings.deployed_version,
        )
        self._strategy = StrategyLoop(
            self._repo, settings.worker_id, settings.deployed_version,
        )
        self._executor = ExecutorLoop(
            self._repo, self._kalshi,
            settings.worker_id, settings.deployed_version,
        )

        self._ticker_to_mapping: dict[str, str] = {}

    def start(self) -> None:
        """Start all loops."""
        logger.info("KalshiBot worker starting (env=%s, version=%s)",
                     self._settings.bot_env, self._settings.deployed_version)

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        self._maybe_start_websocket()

        last_fetcher = last_strategy = last_executor = 0.0

        while self._running:
            now = time.monotonic()

            if now - last_fetcher >= self._settings.fetcher_tick_seconds:
                self._fetcher.tick()
                last_fetcher = now

            if now - last_strategy >= self._settings.strategy_tick_seconds:
                self._strategy.tick()
                last_strategy = now

            if now - last_executor >= self._settings.executor_tick_seconds:
                self._executor.tick()
                last_executor = now

            self._refresh_websocket_subscriptions()
            time.sleep(0.5)

        self._cleanup()

    def _maybe_start_websocket(self) -> None:
        """Start WebSocket client if configured."""
        try:
            config = self._repo.get_bot_config()
            if config.get("kalshi_market_data_mode") != "websocket":
                return

            self._refresh_ticker_map()

            def on_ticker(ticker: str, data: dict[str, Any]) -> None:
                mapping_id = self._ticker_to_mapping.get(ticker)
                if mapping_id:
                    self._fetcher.write_ws_snapshot(mapping_id, ticker, data)

            self._ws_client = KalshiWebSocketClient(
                self._settings, self._kalshi, on_ticker,
            )
            self._ws_client.set_subscriptions(list(self._ticker_to_mapping.keys()))

            def run_ws() -> None:
                asyncio.run(self._ws_client.run())

            self._ws_thread = threading.Thread(target=run_ws, daemon=True)
            self._ws_thread.start()
            logger.info("WebSocket mode started with %d tickers", len(self._ticker_to_mapping))
        except Exception as exc:
            logger.error("Failed to start WebSocket: %s", exc)
            config = self._repo.get_bot_config()
            if config.get("websocket_fallback_to_polling"):
                logger.info("Falling back to polling mode")

    def _refresh_ticker_map(self) -> None:
        """Build ticker → mapping_id lookup from active mappings."""
        mappings = self._repo.get_active_mappings()
        self._ticker_to_mapping = {}
        for m in mappings:
            kalshi = m.get("kalshi_markets", {})
            ticker = kalshi.get("market_ticker")
            if ticker:
                self._ticker_to_mapping[ticker] = m["id"]

    def _refresh_websocket_subscriptions(self) -> None:
        """Periodically refresh WebSocket subscriptions."""
        if self._ws_client is None:
            return
        self._refresh_ticker_map()
        self._ws_client.set_subscriptions(list(self._ticker_to_mapping.keys()))

    def _shutdown(self, *_args: Any) -> None:
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received")
        self._running = False
        if self._ws_client:
            self._ws_client.stop()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._kalshi.close()
        self._odds.close()
        logger.info("Worker stopped")


def main() -> None:
    """Entry point for Railway: python -m bot.main"""
    settings = get_settings()
    worker = BotWorker(settings)
    worker.start()


if __name__ == "__main__":
    main()
