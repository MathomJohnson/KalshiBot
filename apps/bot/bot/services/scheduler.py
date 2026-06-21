"""
Tiered polling scheduler based on match proximity.

Computes per-market polling intervals from match state machine.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import Enum


class PollingTier(str, Enum):
    """Polling frequency tiers."""

    IDLE = "idle"          # >6h to kickoff: 30 min
    WARM = "warm"          # <6h: 5 min
    HOT = "hot"            # <30m: 30 sec
    LIVE = "live"          # in progress: 5 sec
    FINISHED = "finished"  # post-match wind-down: 30 min


TIER_INTERVALS: dict[PollingTier, int] = {
    PollingTier.IDLE: 1800,
    PollingTier.WARM: 300,
    PollingTier.HOT: 30,
    PollingTier.LIVE: 5,
    PollingTier.FINISHED: 1800,
}


@dataclass
class MatchContext:
    """Minimal match info for scheduler decisions."""

    kickoff_at: dt.datetime
    status: str
    live_started_at: dt.datetime | None = None


def compute_tier(match: MatchContext | None, now: dt.datetime | None = None) -> PollingTier:
    """
    Determine polling tier from match status and kickoff time.

    Args:
        match: Match context or None if unmapped.
        now: Current UTC time (defaults to now).

    Returns:
        PollingTier enum value.
    """
    now = now or dt.datetime.now(dt.timezone.utc)

    if match is None:
        return PollingTier.IDLE

    if match.status == "live":
        return PollingTier.LIVE

    if match.status in ("finished", "cancelled"):
        return PollingTier.FINISHED

    kickoff = match.kickoff_at
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=dt.timezone.utc)

    delta = (kickoff - now).total_seconds()

    if delta <= 0:
        return PollingTier.LIVE

    if delta <= 30 * 60:
        return PollingTier.HOT

    if delta <= 6 * 3600:
        return PollingTier.WARM

    return PollingTier.IDLE


def interval_seconds(tier: PollingTier) -> int:
    """Return polling interval in seconds for a tier."""
    return TIER_INTERVALS[tier]


def is_due(last_polled: dt.datetime | None, tier: PollingTier, now: dt.datetime | None = None) -> bool:
    """Check if a market is due for polling based on tier interval."""
    if last_polled is None:
        return True

    now = now or dt.datetime.now(dt.timezone.utc)
    if last_polled.tzinfo is None:
        last_polled = last_polled.replace(tzinfo=dt.timezone.utc)

    elapsed = (now - last_polled).total_seconds()
    return elapsed >= interval_seconds(tier)
