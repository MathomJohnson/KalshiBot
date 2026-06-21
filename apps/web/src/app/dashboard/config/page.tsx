import { createClient } from "@/lib/supabase/server";
import { ConfigForm } from "@/components/config-form";

/** Bot configuration editor. */
export default async function ConfigPage() {
  const supabase = await createClient();
  const { data: config } = await supabase.from("bot_config").select("*").limit(1).single();

  if (!config) {
    return <p className="text-gray-400">No bot config found. Run migrations.</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Bot Configuration</h1>
      <p className="text-gray-400 text-sm mb-6">
        Changes take effect on the bot&apos;s next config read cycle.
      </p>
      <ConfigForm config={config} />
    </div>
  );
}
