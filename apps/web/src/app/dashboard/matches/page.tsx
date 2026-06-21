import { createClient } from "@/lib/supabase/server";
import { DataTable } from "@/components/data-table";
import type { Match } from "@/lib/database.types";

export default async function MatchesPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("matches")
    .select("*")
    .order("kickoff_at", { ascending: true });

  const matches = (data ?? []) as Match[];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Matches</h1>
      <DataTable
        columns={["home_team", "away_team", "kickoff_at", "status", "stage"]}
        rows={matches.map((m) => ({
          home_team: m.home_team,
          away_team: m.away_team,
          kickoff_at: new Date(m.kickoff_at).toLocaleString(),
          status: m.status,
          stage: m.stage ?? "—",
        }))}
      />
    </div>
  );
}
