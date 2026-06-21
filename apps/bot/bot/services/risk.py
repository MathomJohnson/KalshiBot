"""
Risk management checks before order placement.

Enforces kill switch, exposure limits, and open order caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskCheckResult:
    """Result of a risk check."""

    allowed: bool
    reason_code: str
    detail: str | None = None


def check_trading_allowed(config: dict[str, Any]) -> RiskCheckResult:
    """Verify bot config allows trading."""
    if config.get("kill_switch"):
        return RiskCheckResult(False, "KILL_SWITCH", "Kill switch is active")
    if not config.get("trading_enabled"):
        return RiskCheckResult(False, "TRADING_DISABLED", "Trading is disabled")
    return RiskCheckResult(True, "OK")


def check_position_limit(
    config: dict[str, Any],
    current_position: int,
    order_quantity: int,
) -> RiskCheckResult:
    """Verify order won't exceed per-market position limit."""
    max_pos = config.get("max_position_per_market", 100)
    if current_position + order_quantity > max_pos:
        return RiskCheckResult(
            False,
            "MAX_POSITION",
            f"Would exceed max position {max_pos} (current={current_position}, order={order_quantity})",
        )
    return RiskCheckResult(True, "OK")


def check_total_exposure(
    config: dict[str, Any],
    current_exposure: int,
    order_cost: int,
) -> RiskCheckResult:
    """Verify order won't exceed total exposure cap."""
    max_exp = config.get("max_total_exposure", 1000)
    if current_exposure + order_cost > max_exp:
        return RiskCheckResult(
            False,
            "MAX_EXPOSURE",
            f"Would exceed max exposure {max_exp}",
        )
    return RiskCheckResult(True, "OK")


def check_open_orders(
    config: dict[str, Any],
    open_order_count: int,
) -> RiskCheckResult:
    """Verify open order count is within limit."""
    max_open = config.get("max_open_orders", 10)
    if open_order_count >= max_open:
        return RiskCheckResult(False, "MAX_OPEN_ORDERS", f"At max open orders ({max_open})")
    return RiskCheckResult(True, "OK")


def check_daily_loss(
    config: dict[str, Any],
    daily_pnl_cents: int,
) -> RiskCheckResult:
    """Verify daily loss hasn't exceeded cap."""
    cap = config.get("daily_loss_cap_cents", 50000)
    if daily_pnl_cents < -cap:
        return RiskCheckResult(False, "DAILY_LOSS_CAP", f"Daily loss cap reached ({cap} cents)")
    return RiskCheckResult(True, "OK")


def run_all_checks(
    config: dict[str, Any],
    *,
    current_position: int = 0,
    order_quantity: int = 0,
    current_exposure: int = 0,
    order_cost: int = 0,
    open_order_count: int = 0,
    daily_pnl_cents: int = 0,
) -> RiskCheckResult:
    """Run all risk checks in sequence; return first failure."""
    checks = [
        check_trading_allowed(config),
        check_position_limit(config, current_position, order_quantity),
        check_total_exposure(config, current_exposure, order_cost),
        check_open_orders(config, open_order_count),
        check_daily_loss(config, daily_pnl_cents),
    ]
    for result in checks:
        if not result.allowed:
            return result
    return RiskCheckResult(True, "OK")
