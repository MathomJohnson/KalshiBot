"""Tests for risk management checks."""

from bot.services.risk import (
    check_daily_loss,
    check_open_orders,
    check_position_limit,
    check_total_exposure,
    check_trading_allowed,
    run_all_checks,
)


def _config(**overrides):
    base = {
        "kill_switch": False,
        "trading_enabled": True,
        "max_position_per_market": 100,
        "max_total_exposure": 1000,
        "max_open_orders": 10,
        "daily_loss_cap_cents": 50000,
    }
    base.update(overrides)
    return base


def test_kill_switch_blocks():
    result = check_trading_allowed(_config(kill_switch=True))
    assert not result.allowed
    assert result.reason_code == "KILL_SWITCH"


def test_trading_disabled_blocks():
    result = check_trading_allowed(_config(trading_enabled=False))
    assert not result.allowed


def test_position_limit():
    result = check_position_limit(_config(), current_position=95, order_quantity=10)
    assert not result.allowed
    assert result.reason_code == "MAX_POSITION"


def test_exposure_limit():
    result = check_total_exposure(_config(), current_exposure=950, order_cost=100)
    assert not result.allowed


def test_open_orders_limit():
    result = check_open_orders(_config(), open_order_count=10)
    assert not result.allowed


def test_daily_loss_cap():
    result = check_daily_loss(_config(), daily_pnl_cents=-60000)
    assert not result.allowed


def test_all_checks_pass():
    result = run_all_checks(
        _config(),
        current_position=0,
        order_quantity=10,
        current_exposure=0,
        order_cost=100,
        open_order_count=0,
        daily_pnl_cents=0,
    )
    assert result.allowed
