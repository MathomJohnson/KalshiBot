import { createClient } from "@/lib/supabase/server";
import { MappingPanel } from "@/components/mapping-panel";
import { KalshiImportPanel } from "@/components/kalshi-import-panel";

/** Market mapping UI — link Kalshi markets to sportsbook outcomes. */
export default async function MappingsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const params = await searchParams;
  const statusFilter = params.status ?? "pending";

  const supabase = await createClient();

  const { data: unmappedKalshi } = await supabase
    .from("kalshi_markets")
    .select("*")
    .order("title")
    .limit(100);

  const { data: sportsbookEvents } = await supabase
    .from("sportsbook_events")
    .select("*")
    .order("commence_time", { ascending: true })
    .limit(200);

  let mappingsQuery = supabase
    .from("market_mappings")
    .select("*, kalshi_markets(*), sportsbook_events(*)")
    .eq("is_active", true)
    .order("created_at", { ascending: false });

  if (statusFilter !== "all") {
    mappingsQuery = mappingsQuery.eq("status", statusFilter);
  }

  const { data: mappings } = await mappingsQuery.limit(50);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Market Mappings</h1>
      <p className="text-gray-400 text-sm mb-6">
        Link Kalshi markets to sportsbook outcomes. Run discovery script first.
      </p>

      <div className="flex gap-2 mb-6">
        {["pending", "approved", "rejected", "all"].map((s) => (
          <a
            key={s}
            href={`/dashboard/mappings?status=${s}`}
            className={`px-3 py-1 rounded-lg text-sm border ${
              statusFilter === s
                ? "border-[var(--accent)] text-[var(--accent)]"
                : "border-[var(--border)] text-gray-400"
            }`}
          >
            {s}
          </a>
        ))}
      </div>

      <KalshiImportPanel />

      <MappingPanel
        kalshiMarkets={unmappedKalshi ?? []}
        sportsbookEvents={sportsbookEvents ?? []}
        mappings={mappings ?? []}
      />
    </div>
  );
}
