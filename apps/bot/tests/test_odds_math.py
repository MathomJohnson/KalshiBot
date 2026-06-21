"""Tests for odds conversion and edge math."""

import pytest

from bot.services.odds_math import (
    compute_edge,
    decimal_to_implied_probability,
    kalshi_cents_to_dollars,
    remove_overround,
)


def test_decimal_to_implied_probability():
    assert decimal_to_implied_probability(2.0) == pytest.approx(0.5)
    assert decimal_to_implied_probability(4.0) == pytest.approx(0.25)


def test_decimal_to_implied_probability_invalid():
    with pytest.raises(ValueError):
        decimal_to_implied_probability(0.5)


def test_remove_overround():
    raw = [0.55, 0.55]  # 110% overround on binary
    fair = remove_overround(raw)
    assert sum(fair) == pytest.approx(1.0)
    assert fair[0] == pytest.approx(0.5)


def test_compute_edge_positive():
    assert compute_edge(0.60, 0.55) == pytest.approx(0.05)


def test_compute_edge_negative():
    assert compute_edge(0.50, 0.55) == pytest.approx(-0.05)


def test_kalshi_cents_to_dollars():
    assert kalshi_cents_to_dollars(55) == pytest.approx(0.55)
