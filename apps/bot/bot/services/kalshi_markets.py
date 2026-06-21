"""
Shared helpers for normalizing and upserting Kalshi market records.
"""

from __future__ import annotations

from typing import Any

from bot.repositories.db import Repository

# Keywords used when scanning market/event titles during discovery.
SOCCER_KEYWORDS = (
    "world cup",
    "fifa",
    "soccer",
    "football",
    "uefa",
    "premier league",
    "champions league",
    "mls",
    "copa",
    "euro ",
    "euro-",
    "worldcup",
    "la liga",
    "bundesliga",
    "serie a",
    "ligue 1",
)


def matches_keywords(text: str, extra: list[str] | None = None) -> bool:
    """Return True if text contains any configured discovery keyword."""
    haystack = text.lower()
    keywords = list(SOCCER_KEYWORDS) + (extra or [])
    return any(k in haystack for k in keywords)


def market_to_row(market: dict[str, Any]) -> dict[str, Any]:
    """Convert Kalshi API market payload to kalshi_markets table row."""
    return {
        "market_ticker": market["ticker"],
        "event_ticker": market.get("event_ticker"),
        "title": market.get("title", market["ticker"]),
        "subtitle": market.get("subtitle"),
        "status": market.get("status"),
        "close_time": market.get("close_time"),
        "yes_bid": _price(market.get("yes_bid_dollars") or market.get("yes_bid")),
        "yes_ask": _price(market.get("yes_ask_dollars") or market.get("yes_ask")),
        "no_bid": _price(market.get("no_bid_dollars") or market.get("no_bid")),
        "no_ask": _price(market.get("no_ask_dollars") or market.get("no_ask")),
        "raw": market,
    }


def upsert_market(repo: Repository, market: dict[str, Any]) -> None:
    """Upsert one Kalshi market row."""
    repo.upsert_kalshi_market(market_to_row(market))


def _price(value: Any) -> float | None:
    if value is None:
        return None
    val = float(value)
    return val / 100.0 if val > 1.0 else val
