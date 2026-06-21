"""
Strategy loop — reads recent prices, computes edges, writes signals.

Entry when gap exceeds threshold; exit on convergence.
"""

from __future__ import annotations

import logging
from typing import Any

from bot.repositories.db import Repository
from bot.services.odds_math import compute_edge

logger = logging.getLogger(__name__)


class StrategyLoop:
    """Edge detection and signal generation."""

    def __init__(self, repo: Repository, worker_id: str, deployed_version: str) -> None:
        self._repo = repo
        self._worker_id = worker_id
        self._deployed_version = deployed_version

    def tick(self) -> None:
        """Run one strategy cycle across active mappings."""
        try:
            config = self._repo.get_bot_config()
            mappings = self._repo.get_active_mappings()
            entry_threshold = float(config.get("edge_entry_threshold", 0.03))
            exit_threshold = float(config.get("edge_exit_threshold", 0.01))

            signals_created = 0
            for mapping in mappings:
                if self._evaluate_mapping(mapping, entry_threshold, exit_threshold):
                    signals_created += 1

            self._repo.write_heartbeat(
                self._worker_id, "strategy", "running",
                metadata={"mappings_evaluated": len(mappings), "signals_created": signals_created},
                deployed_version=self._deployed_version,
            )
        except Exception as exc:
            logger.exception("Strategy tick failed")
            self._repo.write_heartbeat(
                self._worker_id, "strategy", "error",
                last_error=str(exc), deployed_version=self._deployed_version,
            )

    def _evaluate_mapping(
        self,
        mapping: dict[str, Any],
        entry_threshold: float,
        exit_threshold: float,
    ) -> bool:
        """Evaluate a single mapping for entry/exit signals."""
        snapshots = self._repo.get_recent_snapshots(mapping["id"], limit=5)
        if not snapshots:
            return False

        latest = snapshots[0]
        fair_prob = latest.get("fair_probability")
        yes_ask = latest.get("kalshi_yes_ask")
        yes_bid = latest.get("kalshi_yes_bid")

        if fair_prob is None or yes_ask is None:
            return False

        fair_prob = float(fair_prob)
        yes_ask = float(yes_ask)
        yes_bid = float(yes_bid) if yes_bid else yes_ask

        buy_edge = compute_edge(fair_prob, yes_ask)
        sell_edge = compute_edge(yes_bid, fair_prob)

        action = "hold"
        edge = 0.0
        reason_code = "NO_EDGE"

        if buy_edge >= entry_threshold:
            action = "enter_yes"
            edge = buy_edge
            reason_code = "EDGE_ENTRY_YES"
        elif sell_edge >= entry_threshold:
            action = "enter_no"
            edge = sell_edge
            reason_code = "EDGE_ENTRY_NO"
        elif abs(buy_edge) <= exit_threshold and abs(sell_edge) <= exit_threshold:
            action = "exit"
            edge = min(abs(buy_edge), abs(sell_edge))
            reason_code = "CONVERGENCE_EXIT"

        if action == "hold":
            return False

        self._repo.insert_signal({
            "mapping_id": mapping["id"],
            "match_id": mapping.get("match_id"),
            "action": action,
            "status": "new",
            "edge": edge,
            "fair_probability": fair_prob,
            "kalshi_price": yes_ask if action == "enter_yes" else yes_bid,
            "threshold": entry_threshold if action != "exit" else exit_threshold,
            "reason_code": reason_code,
            "reason_detail": f"fair={fair_prob:.4f} ask={yes_ask:.4f} bid={yes_bid:.4f}",
            "snapshot_ids": [latest["id"]],
        })
        logger.info("Signal %s edge=%.4f for mapping %s", action, edge, mapping["id"])
        return True
