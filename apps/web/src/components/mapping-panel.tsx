"use client";

/**
 * Interactive mapping panel — create and approve Kalshi ↔ sportsbook links.
 */
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { KalshiMarket, MarketMapping, SportsbookEvent } from "@/lib/database.types";
import { useRouter } from "next/navigation";

type MappingWithRelations = MarketMapping & {
  kalshi_markets: KalshiMarket | null;
  sportsbook_events: SportsbookEvent | null;
};

interface Props {
  kalshiMarkets: KalshiMarket[];
  sportsbookEvents: SportsbookEvent[];
  mappings: MappingWithRelations[];
}

export function MappingPanel({ kalshiMarkets, sportsbookEvents, mappings }: Props) {
  const [kalshiId, setKalshiId] = useState("");
  const [sportsbookId, setSportsbookId] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function createMapping() {
    if (!kalshiId || !sportsbookId) return;
    setLoading(true);
    const supabase = createClient();
    await supabase.from("market_mappings").insert({
      kalshi_market_id: kalshiId,
      sportsbook_event_id: sportsbookId,
      status: "pending",
      reason: reason || null,
    });
    setLoading(false);
    router.refresh();
  }

  async function updateStatus(id: string, status: "approved" | "rejected") {
    setLoading(true);
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    await supabase
      .from("market_mappings")
      .update({
        status,
        approved_at: new Date().toISOString(),
        approved_by: user?.id ?? null,
      })
      .eq("id", id);
    setLoading(false);
    router.refresh();
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
        <h2 className="font-semibold mb-4">Create Mapping</h2>
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm mb-1 text-gray-400">Kalshi Market</label>
            <select
              value={kalshiId}
              onChange={(e) => setKalshiId(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm"
            >
              <option value="">Select Kalshi market...</option>
              {kalshiMarkets.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title} ({m.market_ticker})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1 text-gray-400">Sportsbook Outcome</label>
            <select
              value={sportsbookId}
              onChange={(e) => setSportsbookId(e.target.value)}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm"
            >
              <option value="">Select outcome...</option>
              {sportsbookEvents.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.home_team} vs {e.away_team} — {e.outcome_name} ({e.bookmaker})
                </option>
              ))}
            </select>
          </div>
        </div>
        <input
          placeholder="Reason / notes"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm mb-4"
        />
        <button
          onClick={createMapping}
          disabled={loading || !kalshiId || !sportsbookId}
          className="rounded-lg bg-[var(--accent)] text-black px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Create Pending Mapping
        </button>
      </section>

      <section>
        <h2 className="font-semibold mb-4">Existing Mappings</h2>
        {mappings.length === 0 ? (
          <p className="text-gray-400 text-sm">No mappings yet.</p>
        ) : (
          <div className="space-y-3">
            {mappings.map((m) => (
              <div
                key={m.id}
                className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div className="text-sm">
                  <p className="font-medium">{m.kalshi_markets?.title}</p>
                  <p className="text-gray-400">
                    ↔ {m.sportsbook_events?.outcome_name} ({m.sportsbook_events?.bookmaker})
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Status: <span className="capitalize">{m.status}</span>
                    {m.reason && ` — ${m.reason}`}
                  </p>
                </div>
                {m.status === "pending" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => updateStatus(m.id, "approved")}
                      disabled={loading}
                      className="rounded-lg bg-[var(--accent)] text-black px-3 py-1 text-sm"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => updateStatus(m.id, "rejected")}
                      disabled={loading}
                      className="rounded-lg border border-[var(--danger)] text-[var(--danger)] px-3 py-1 text-sm"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
