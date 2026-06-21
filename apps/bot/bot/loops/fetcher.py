"""
Fetcher loop — pulls Kalshi and sportsbook prices, writes price_snapshots.

Supports polling mode (default) with tiered per-market intervals.
WebSocket mode delegates to KalshiWebSocketClient when configured.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from bot.clients.kalshi_rest import KalshiRestClient
from bot.clients.odds_api import OddsApiClient
from bot.repositories.db import Repository
from bot.services.odds_math import decimal_to_implied_probability, remove_overround
from bot.services.scheduler import MatchContext, compute_tier, is_due

logger = logging.getLogger(__name__)


class FetcherLoop:
    """Tiered price fetcher for active market mappings."""

    def __init__(
        self,
        repo: Repository,
        kalshi: KalshiRestClient,
        odds: OddsApiClient,
        worker_id: str,
        deployed_version: str,
    ) -> None:
        self._repo = repo
        self._kalshi = kalshi
        self._odds = odds
        self._worker_id = worker_id
        self._deployed_version = deployed_version
        self._last_polled: dict[str, dt.datetime] = {}

    def tick(self) -> None:
        """Run one fetcher cycle across all due mappings."""
        try:
            config = self._repo.get_bot_config()
            if config.get("kalshi_market_data_mode") == "websocket":
                self._repo.write_heartbeat(
                    self._worker_id, "fetcher", "delegated_to_websocket",
                    kalshi_data_mode="websocket", deployed_version=self._deployed_version,
                )
                return

            mappings = self._repo.get_active_mappings()
            now = dt.datetime.now(dt.timezone.utc)

            for mapping in mappings:
                self._fetch_mapping(mapping, config, now)

            self._repo.write_heartbeat(
                self._worker_id, "fetcher", "running",
                kalshi_data_mode="polling",
                metadata={"mappings_checked": len(mappings)},
                deployed_version=self._deployed_version,
            )
        except Exception as exc:
            logger.exception("Fetcher tick failed")
            self._repo.write_heartbeat(
                self._worker_id, "fetcher", "error",
                last_error=str(exc), deployed_version=self._deployed_version,
            )

    def _fetch_mapping(self, mapping: dict[str, Any], config: dict[str, Any], now: dt.datetime) -> None:
        """Fetch prices for a single mapping if due."""
        mapping_id = mapping["id"]
        match_data = mapping.get("matches")
        match_ctx = None
        if match_data:
            match_ctx = MatchContext(
                kickoff_at=dt.datetime.fromisoformat(match_data["kickoff_at"].replace("Z", "+00:00")),
                status=match_data["status"],
            )

        tier = compute_tier(match_ctx, now)
        last = self._last_polled.get(mapping_id)
        if not is_due(last, tier, now):
            return

        kalshi_market = mapping.get("kalshi_markets", {})
        sportsbook = mapping.get("sportsbook_events", {})
        ticker = kalshi_market.get("market_ticker", "")

        kalshi_data = self._fetch_kalshi(ticker)
        odds_data = self._fetch_odds(sportsbook, config)

        fair_prob = None
        if odds_data and odds_data.get("price"):
            fair_prob = decimal_to_implied_probability(float(odds_data["price"]))

        self._repo.insert_price_snapshot({
            "mapping_id": mapping_id,
            "match_id": mapping.get("match_id"),
            "source": "fetcher_polling",
            "kalshi_market_ticker": ticker,
            "kalshi_yes_bid": kalshi_data.get("yes_bid"),
            "kalshi_yes_ask": kalshi_data.get("yes_ask"),
            "kalshi_no_bid": kalshi_data.get("no_bid"),
            "kalshi_no_ask": kalshi_data.get("no_ask"),
            "sportsbook_bookmaker": odds_data.get("bookmaker") if odds_data else None,
            "sportsbook_outcome": odds_data.get("outcome") if odds_data else None,
            "sportsbook_odds_decimal": odds_data.get("price") if odds_data else None,
            "fair_probability": fair_prob,
            "raw": {"kalshi": kalshi_data, "odds": odds_data},
        })

        self._last_polled[mapping_id] = now
        logger.info("Fetched %s tier=%s", ticker, tier.value)

    def _fetch_kalshi(self, ticker: str) -> dict[str, Any]:
        """Fetch Kalshi market prices."""
        if not ticker:
            return {}
        try:
            market = self._kalshi.get_market(ticker)
            return {
                "yes_bid": _price_to_decimal(market.get("yes_bid_dollars") or market.get("yes_bid")),
                "yes_ask": _price_to_decimal(market.get("yes_ask_dollars") or market.get("yes_ask")),
                "no_bid": _price_to_decimal(market.get("no_bid_dollars") or market.get("no_bid")),
                "no_ask": _price_to_decimal(market.get("no_ask_dollars") or market.get("no_ask")),
            }
        except Exception:
            logger.warning("Failed to fetch Kalshi market %s", ticker)
            return {}

    def _fetch_odds(self, sportsbook: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
        """Fetch sportsbook odds for mapped outcome."""
        sport_key = sportsbook.get("sport_key")
        if not sport_key:
            return None
        try:
            regions = config.get("odds_api_regions", ["us", "eu"])
            bookmakers = config.get("sharp_bookmakers", ["pinnacle"])
            odds_events = self._odds.get_odds(sport_key, regions, bookmakers=bookmakers)
            target_event_id = sportsbook.get("odds_api_event_id")
            target_outcome = sportsbook.get("outcome_name")

            for event in odds_events:
                if event.get("id") != target_event_id:
                    continue
                for bookmaker in event.get("bookmakers", []):
                    if bookmakers and bookmaker.get("key") not in bookmakers:
                        continue
                    for market in bookmaker.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == target_outcome:
                                return {
                                    "bookmaker": bookmaker.get("key"),
                                    "outcome": outcome.get("name"),
                                    "price": outcome.get("price"),
                                }
            return None
        except Exception:
            logger.warning("Failed to fetch odds for %s", sport_key)
            return None

    def write_ws_snapshot(self, mapping_id: str, ticker: str, kalshi_data: dict[str, Any]) -> None:
        """Write a price snapshot from WebSocket data."""
        self._repo.insert_price_snapshot({
            "mapping_id": mapping_id,
            "source": "fetcher_websocket",
            "kalshi_market_ticker": ticker,
            "kalshi_yes_bid": kalshi_data.get("yes_bid"),
            "kalshi_yes_ask": kalshi_data.get("yes_ask"),
            "kalshi_no_bid": kalshi_data.get("no_bid"),
            "kalshi_no_ask": kalshi_data.get("no_ask"),
            "raw": {"kalshi_ws": kalshi_data},
        })


def _price_to_decimal(value: Any) -> float | None:
    """Normalize Kalshi price to 0-1 decimal."""
    if value is None:
        return None
    val = float(value)
    if val > 1.0:
        return val / 100.0
    return val
