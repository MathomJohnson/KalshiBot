"""
Discovery script — populates kalshi_markets and sportsbook_events.

Usage:
  python -m bot.scripts.discover_markets
  python -m bot.scripts.discover_markets --kalshi-all-open   # import all open markets (debug)
  python -m bot.scripts.discover_markets --series KXSOCCER   # filter by series ticker

Manual import (preferred when auto-discovery misses markets):
  python -m bot.scripts.import_kalshi_markets MARKET-TICKER-1 MARKET-TICKER-2
  python -m bot.scripts.import_kalshi_markets --event EVENT-TICKER
  python -m bot.scripts.import_kalshi_markets --file kalshi_markets.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from bot.clients.kalshi_rest import KalshiRestClient
from bot.clients.odds_api import OddsApiClient
from bot.clients.supabase_client import create_supabase_client
from bot.config import get_settings
from bot.repositories.db import Repository
from bot.services.kalshi_markets import matches_keywords, upsert_market

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

WORLD_CUP_SPORTS = [
    "soccer_fifa_world_cup",
    "soccer_fifa_world_cup_winner",
]


def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def discover_kalshi(
    repo: Repository,
    kalshi: KalshiRestClient,
    *,
    import_all_open: bool = False,
    series_filters: list[str] | None = None,
) -> int:
    """
    Discover Kalshi markets using multiple strategies:
    1. Explicit series/event tickers from env or CLI
    2. Keyword scan across open events + markets
    3. Optional import-all-open debug mode
    """
    seen: set[str] = set()
    count = 0

    def add_market(market: dict) -> None:
        nonlocal count
        ticker = market.get("ticker")
        if not ticker or ticker in seen:
            return
        seen.add(ticker)
        upsert_market(repo, market)
        count += 1

    # Strategy 1: explicit series tickers
    for series in (series_filters or []) + _csv_env("KALSHI_SERIES_TICKERS"):
        logger.info("Fetching markets for series %s", series)
        for market in kalshi.iter_markets(series_ticker=series, max_pages=5):
            add_market(market)

    # Strategy 2: explicit event tickers
    for event_ticker in _csv_env("KALSHI_EVENT_TICKERS"):
        logger.info("Fetching event %s", event_ticker)
        try:
            payload = kalshi.get_event(event_ticker, with_nested_markets=True)
            event = payload.get("event", payload)
            for market in payload.get("markets") or event.get("markets") or []:
                add_market(market)
        except Exception as exc:
            logger.warning("Failed to fetch event %s: %s", event_ticker, exc)

    # Strategy 3: keyword scan on open events, then their markets
    cursor = None
    for _ in range(5):
        payload = kalshi.get_events(status="open", limit=200, cursor=cursor)
        for event in payload.get("events", []):
            title = event.get("title") or ""
            ticker = event.get("event_ticker") or ""
            category = event.get("category") or ""
            blob = f"{title} {ticker} {category}"
            if import_all_open or matches_keywords(blob):
                try:
                    detail = kalshi.get_event(ticker, with_nested_markets=True)
                    for market in detail.get("markets") or []:
                        add_market(market)
                except Exception as exc:
                    logger.debug("Event detail failed for %s: %s", ticker, exc)
        cursor = payload.get("cursor")
        if not cursor:
            break

    # Strategy 4: keyword scan on open markets directly
    markets = kalshi.iter_markets(max_pages=10 if import_all_open else 5)
    sample_titles: list[str] = []
    for market in markets:
        title = market.get("title") or ""
        subtitle = market.get("subtitle") or ""
        event_ticker = market.get("event_ticker") or ""
        blob = f"{title} {subtitle} {event_ticker}"
        if import_all_open or matches_keywords(blob):
            add_market(market)
        elif len(sample_titles) < 5:
            sample_titles.append(title)

    if count == 0:
        logger.warning(
            "No Kalshi markets matched. Demo API often has zero World Cup markets. "
            "Try production URL or manual import: python -m bot.scripts.import_kalshi_markets TICKER"
        )
        if sample_titles:
            logger.info("Sample open market titles on this API: %s", sample_titles)

    logger.info("Discovered %d Kalshi markets", count)
    return count


def discover_odds(repo: Repository, odds: OddsApiClient) -> int:
    """Discover World Cup sportsbook events and outcomes."""
    count = 0
    for sport_key in WORLD_CUP_SPORTS:
        is_outright = "winner" in sport_key
        market_type = "outrights" if is_outright else "h2h"

        try:
            events = odds.get_odds(sport_key, regions=["us", "eu"], markets=market_type)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", sport_key, exc)
            continue

        for event in events:
            event_id = event.get("id", "")
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        repo.upsert_sportsbook_event({
                            "odds_api_event_id": event_id,
                            "sport_key": sport_key,
                            "home_team": event.get("home_team"),
                            "away_team": event.get("away_team"),
                            "commence_time": event.get("commence_time"),
                            "market_type": market.get("key", market_type),
                            "outcome_name": outcome.get("name", ""),
                            "outcome_price": outcome.get("price"),
                            "bookmaker": bookmaker.get("key"),
                            "is_outright": is_outright,
                            "raw": {"event": event, "outcome": outcome},
                        })
                        count += 1

    logger.info("Discovered %d sportsbook outcomes", count)
    return count


def main() -> int:
    """Run discovery for Kalshi and Odds API."""
    parser = argparse.ArgumentParser(description="Discover Kalshi and sportsbook markets")
    parser.add_argument("--kalshi-all-open", action="store_true", help="Import all open Kalshi markets")
    parser.add_argument("--series", action="append", default=[], help="Kalshi series ticker filter")
    parser.add_argument("--odds-only", action="store_true", help="Skip Kalshi discovery")
    parser.add_argument("--kalshi-only", action="store_true", help="Skip Odds API discovery")
    args = parser.parse_args()

    settings = get_settings()
    supabase = create_supabase_client(settings)
    repo = Repository(supabase)

    kalshi = KalshiRestClient(settings)
    odds = OddsApiClient(settings)

    try:
        k_count = 0
        o_count = 0
        if not args.odds_only:
            k_count = discover_kalshi(
                repo,
                kalshi,
                import_all_open=args.kalshi_all_open,
                series_filters=args.series,
            )
        if not args.kalshi_only:
            o_count = discover_odds(repo, odds)
        logger.info("Discovery complete: %d Kalshi, %d sportsbook", k_count, o_count)
        return 0
    finally:
        kalshi.close()
        odds.close()


if __name__ == "__main__":
    sys.exit(main())
