"""
Database repository layer for the bot worker.

Centralizes Supabase reads/writes for all loops.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from supabase import Client


class Repository:
    """Supabase data access for bot loops."""

    def __init__(self, client: Client) -> None:
        self._db = client

    def get_bot_config(self) -> dict[str, Any]:
        """Fetch singleton bot config."""
        result = self._db.table("bot_config").select("*").limit(1).single().execute()
        return result.data

    def get_active_mappings(self) -> list[dict[str, Any]]:
        """Fetch approved active market mappings with related data."""
        result = (
            self._db.table("market_mappings")
            .select("*, kalshi_markets(*), sportsbook_events(*), matches(*)")
            .eq("status", "approved")
            .eq("is_active", True)
            .execute()
        )
        return result.data or []

    def get_matches(self) -> list[dict[str, Any]]:
        """Fetch all matches."""
        result = self._db.table("matches").select("*").execute()
        return result.data or []

    def insert_price_snapshot(self, row: dict[str, Any]) -> dict[str, Any]:
        """Insert a price snapshot row."""
        result = self._db.table("price_snapshots").insert(row).execute()
        return result.data[0] if result.data else {}

    def get_recent_snapshots(self, mapping_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent snapshots for a mapping."""
        result = (
            self._db.table("price_snapshots")
            .select("*")
            .eq("mapping_id", mapping_id)
            .order("captured_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def insert_signal(self, row: dict[str, Any]) -> dict[str, Any]:
        """Insert a strategy signal."""
        result = self._db.table("signals").insert(row).execute()
        return result.data[0] if result.data else {}

    def get_new_signals(self) -> list[dict[str, Any]]:
        """Fetch signals awaiting execution."""
        result = (
            self._db.table("signals")
            .select("*, market_mappings(*, kalshi_markets(*))")
            .eq("status", "new")
            .order("created_at")
            .execute()
        )
        return result.data or []

    def update_signal_status(self, signal_id: str, status: str) -> None:
        """Update signal lifecycle status."""
        self._db.table("signals").update({
            "status": status,
            "processed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }).eq("id", signal_id).execute()

    def insert_order(self, row: dict[str, Any]) -> dict[str, Any]:
        """Insert an order audit row."""
        result = self._db.table("orders").insert(row).execute()
        return result.data[0] if result.data else {}

    def update_order(self, order_id: str, updates: dict[str, Any]) -> None:
        """Update an order row."""
        self._db.table("orders").update(updates).eq("id", order_id).execute()

    def insert_fill(self, row: dict[str, Any]) -> dict[str, Any]:
        """Insert a fill audit row."""
        result = self._db.table("fills").insert(row).execute()
        return result.data[0] if result.data else {}

    def get_open_orders_count(self) -> int:
        """Count resting/submitted orders."""
        result = (
            self._db.table("orders")
            .select("*", count="exact")
            .in_("status", ["pending", "submitted", "resting", "partially_filled"])
            .execute()
        )
        return result.count or 0

    def upsert_kalshi_market(self, row: dict[str, Any]) -> None:
        """Upsert a discovered Kalshi market."""
        self._db.table("kalshi_markets").upsert(row, on_conflict="market_ticker").execute()

    def upsert_sportsbook_event(self, row: dict[str, Any]) -> None:
        """Upsert a discovered sportsbook event/outcome."""
        self._db.table("sportsbook_events").upsert(
            row,
            on_conflict="odds_api_event_id,market_type,outcome_name,bookmaker",
        ).execute()

    def write_heartbeat(
        self,
        worker_id: str,
        loop_name: str,
        status: str = "running",
        kalshi_data_mode: str | None = None,
        last_error: str | None = None,
        metadata: dict[str, Any] | None = None,
        deployed_version: str | None = None,
    ) -> None:
        """Write worker heartbeat for dashboard monitoring."""
        self._db.table("worker_runs").insert({
            "worker_id": worker_id,
            "loop_name": loop_name,
            "status": status,
            "kalshi_data_mode": kalshi_data_mode,
            "last_heartbeat_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "last_error": last_error,
            "metadata": metadata or {},
            "deployed_version": deployed_version,
        }).execute()
