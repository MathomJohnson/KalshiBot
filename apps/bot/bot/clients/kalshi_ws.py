"""
Kalshi WebSocket client for real-time market data.

Handles reconnect, resubscribe, sequence gap detection, and REST resync fallback.
Not traditional webhooks — Kalshi uses authenticated WebSocket streams.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import websockets
from websockets.exceptions import ConnectionClosed

from bot.clients.kalshi_rest import KalshiRestClient
from bot.config import Settings

logger = logging.getLogger(__name__)

MAX_BACKOFF = 60
INITIAL_BACKOFF = 1


class KalshiWebSocketClient:
    """Authenticated WebSocket client with reconnect and resync."""

    def __init__(
        self,
        settings: Settings,
        kalshi_rest: KalshiRestClient,
        on_ticker: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self._ws_url = settings.kalshi_ws_url
        self._kalshi_rest = kalshi_rest
        self._on_ticker = on_ticker
        self._subscribed_tickers: set[str] = set()
        self._running = False
        self._last_seq: dict[str, int] = {}
        self._key_id = settings.kalshi_api_key_id
        self._private_key_pem = settings.kalshi_private_key

    def set_subscriptions(self, tickers: list[str]) -> None:
        """Update the set of market tickers to subscribe to."""
        self._subscribed_tickers = set(tickers)

    async def run(self) -> None:
        """Main WebSocket loop with exponential backoff reconnect."""
        self._running = True
        backoff = INITIAL_BACKOFF

        while self._running:
            try:
                headers = self._auth_headers()
                async with websockets.connect(self._ws_url, additional_headers=headers) as ws:
                    logger.info("WebSocket connected")
                    backoff = INITIAL_BACKOFF
                    await self._subscribe_all(ws)

                    async for message in ws:
                        await self._handle_message(ws, message)

            except ConnectionClosed as exc:
                logger.warning("WebSocket closed: %s", exc)
            except Exception as exc:
                logger.error("WebSocket error: %s", exc)

            if self._running:
                logger.info("Reconnecting in %ds...", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

    def stop(self) -> None:
        """Stop the WebSocket loop."""
        self._running = False

    def _auth_headers(self) -> dict[str, str]:
        """Build WebSocket handshake auth headers using REST client signing."""
        import datetime as dt

        path = "/trade-api/ws/v2"
        timestamp_ms = str(int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000))
        signature = self._kalshi_rest._sign(timestamp_ms, "GET", path)
        return {
            "KALSHI-ACCESS-KEY": self._key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    async def _subscribe_all(self, ws: Any) -> None:
        """Subscribe to ticker channel for all mapped tickers."""
        if not self._subscribed_tickers:
            cmd = {"id": 1, "cmd": "subscribe", "params": {"channels": ["ticker"]}}
        else:
            cmd = {
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["ticker"],
                    "market_tickers": list(self._subscribed_tickers),
                },
            }
        await ws.send(json.dumps(cmd))
        logger.info("Subscribed to %d tickers", len(self._subscribed_tickers))

    async def _handle_message(self, ws: Any, raw: str | bytes) -> None:
        """Process incoming WebSocket message."""
        data = json.loads(raw)
        msg_type = data.get("type", "")

        if msg_type == "ticker":
            ticker = data.get("msg", {}).get("market_ticker", "")
            msg_data = data.get("msg", {})
            seq = data.get("seq")

            if seq is not None and ticker:
                last = self._last_seq.get(ticker)
                if last is not None and seq > last + 1:
                    logger.warning("Sequence gap for %s: expected %d, got %d — resyncing", ticker, last + 1, seq)
                    await self._resync_ticker(ticker)
                self._last_seq[ticker] = seq

            if ticker:
                self._on_ticker(ticker, {
                    "yes_bid": _normalize_price(msg_data.get("yes_bid_dollars") or msg_data.get("yes_bid")),
                    "yes_ask": _normalize_price(msg_data.get("yes_ask_dollars") or msg_data.get("yes_ask")),
                    "no_bid": _normalize_price(msg_data.get("no_bid_dollars") or msg_data.get("no_bid")),
                    "no_ask": _normalize_price(msg_data.get("no_ask_dollars") or msg_data.get("no_ask")),
                })

        elif msg_type == "error":
            logger.error("WebSocket error message: %s", data)

    async def _resync_ticker(self, ticker: str) -> None:
        """REST resync for a market after sequence gap."""
        try:
            market = self._kalshi_rest.get_market(ticker)
            self._on_ticker(ticker, {
                "yes_bid": _normalize_price(market.get("yes_bid_dollars") or market.get("yes_bid")),
                "yes_ask": _normalize_price(market.get("yes_ask_dollars") or market.get("yes_ask")),
                "no_bid": _normalize_price(market.get("no_bid_dollars") or market.get("no_bid")),
                "no_ask": _normalize_price(market.get("no_ask_dollars") or market.get("no_ask")),
            })
            logger.info("REST resync complete for %s", ticker)
        except Exception as exc:
            logger.error("REST resync failed for %s: %s", ticker, exc)


def _normalize_price(value: Any) -> float | None:
    """Normalize Kalshi price to 0-1 decimal."""
    if value is None:
        return None
    val = float(value)
    return val / 100.0 if val > 1.0 else val
