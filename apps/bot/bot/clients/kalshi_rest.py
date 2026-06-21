"""
Kalshi REST API client with RSA-PSS request signing.

Auth headers only — never query string secrets.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from bot.config import Settings


class KalshiRestClient:
    """Signed REST client for Kalshi Trade API v2."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.kalshi_base_url.rstrip("/")
        self._key_id = settings.kalshi_api_key_id
        self._private_key_pem = settings.kalshi_private_key
        self._client = httpx.Client(timeout=30.0)
        self._private_key = self._load_private_key()

    def _load_private_key(self):
        """Load RSA private key from PEM string, raw base64, or file path."""
        pem = self._private_key_pem.strip().strip('"').strip("'")
        pem = pem.replace("\\n", "\n")

        if pem.startswith("-----BEGIN"):
            key_bytes = pem.encode()
        elif len(pem) < 260 and not pem.startswith("MII"):
            # Treat as file path when it doesn't look like key material.
            with open(pem, "rb") as f:
                key_bytes = f.read()
        else:
            # Raw base64 body without PEM headers (common when pasted into .env).
            body = "".join(pem.split())
            wrapped = "\n".join(
                body[i : i + 64] for i in range(0, len(body), 64)
            )
            key_bytes = f"-----BEGIN RSA PRIVATE KEY-----\n{wrapped}\n-----END RSA PRIVATE KEY-----\n".encode()

        try:
            return serialization.load_pem_private_key(key_bytes, password=None)
        except ValueError:
            # Retry PKCS#8 wrapper if RSA format failed.
            if b"BEGIN RSA PRIVATE KEY" in key_bytes:
                body = key_bytes.decode().replace("RSA PRIVATE KEY", "PRIVATE KEY")
                return serialization.load_pem_private_key(body.encode(), password=None)
            raise

    def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
        """Create Kalshi access signature."""
        message = f"{timestamp_ms}{method.upper()}{path}".encode()
        signature = self._private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode()

    def _headers(self, method: str, path: str) -> dict[str, str]:
        """Build authenticated request headers."""
        timestamp_ms = str(int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000))
        return {
            "KALSHI-ACCESS-KEY": self._key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": self._sign(timestamp_ms, method, path),
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a signed API request."""
        url = f"{self._base_url}{path}"
        headers = self._headers(method, path)
        response = self._client.request(method, url, headers=headers, json=body)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    def get_markets(
        self,
        status: str = "open",
        limit: int = 200,
        *,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        tickers: list[str] | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch markets from Kalshi with optional filters. Returns API payload."""
        params: list[str] = [f"status={status}", f"limit={limit}"]
        if series_ticker:
            params.append(f"series_ticker={series_ticker}")
        if event_ticker:
            params.append(f"event_ticker={event_ticker}")
        if tickers:
            params.append(f"tickers={','.join(tickers)}")
        if cursor:
            params.append(f"cursor={cursor}")
        query = "&".join(params)
        return self.request("GET", f"/markets?{query}")

    def iter_markets(
        self,
        status: str = "open",
        limit: int = 200,
        max_pages: int = 10,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        """Paginate through Kalshi markets."""
        markets: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(max_pages):
            payload = self.get_markets(status=status, limit=limit, cursor=cursor, **filters)
            batch = payload.get("markets", [])
            markets.extend(batch)
            cursor = payload.get("cursor")
            if not cursor or not batch:
                break
        return markets

    def get_events(
        self,
        status: str = "open",
        limit: int = 200,
        series_ticker: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch events, optionally filtered by series."""
        params: list[str] = [f"status={status}", f"limit={limit}"]
        if series_ticker:
            params.append(f"series_ticker={series_ticker}")
        if cursor:
            params.append(f"cursor={cursor}")
        query = "&".join(params)
        return self.request("GET", f"/events?{query}")

    def get_event(self, event_ticker: str, with_nested_markets: bool = True) -> dict[str, Any]:
        """Fetch one event and optionally include nested markets."""
        nested = "true" if with_nested_markets else "false"
        return self.request("GET", f"/events/{event_ticker}?with_nested_markets={nested}")

    def get_market(self, ticker: str) -> dict[str, Any]:
        """Fetch a single market by ticker."""
        data = self.request("GET", f"/markets/{ticker}")
        return data.get("market", data)

    def get_orderbook(self, ticker: str) -> dict[str, Any]:
        """Fetch orderbook for a market."""
        return self.request("GET", f"/markets/{ticker}/orderbook")

    def create_order_v2(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Place an order via Kalshi V2 endpoint."""
        return self.request("POST", "/portfolio/events/orders", payload)

    def get_orders(self, ticker: str | None = None) -> list[dict[str, Any]]:
        """Fetch resting/recent orders."""
        path = "/portfolio/orders"
        if ticker:
            path += f"?ticker={ticker}"
        data = self.request("GET", path)
        return data.get("orders", [])

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an order by ID."""
        return self.request("DELETE", f"/portfolio/orders/{order_id}")

    def get_positions(self) -> list[dict[str, Any]]:
        """Fetch current market positions."""
        data = self.request("GET", "/portfolio/positions?count_filter=position")
        return data.get("market_positions", [])

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()
