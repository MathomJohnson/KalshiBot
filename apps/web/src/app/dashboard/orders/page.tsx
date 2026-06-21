import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";

export default async function OrdersPage() {
  const supabase = await createClient();
  const { data: orders } = await supabase
    .from("orders")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Orders</h1>
      <DataTable
        columns={["ticker", "side", "action", "qty", "status", "paper", "created"]}
        rows={(orders ?? []).map((o) => ({
          ticker: o.market_ticker,
          side: o.side,
          action: o.action,
          qty: o.quantity.toString(),
          status: o.status,
          paper: o.is_paper ? "Yes" : "No",
          created: new Date(o.created_at).toLocaleString(),
        }))}
      />
    </div>
  );
}
