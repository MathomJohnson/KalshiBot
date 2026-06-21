"""Tests for tiered polling scheduler."""

import datetime as dt

from bot.services.scheduler import (
    MatchContext,
    PollingTier,
    compute_tier,
    interval_seconds,
    is_due,
)


def _now():
    return dt.datetime(2026, 6, 20, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_idle_tier_far_from_kickoff():
    match = MatchContext(
        kickoff_at=_now() + dt.timedelta(hours=10),
        status="scheduled",
    )
    assert compute_tier(match, _now()) == PollingTier.IDLE
    assert interval_seconds(PollingTier.IDLE) == 1800


def test_warm_tier_within_6h():
    match = MatchContext(
        kickoff_at=_now() + dt.timedelta(hours=3),
        status="scheduled",
    )
    assert compute_tier(match, _now()) == PollingTier.WARM
    assert interval_seconds(PollingTier.WARM) == 300


def test_hot_tier_within_30m():
    match = MatchContext(
        kickoff_at=_now() + dt.timedelta(minutes=15),
        status="scheduled",
    )
    assert compute_tier(match, _now()) == PollingTier.HOT
    assert interval_seconds(PollingTier.HOT) == 30


def test_live_tier():
    match = MatchContext(
        kickoff_at=_now() - dt.timedelta(minutes=30),
        status="live",
    )
    assert compute_tier(match, _now()) == PollingTier.LIVE
    assert interval_seconds(PollingTier.LIVE) == 5


def test_finished_tier():
    match = MatchContext(
        kickoff_at=_now() - dt.timedelta(hours=2),
        status="finished",
    )
    assert compute_tier(match, _now()) == PollingTier.FINISHED


def test_is_due_never_polled():
    assert is_due(None, PollingTier.IDLE, _now()) is True


def test_is_due_recently_polled():
    last = _now() - dt.timedelta(seconds=60)
    assert is_due(last, PollingTier.IDLE, _now()) is False
