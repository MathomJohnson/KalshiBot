"""
Executor loop — reads signals, enforces risk, places/cancels orders.

Paper mode simulates fills; live mode calls Kalshi V2 order APIs.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from bot.clients.kalshi_rest import KalshiRestClient
from bot.repositories.db import Repository
from bot.services.risk import run_all_checks

logger = logging.getLogger(__name__)


class ExecutorLoop:
    """Order placement and fill reconciliation."""

    def __init__(
        self,
        repo: Repository,
        kalshi: KalshiRestClient,
        worker_id: str,
        deployed_version: str,
    ) -> None:
        self._repo = repo
        self._kalshi = kalshi
        self._worker_id = worker_id
        self._deployed_version = deployed_version

    def tick(self) -> None:
        """Process all new signals."""
        try:
            config = self._repo.get_bot_config()
            signals = self._repo.get_new_signals()
            processed = 0

            for signal in signals:
                self._process_signal(signal, config)
                processed += 1

            self._repo.write_heartbeat(
                self._worker_id, "executor", "running",
                metadata={"signals_processed": processed},
                deployed_version=self._deployed_version,
            )
        except Exception as exc:
            logger.exception("Executor tick failed")
            self._repo.write_heartbeat(
                self._worker_id, "executor", "error",
                last_error=str(exc), deployed_version=self._deployed_version,
            )

    def _process_signal(self, signal: dict[str, Any], config: dict[str, Any]) -> None:
        """Execute or skip a single signal."""
        self._repo.update_signal_status(signal["id"], "processing")

        open_orders = self._repo.get_open_orders_count()
        risk = run_all_checks(
            config,
            order_quantity=10,
            order_cost=500,
            open_order_count=open_orders,
        )

        if not risk.allowed:
            self._repo.update_signal_status(signal["id"], "skipped")
            logger.info("Signal %s skipped: %s", signal["id"], risk.reason_code)
            return

        mapping = signal.get("market_mappings", {})
        kalshi_market = mapping.get("kalshi_markets", {})
        ticker = kalshi_market.get("market_ticker", "")
        action = signal["action"]
        is_paper = config.get("trading_mode", "paper") == "paper"

        if action == "hold":
            self._repo.update_signal_status(signal["id"], "skipped")
            return

        side = "yes" if action == "enter_yes" else "no"
        order_action = "buy" if action in ("enter_yes", "enter_no") else "sell"
        quantity = min(config.get("max_position_per_market", 100), 10)
        price_cents = int(float(signal.get("kalshi_price", 0.5)) * 100)

        order_row = {
            "signal_id": signal["id"],
            "mapping_id": signal.get("mapping_id"),
            "market_ticker": ticker,
            "side": side,
            "action": order_action,
            "quantity": quantity,
            "price_cents": price_cents,
            "status": "pending",
            "is_paper": is_paper,
            "request_payload": {"ticker": ticker, "side": side, "action": order_action, "count": quantity},
            "response_payload": {},
        }

        order = self._repo.insert_order(order_row)

        if is_paper:
            self._execute_paper(order, price_cents, quantity)
        else:
            self._execute_live(order, ticker, side, order_action, quantity, price_cents)

        self._repo.update_signal_status(signal["id"], "executed")

    def _execute_paper(self, order: dict[str, Any], price_cents: int, quantity: int) -> None:
        """Simulate order fill in paper mode."""
        self._repo.update_order(order["id"], {"status": "filled"})
        self._repo.insert_fill({
            "order_id": order["id"],
            "kalshi_fill_id": f"paper-{uuid.uuid4().hex[:12]}",
            "quantity": quantity,
            "price_cents": price_cents,
            "is_paper": True,
            "raw": {"simulated": True},
        })
        logger.info("Paper fill: %s qty=%d @ %d¢", order["market_ticker"], quantity, price_cents)

    def _execute_live(
        self,
        order: dict[str, Any],
        ticker: str,
        side: str,
        action: str,
        quantity: int,
        price_cents: int,
    ) -> None:
        """Place real order via Kalshi V2 API."""
        try:
            payload = {
                "ticker": ticker,
                "side": side,
                "action": action,
                "count": quantity,
                "type": "limit",
                "yes_price_dollars": f"{price_cents / 100:.4f}" if side == "yes" else None,
                "no_price_dollars": f"{price_cents / 100:.4f}" if side == "no" else None,
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            response = self._kalshi.create_order_v2(payload)
            kalshi_order = response.get("order", response)

            self._repo.update_order(order["id"], {
                "status": "submitted",
                "kalshi_order_id": kalshi_order.get("order_id"),
                "response_payload": response,
            })
            logger.info("Live order submitted: %s", ticker)
        except Exception as exc:
            self._repo.update_order(order["id"], {
                "status": "error",
                "error_message": str(exc),
            })
            logger.error("Live order failed for %s: %s", ticker, exc)
