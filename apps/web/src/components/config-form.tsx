"use client";

/**
 * Bot config form — edit trading parameters, kill switch, and data mode.
 */
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { BotConfig } from "@/lib/database.types";
import { useRouter } from "next/navigation";

export function ConfigForm({ config }: { config: BotConfig }) {
  const [form, setForm] = useState(config);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const supabase = createClient();
    const { error } = await supabase
      .from("bot_config")
      .update({
        max_position_per_market: form.max_position_per_market,
        max_total_exposure: form.max_total_exposure,
        max_open_orders: form.max_open_orders,
        daily_loss_cap_cents: form.daily_loss_cap_cents,
        kill_switch: form.kill_switch,
        trading_enabled: form.trading_enabled,
        trading_mode: form.trading_mode,
        kalshi_market_data_mode: form.kalshi_market_data_mode,
        edge_entry_threshold: form.edge_entry_threshold,
        edge_exit_threshold: form.edge_exit_threshold,
        sharp_bookmakers: form.sharp_bookmakers,
        websocket_fallback_to_polling: form.websocket_fallback_to_polling,
      })
      .eq("id", form.id);

    setSaving(false);
    setMessage(error ? error.message : "Saved successfully");
    router.refresh();
  }

  function updateField<K extends keyof BotConfig>(key: K, value: BotConfig[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <form onSubmit={handleSave} className="max-w-xl space-y-4">
      <Field label="Max Position Per Market">
        <input
          type="number"
          value={form.max_position_per_market}
          onChange={(e) => updateField("max_position_per_market", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Max Total Exposure">
        <input
          type="number"
          value={form.max_total_exposure}
          onChange={(e) => updateField("max_total_exposure", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Max Open Orders">
        <input
          type="number"
          value={form.max_open_orders}
          onChange={(e) => updateField("max_open_orders", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Daily Loss Cap (cents)">
        <input
          type="number"
          value={form.daily_loss_cap_cents}
          onChange={(e) => updateField("daily_loss_cap_cents", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Entry Edge Threshold">
        <input
          type="number"
          step="0.001"
          value={form.edge_entry_threshold}
          onChange={(e) => updateField("edge_entry_threshold", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Exit Edge Threshold">
        <input
          type="number"
          step="0.001"
          value={form.edge_exit_threshold}
          onChange={(e) => updateField("edge_exit_threshold", Number(e.target.value))}
          className="input"
        />
      </Field>
      <Field label="Sharp Bookmakers (comma-separated)">
        <input
          type="text"
          value={form.sharp_bookmakers.join(", ")}
          onChange={(e) =>
            updateField(
              "sharp_bookmakers",
              e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
            )
          }
          className="input"
        />
      </Field>
      <Field label="Trading Mode">
        <select
          value={form.trading_mode}
          onChange={(e) => updateField("trading_mode", e.target.value as BotConfig["trading_mode"])}
          className="input"
        >
          <option value="paper">Paper</option>
          <option value="live">Live</option>
        </select>
      </Field>
      <Field label="Kalshi Data Mode">
        <select
          value={form.kalshi_market_data_mode}
          onChange={(e) =>
            updateField("kalshi_market_data_mode", e.target.value as BotConfig["kalshi_market_data_mode"])
          }
          className="input"
        >
          <option value="polling">Polling</option>
          <option value="websocket">WebSocket</option>
        </select>
      </Field>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.kill_switch}
          onChange={(e) => updateField("kill_switch", e.target.checked)}
        />
        Kill Switch (blocks all orders)
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.trading_enabled}
          onChange={(e) => updateField("trading_enabled", e.target.checked)}
        />
        Trading Enabled
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.websocket_fallback_to_polling}
          onChange={(e) => updateField("websocket_fallback_to_polling", e.target.checked)}
        />
        WebSocket Fallback to Polling
      </label>

      {message && (
        <p className={`text-sm ${message.includes("success") ? "text-[var(--accent)]" : "text-[var(--danger)]"}`}>
          {message}
        </p>
      )}
      <button
        type="submit"
        disabled={saving}
        className="rounded-lg bg-[var(--accent)] text-black px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Configuration"}
      </button>

      <style jsx>{`
        .input {
          width: 100%;
          border-radius: 0.5rem;
          border: 1px solid var(--border);
          background: var(--background);
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
        }
      `}</style>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm mb-1 text-gray-400">{label}</label>
      {children}
    </div>
  );
}
