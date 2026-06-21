"""
The Odds API client for sportsbook prices.

API key is passed server-side only (Railway bot).
"""

from __future__ import annotations

from typing import Any

import httpx

from bot.config import Settings


class OddsApiClient:
    """Client for The Odds API v4."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.odds_api_base_url.rstrip("/")
        self._api_key = settings.odds_api_key
        self._client = httpx.Client(timeout=30.0)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make authenticated GET request."""
        query = {"apiKey": self._api_key, **(params or {})}
        response = self._client.get(f"{self._base_url}{path}", params=query)
        response.raise_for_status()
        return response.json()

    def get_sports(self) -> list[dict[str, Any]]:
        """List available sports."""
        return self._get("/sports")

    def get_events(self, sport_key: str) -> list[dict[str, Any]]:
        """List events for a sport (free — no quota)."""
        return self._get(f"/sports/{sport_key}/events")

    def get_odds(
        self,
        sport_key: str,
        regions: list[str],
        markets: str = "h2h",
        bookmakers: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch odds for a sport."""
        params: dict[str, Any] = {
            "regions": ",".join(regions),
            "markets": markets,
            "oddsFormat": "decimal",
        }
        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)
        return self._get(f"/sports/{sport_key}/odds", params)

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()
