import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";

export default async function SnapshotsPage() {
  const supabase = await createClient();
  const { data: snapshots } = await supabase
    .from("price_snapshots")
    .select("*")
    .order("captured_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Price Snapshots</h1>
      <DataTable
        columns={["source", "ticker", "yes_bid", "yes_ask", "fair_prob", "captured"]}
        rows={(snapshots ?? []).map((s) => ({
          source: s.source,
          ticker: s.kalshi_market_ticker ?? "—",
          yes_bid: s.kalshi_yes_bid?.toString() ?? "—",
          yes_ask: s.kalshi_yes_ask?.toString() ?? "—",
          fair_prob: s.fair_probability?.toString() ?? "—",
          captured: new Date(s.captured_at).toLocaleString(),
        }))}
      />
    </div>
  );
}
