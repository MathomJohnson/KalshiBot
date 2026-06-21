"""
Odds and probability math for edge detection.

Converts decimal odds to implied probabilities and removes overround.
"""

from __future__ import annotations


def decimal_to_implied_probability(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds <= 1.0:
        raise ValueError(f"Invalid decimal odds: {odds}")
    return 1.0 / odds


def remove_overround(probabilities: list[float]) -> list[float]:
    """
    Normalize implied probabilities to sum to 1.0 (fair probabilities).

    Args:
        probabilities: Raw implied probabilities from bookmaker odds.

    Returns:
        Normalized fair probabilities.
    """
    total = sum(probabilities)
    if total <= 0:
        raise ValueError("Probabilities must sum to a positive value")
    return [p / total for p in probabilities]


def compute_edge(fair_prob: float, kalshi_price: float) -> float:
    """
    Compute edge: positive means Kalshi is cheap relative to fair value.

    Args:
        fair_prob: Fair probability from sportsbook (0-1).
        kalshi_price: Kalshi price in dollars (0-1).

    Returns:
        Edge as decimal (e.g. 0.03 = 3% edge).
    """
    return fair_prob - kalshi_price


def kalshi_cents_to_dollars(cents: int | float) -> float:
    """Convert Kalshi cents to dollar probability."""
    return float(cents) / 100.0
