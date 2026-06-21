import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";

export default async function WorkerPage() {
  const supabase = await createClient();
  const { data: runs } = await supabase
    .from("worker_runs")
    .select("*")
    .order("last_heartbeat_at", { ascending: false })
    .limit(50);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Worker Health</h1>
      <DataTable
        columns={["worker", "loop", "status", "mode", "heartbeat", "error"]}
        rows={(runs ?? []).map((r) => ({
          worker: r.worker_id,
          loop: r.loop_name,
          status: r.status,
          mode: r.kalshi_data_mode ?? "—",
          heartbeat: new Date(r.last_heartbeat_at).toLocaleString(),
          error: r.last_error ?? "—",
        }))}
      />
    </div>
  );
}
