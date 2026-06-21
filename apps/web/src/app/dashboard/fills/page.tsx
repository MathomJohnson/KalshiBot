import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";

export default async function FillsPage() {
  const supabase = await createClient();
  const { data: fills } = await supabase
    .from("fills")
    .select("*, orders(market_ticker)")
    .order("filled_at", { ascending: false })
    .limit(100);

  type FillRow = {
    quantity: number;
    price_cents: number;
    is_paper: boolean;
    filled_at: string;
    orders: { market_ticker: string } | null;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Fills</h1>
      <DataTable
        columns={["ticker", "qty", "price", "paper", "filled"]}
        rows={((fills ?? []) as FillRow[]).map((f) => ({
          ticker: f.orders?.market_ticker ?? "—",
          qty: f.quantity.toString(),
          price: `${f.price_cents}¢`,
          paper: f.is_paper ? "Yes" : "No",
          filled: new Date(f.filled_at).toLocaleString(),
        }))}
      />
    </div>
  );
}
