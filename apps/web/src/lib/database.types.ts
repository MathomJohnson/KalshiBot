/**
 * Database types generated from Supabase schema.
 * Regenerate after migration changes.
 */

export type MatchStatus = "scheduled" | "live" | "finished" | "cancelled";
export type MappingStatus = "pending" | "approved" | "rejected";
export type SignalAction = "enter_yes" | "enter_no" | "exit" | "hold";
export type SignalStatus = "new" | "processing" | "executed" | "skipped" | "expired";
export type OrderStatus =
  | "pending"
  | "submitted"
  | "resting"
  | "filled"
  | "partially_filled"
  | "cancelled"
  | "error";
export type KalshiDataMode = "polling" | "websocket";
export type TradingMode = "paper" | "live";

export interface Profile {
  id: string;
  email: string | null;
  is_allowed: boolean;
  created_at: string;
  updated_at: string;
}

export interface Match {
  id: string;
  home_team: string;
  away_team: string;
  kickoff_at: string;
  status: MatchStatus;
  live_started_at: string | null;
  finished_at: string | null;
  kalshi_event_ticker: string | null;
  odds_api_event_id: string | null;
  stage: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BotConfig {
  id: string;
  max_position_per_market: number;
  max_total_exposure: number;
  max_open_orders: number;
  daily_loss_cap_cents: number;
  kill_switch: boolean;
  trading_enabled: boolean;
  trading_mode: TradingMode;
  kalshi_market_data_mode: KalshiDataMode;
  edge_entry_threshold: number;
  edge_exit_threshold: number;
  sharp_bookmakers: string[];
  odds_api_regions: string[];
  websocket_fallback_to_polling: boolean;
  updated_at: string;
  updated_by: string | null;
}

export interface KalshiMarket {
  id: string;
  market_ticker: string;
  event_ticker: string | null;
  title: string;
  subtitle: string | null;
  status: string | null;
  close_time: string | null;
  yes_bid: number | null;
  yes_ask: number | null;
  no_bid: number | null;
  no_ask: number | null;
  raw: Record<string, unknown>;
  discovered_at: string;
  updated_at: string;
}

export interface SportsbookEvent {
  id: string;
  odds_api_event_id: string;
  sport_key: string;
  home_team: string | null;
  away_team: string | null;
  commence_time: string | null;
  market_type: string;
  outcome_name: string;
  outcome_price: number | null;
  bookmaker: string | null;
  is_outright: boolean;
  raw: Record<string, unknown>;
  discovered_at: string;
  updated_at: string;
}

export interface MarketMapping {
  id: string;
  kalshi_market_id: string;
  sportsbook_event_id: string;
  match_id: string | null;
  status: MappingStatus;
  kalshi_side: string;
  confidence: number | null;
  reason: string | null;
  approved_by: string | null;
  approved_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PriceSnapshot {
  id: string;
  mapping_id: string | null;
  match_id: string | null;
  source: string;
  kalshi_market_ticker: string | null;
  kalshi_yes_bid: number | null;
  kalshi_yes_ask: number | null;
  kalshi_no_bid: number | null;
  kalshi_no_ask: number | null;
  sportsbook_bookmaker: string | null;
  sportsbook_outcome: string | null;
  sportsbook_odds_decimal: number | null;
  fair_probability: number | null;
  captured_at: string;
  raw: Record<string, unknown>;
}

export interface Signal {
  id: string;
  mapping_id: string;
  match_id: string | null;
  action: SignalAction;
  status: SignalStatus;
  edge: number;
  fair_probability: number | null;
  kalshi_price: number | null;
  threshold: number | null;
  reason_code: string;
  reason_detail: string | null;
  snapshot_ids: string[];
  created_at: string;
  processed_at: string | null;
}

export interface Order {
  id: string;
  signal_id: string | null;
  mapping_id: string | null;
  kalshi_order_id: string | null;
  market_ticker: string;
  side: string;
  action: string;
  quantity: number;
  price_cents: number | null;
  status: OrderStatus;
  is_paper: boolean;
  error_message: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Fill {
  id: string;
  order_id: string;
  kalshi_fill_id: string | null;
  quantity: number;
  price_cents: number;
  is_paper: boolean;
  raw: Record<string, unknown>;
  filled_at: string;
}

export interface WorkerRun {
  id: string;
  worker_id: string;
  loop_name: string;
  status: string;
  kalshi_data_mode: KalshiDataMode | null;
  last_heartbeat_at: string;
  last_error: string | null;
  metadata: Record<string, unknown>;
  deployed_version: string | null;
  created_at: string;
}

type TableDef<T> = {
  Row: T;
  Insert: { [K in keyof T]?: T[K] };
  Update: { [K in keyof T]?: T[K] };
  Relationships: [];
};

export interface Database {
  public: {
    Tables: {
      profiles: TableDef<Profile>;
      matches: TableDef<Match>;
      bot_config: TableDef<BotConfig>;
      kalshi_markets: TableDef<KalshiMarket>;
      sportsbook_events: TableDef<SportsbookEvent>;
      market_mappings: TableDef<MarketMapping>;
      price_snapshots: TableDef<PriceSnapshot>;
      signals: TableDef<Signal>;
      orders: TableDef<Order>;
      fills: TableDef<Fill>;
      worker_runs: TableDef<WorkerRun>;
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
}
