"""
Manually import Kalshi markets by ticker, event, or file.

The Kalshi demo API often has no World Cup markets. Production may use
different tickers than keyword search finds. Paste tickers from the Kalshi
website URL or market page.

Usage:
  python -m bot.scripts.import_kalshi_markets KXWORLDCUP-25-ENG
  python -m bot.scripts.import_kalshi_markets --event KXWORLDCUP-25-ENG
  python -m bot.scripts.import_kalshi_markets --file kalshi_markets.txt

File format (kalshi_markets.txt):
  # comments and blank lines ignored
  KXWORLDCUP-25-ENG
  KXWORLDCUP-25-FRA
  --event KXWORLDCUP-25-ENG
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from bot.clients.kalshi_rest import KalshiRestClient
from bot.clients.supabase_client import create_supabase_client
from bot.config import get_settings
from bot.repositories.db import Repository
from bot.services.kalshi_markets import upsert_market

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]+$")


def parse_file(path: Path) -> tuple[list[str], list[str]]:
    """Parse tickers and --event lines from a text file."""
    tickers: list[str] = []
    events: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--event "):
            events.append(line.replace("--event ", "", 1).strip())
        else:
            tickers.append(line)
    return tickers, events


def import_market_ticker(repo: Repository, kalshi: KalshiRestClient, ticker: str) -> bool:
    """Fetch and upsert one market ticker."""
    try:
        market = kalshi.get_market(ticker)
        upsert_market(repo, market)
        logger.info("Imported market %s — %s", ticker, market.get("title", ticker))
        return True
    except Exception as exc:
        logger.error("Failed to import market %s: %s", ticker, exc)
        return False


def import_event(repo: Repository, kalshi: KalshiRestClient, event_ticker: str) -> int:
    """Fetch and upsert all markets under an event ticker."""
    count = 0
    try:
        payload = kalshi.get_event(event_ticker, with_nested_markets=True)
        markets = payload.get("markets") or []
        if not markets:
            logger.warning("No markets found for event %s", event_ticker)
            return 0
        for market in markets:
            upsert_market(repo, market)
            count += 1
            logger.info("Imported %s — %s", market.get("ticker"), market.get("title"))
    except Exception as exc:
        logger.error("Failed to import event %s: %s", event_ticker, exc)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Manually import Kalshi markets")
    parser.add_argument("tickers", nargs="*", help="Market tickers to import")
    parser.add_argument("--event", action="append", default=[], help="Event ticker(s) to import")
    parser.add_argument("--file", type=Path, help="Text file with tickers / --event lines")
    args = parser.parse_args()

    tickers = list(args.tickers)
    events = list(args.event)
    if args.file:
        file_tickers, file_events = parse_file(args.file)
        tickers.extend(file_tickers)
        events.extend(file_events)

    if not tickers and not events:
        parser.error("Provide tickers, --event, or --file")

    settings = get_settings()
    repo = Repository(create_supabase_client(settings))
    kalshi = KalshiRestClient(settings)

    ok = 0
    fail = 0
    try:
        for ticker in tickers:
            if not TICKER_RE.match(ticker):
                logger.warning("Skipping invalid ticker format: %s", ticker)
                fail += 1
                continue
            if import_market_ticker(repo, kalshi, ticker):
                ok += 1
            else:
                fail += 1

        for event_ticker in events:
            ok += import_event(repo, kalshi, event_ticker)
    finally:
        kalshi.close()

    logger.info("Import finished: %d succeeded, %d failed", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
