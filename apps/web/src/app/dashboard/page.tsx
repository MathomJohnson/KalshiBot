import { createClient } from "@/lib/supabase/server";

/** Dashboard overview with key stats. */
export default async function DashboardPage() {
  const supabase = await createClient();

  const [
    { count: mappingCount },
    { count: pendingMappings },
    { count: signalCount },
    { count: orderCount },
    { data: config },
    { data: worker },
  ] = await Promise.all([
    supabase.from("market_mappings").select("*", { count: "exact", head: true }).eq("is_active", true),
    supabase.from("market_mappings").select("*", { count: "exact", head: true }).eq("status", "pending"),
    supabase.from("signals").select("*", { count: "exact", head: true }).eq("status", "new"),
    supabase.from("orders").select("*", { count: "exact", head: true }),
    supabase.from("bot_config").select("*").limit(1).single(),
    supabase.from("worker_runs").select("*").order("last_heartbeat_at", { ascending: false }).limit(1).maybeSingle(),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Overview</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Active Mappings" value={mappingCount ?? 0} />
        <StatCard label="Pending Mappings" value={pendingMappings ?? 0} />
        <StatCard label="New Signals" value={signalCount ?? 0} />
        <StatCard label="Total Orders" value={orderCount ?? 0} />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
          <h2 className="font-semibold mb-3">Bot Status</h2>
          {config ? (
            <dl className="space-y-2 text-sm">
              <Row label="Trading Mode" value={config.trading_mode} />
              <Row label="Trading Enabled" value={config.trading_enabled ? "Yes" : "No"} />
              <Row label="Kill Switch" value={config.kill_switch ? "ON" : "OFF"} highlight={config.kill_switch} />
              <Row label="Kalshi Data Mode" value={config.kalshi_market_data_mode} />
              <Row label="Entry Threshold" value={`${(Number(config.edge_entry_threshold) * 100).toFixed(1)}%`} />
            </dl>
          ) : (
            <p className="text-gray-400 text-sm">No config found</p>
          )}
        </section>

        <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
          <h2 className="font-semibold mb-3">Worker Health</h2>
          {worker ? (
            <dl className="space-y-2 text-sm">
              <Row label="Worker ID" value={worker.worker_id} />
              <Row label="Loop" value={worker.loop_name} />
              <Row label="Status" value={worker.status} />
              <Row label="Last Heartbeat" value={new Date(worker.last_heartbeat_at).toLocaleString()} />
              {worker.last_error && (
                <Row label="Last Error" value={worker.last_error} highlight />
              )}
            </dl>
          ) : (
            <p className="text-gray-400 text-sm">No worker heartbeat yet</p>
          )}
        </section>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function Row({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-400">{label}</dt>
      <dd className={highlight ? "text-[var(--warning)]" : ""}>{value}</dd>
    </div>
  );
}
