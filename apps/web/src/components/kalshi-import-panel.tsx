"use client";

/**
 * Queue manual Kalshi market tickers in Supabase, then import via bot script.
 * Dashboard cannot call Kalshi directly (secrets stay on Railway/local bot).
 */
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export function KalshiImportPanel() {
  const [ticker, setTicker] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function queueTicker(e: React.FormEvent) {
    e.preventDefault();
    const value = ticker.trim().toUpperCase();
    if (!value) return;

    setLoading(true);
    setMessage(null);
    const supabase = createClient();

    const { error } = await supabase.from("kalshi_markets").upsert(
      {
        market_ticker: value,
        title: `${value} (pending import)`,
        status: "manual",
        raw: { source: "dashboard_manual", needs_import: true },
      },
      { onConflict: "market_ticker" }
    );

    setLoading(false);
    if (error) {
      setMessage(error.message);
      return;
    }

    setTicker("");
    setMessage(
      `Queued ${value}. Run: python -m bot.scripts.import_kalshi_markets ${value}`
    );
    router.refresh();
  }

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 mb-8">
      <h2 className="font-semibold mb-2">Add Kalshi Market Manually</h2>
      <p className="text-sm text-gray-400 mb-4">
        Paste a market ticker from kalshi.com (shown in the URL or market page).
        Then run the import command locally to fetch full details from Kalshi.
      </p>
      <form onSubmit={queueTicker} className="flex gap-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="KXWORLDCUP-25-ENG"
          className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm uppercase"
        />
        <button
          type="submit"
          disabled={loading || !ticker.trim()}
          className="rounded-lg bg-[var(--accent)] text-black px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Queue
        </button>
      </form>
      {message && <p className="text-sm text-[var(--accent)] mt-3">{message}</p>}
    </section>
  );
}
