import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";

export default async function SignalsPage() {
  const supabase = await createClient();
  const { data: signals } = await supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Signals</h1>
      <DataTable
        columns={["action", "status", "edge", "reason", "created"]}
        rows={(signals ?? []).map((s) => ({
          action: s.action,
          status: s.status,
          edge: `${(Number(s.edge) * 100).toFixed(2)}%`,
          reason: s.reason_code,
          created: new Date(s.created_at).toLocaleString(),
        }))}
      />
    </div>
  );
}
