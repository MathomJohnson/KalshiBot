-- KalshiBot initial schema: tables, enums, indexes, RLS, seed config
-- Apply via: supabase db push (remote) or supabase start + migration (local)

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE match_status AS ENUM ('scheduled', 'live', 'finished', 'cancelled');
CREATE TYPE mapping_status AS ENUM ('pending', 'approved', 'rejected');
CREATE TYPE signal_action AS ENUM ('enter_yes', 'enter_no', 'exit', 'hold');
CREATE TYPE signal_status AS ENUM ('new', 'processing', 'executed', 'skipped', 'expired');
CREATE TYPE order_status AS ENUM ('pending', 'submitted', 'resting', 'filled', 'partially_filled', 'cancelled', 'error');
CREATE TYPE kalshi_data_mode AS ENUM ('polling', 'websocket');
CREATE TYPE trading_mode AS ENUM ('paper', 'live');

-- ---------------------------------------------------------------------------
-- Profiles (single-user allowlist)
-- ---------------------------------------------------------------------------
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  is_allowed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE profiles IS 'Single-user allowlist; only is_allowed users can access dashboard data via RLS.';

-- ---------------------------------------------------------------------------
-- Matches (World Cup schedule)
-- ---------------------------------------------------------------------------
CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  kickoff_at TIMESTAMPTZ NOT NULL,
  status match_status NOT NULL DEFAULT 'scheduled',
  live_started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  kalshi_event_ticker TEXT,
  odds_api_event_id TEXT,
  stage TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_matches_kickoff ON matches(kickoff_at);
CREATE INDEX idx_matches_status ON matches(status);

-- ---------------------------------------------------------------------------
-- Bot configuration (singleton row)
-- ---------------------------------------------------------------------------
CREATE TABLE bot_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  max_position_per_market INTEGER NOT NULL DEFAULT 100,
  max_total_exposure INTEGER NOT NULL DEFAULT 1000,
  max_open_orders INTEGER NOT NULL DEFAULT 10,
  daily_loss_cap_cents INTEGER NOT NULL DEFAULT 50000,
  kill_switch BOOLEAN NOT NULL DEFAULT true,
  trading_enabled BOOLEAN NOT NULL DEFAULT false,
  trading_mode trading_mode NOT NULL DEFAULT 'paper',
  kalshi_market_data_mode kalshi_data_mode NOT NULL DEFAULT 'polling',
  edge_entry_threshold NUMERIC(6,4) NOT NULL DEFAULT 0.03,
  edge_exit_threshold NUMERIC(6,4) NOT NULL DEFAULT 0.01,
  sharp_bookmakers TEXT[] NOT NULL DEFAULT ARRAY['pinnacle'],
  odds_api_regions TEXT[] NOT NULL DEFAULT ARRAY['us', 'eu'],
  websocket_fallback_to_polling BOOLEAN NOT NULL DEFAULT true,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by UUID REFERENCES auth.users(id)
);

COMMENT ON TABLE bot_config IS 'Singleton trading configuration; dashboard edits, bot reads.';

-- ---------------------------------------------------------------------------
-- Discovery tables
-- ---------------------------------------------------------------------------
CREATE TABLE kalshi_markets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  market_ticker TEXT NOT NULL UNIQUE,
  event_ticker TEXT,
  title TEXT NOT NULL,
  subtitle TEXT,
  status TEXT,
  close_time TIMESTAMPTZ,
  yes_bid NUMERIC(6,4),
  yes_ask NUMERIC(6,4),
  no_bid NUMERIC(6,4),
  no_ask NUMERIC(6,4),
  raw JSONB NOT NULL DEFAULT '{}',
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_kalshi_markets_event ON kalshi_markets(event_ticker);

CREATE TABLE sportsbook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  odds_api_event_id TEXT NOT NULL,
  sport_key TEXT NOT NULL,
  home_team TEXT,
  away_team TEXT,
  commence_time TIMESTAMPTZ,
  market_type TEXT NOT NULL DEFAULT 'h2h',
  outcome_name TEXT NOT NULL,
  outcome_price NUMERIC(10,4),
  bookmaker TEXT,
  is_outright BOOLEAN NOT NULL DEFAULT false,
  raw JSONB NOT NULL DEFAULT '{}',
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (odds_api_event_id, market_type, outcome_name, bookmaker)
);

CREATE INDEX idx_sportsbook_events_commence ON sportsbook_events(commence_time);
CREATE INDEX idx_sportsbook_events_sport ON sportsbook_events(sport_key);

-- ---------------------------------------------------------------------------
-- Market mappings (manual review)
-- ---------------------------------------------------------------------------
CREATE TABLE market_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kalshi_market_id UUID NOT NULL REFERENCES kalshi_markets(id) ON DELETE CASCADE,
  sportsbook_event_id UUID NOT NULL REFERENCES sportsbook_events(id) ON DELETE CASCADE,
  match_id UUID REFERENCES matches(id) ON DELETE SET NULL,
  status mapping_status NOT NULL DEFAULT 'pending',
  kalshi_side TEXT NOT NULL DEFAULT 'yes',
  confidence NUMERIC(4,3),
  reason TEXT,
  approved_by UUID REFERENCES auth.users(id),
  approved_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (kalshi_market_id, sportsbook_event_id)
);

CREATE INDEX idx_market_mappings_status ON market_mappings(status) WHERE is_active = true;

-- ---------------------------------------------------------------------------
-- Price snapshots
-- ---------------------------------------------------------------------------
CREATE TABLE price_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mapping_id UUID REFERENCES market_mappings(id) ON DELETE SET NULL,
  match_id UUID REFERENCES matches(id) ON DELETE SET NULL,
  source TEXT NOT NULL,
  kalshi_market_ticker TEXT,
  kalshi_yes_bid NUMERIC(6,4),
  kalshi_yes_ask NUMERIC(6,4),
  kalshi_no_bid NUMERIC(6,4),
  kalshi_no_ask NUMERIC(6,4),
  sportsbook_bookmaker TEXT,
  sportsbook_outcome TEXT,
  sportsbook_odds_decimal NUMERIC(10,4),
  fair_probability NUMERIC(6,4),
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_price_snapshots_mapping_time ON price_snapshots(mapping_id, captured_at DESC);
CREATE INDEX idx_price_snapshots_captured ON price_snapshots(captured_at DESC);

-- ---------------------------------------------------------------------------
-- Signals
-- ---------------------------------------------------------------------------
CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mapping_id UUID NOT NULL REFERENCES market_mappings(id) ON DELETE CASCADE,
  match_id UUID REFERENCES matches(id) ON DELETE SET NULL,
  action signal_action NOT NULL,
  status signal_status NOT NULL DEFAULT 'new',
  edge NUMERIC(6,4) NOT NULL,
  fair_probability NUMERIC(6,4),
  kalshi_price NUMERIC(6,4),
  threshold NUMERIC(6,4),
  reason_code TEXT NOT NULL,
  reason_detail TEXT,
  snapshot_ids UUID[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX idx_signals_status ON signals(status) WHERE status IN ('new', 'processing');
CREATE INDEX idx_signals_mapping ON signals(mapping_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Orders and fills (audit trail)
-- ---------------------------------------------------------------------------
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
  mapping_id UUID REFERENCES market_mappings(id) ON DELETE SET NULL,
  kalshi_order_id TEXT,
  market_ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  action TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  price_cents INTEGER,
  status order_status NOT NULL DEFAULT 'pending',
  is_paper BOOLEAN NOT NULL DEFAULT true,
  error_message TEXT,
  request_payload JSONB NOT NULL DEFAULT '{}',
  response_payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_ticker ON orders(market_ticker);

CREATE TABLE fills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  kalshi_fill_id TEXT,
  quantity INTEGER NOT NULL,
  price_cents INTEGER NOT NULL,
  is_paper BOOLEAN NOT NULL DEFAULT true,
  raw JSONB NOT NULL DEFAULT '{}',
  filled_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fills_order ON fills(order_id);

-- ---------------------------------------------------------------------------
-- Worker health
-- ---------------------------------------------------------------------------
CREATE TABLE worker_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id TEXT NOT NULL,
  loop_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  kalshi_data_mode kalshi_data_mode,
  last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_error TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  deployed_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_worker_runs_heartbeat ON worker_runs(worker_id, loop_name, last_heartbeat_at DESC);

-- ---------------------------------------------------------------------------
-- Helper: check if current user is allowlisted
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_allowed_user()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM profiles
    WHERE id = auth.uid() AND is_allowed = true
  );
$$;

-- ---------------------------------------------------------------------------
-- Auto-create profile on signup (disabled signup; manual user creation)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, is_allowed)
  VALUES (NEW.id, NEW.email, false);
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE kalshi_markets ENABLE ROW LEVEL SECURITY;
ALTER TABLE sportsbook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE fills ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_runs ENABLE ROW LEVEL SECURITY;

-- Profiles: user can read/update own profile
CREATE POLICY "profiles_select_own" ON profiles FOR SELECT TO authenticated
  USING (id = auth.uid() AND is_allowed_user());
CREATE POLICY "profiles_update_own" ON profiles FOR UPDATE TO authenticated
  USING (id = auth.uid() AND is_allowed_user());

-- Generic allowlisted read/write for dashboard tables
CREATE POLICY "matches_all" ON matches FOR ALL TO authenticated
  USING (is_allowed_user()) WITH CHECK (is_allowed_user());

CREATE POLICY "bot_config_all" ON bot_config FOR ALL TO authenticated
  USING (is_allowed_user()) WITH CHECK (is_allowed_user());

CREATE POLICY "kalshi_markets_all" ON kalshi_markets FOR ALL TO authenticated
  USING (is_allowed_user()) WITH CHECK (is_allowed_user());

CREATE POLICY "sportsbook_events_all" ON sportsbook_events FOR ALL TO authenticated
  USING (is_allowed_user()) WITH CHECK (is_allowed_user());

CREATE POLICY "market_mappings_all" ON market_mappings FOR ALL TO authenticated
  USING (is_allowed_user()) WITH CHECK (is_allowed_user());

CREATE POLICY "price_snapshots_select" ON price_snapshots FOR SELECT TO authenticated
  USING (is_allowed_user());
CREATE POLICY "price_snapshots_insert" ON price_snapshots FOR INSERT TO authenticated
  WITH CHECK (is_allowed_user());

CREATE POLICY "signals_select" ON signals FOR SELECT TO authenticated
  USING (is_allowed_user());

CREATE POLICY "orders_select" ON orders FOR SELECT TO authenticated
  USING (is_allowed_user());

CREATE POLICY "fills_select" ON fills FOR SELECT TO authenticated
  USING (is_allowed_user());

CREATE POLICY "worker_runs_select" ON worker_runs FOR SELECT TO authenticated
  USING (is_allowed_user());

-- ---------------------------------------------------------------------------
-- Seed default bot config
-- ---------------------------------------------------------------------------
INSERT INTO bot_config (
  max_position_per_market,
  max_total_exposure,
  kill_switch,
  trading_enabled,
  trading_mode,
  kalshi_market_data_mode
) VALUES (100, 1000, true, false, 'paper', 'polling');

-- ---------------------------------------------------------------------------
-- Updated_at trigger helper
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER matches_updated_at BEFORE UPDATE ON matches
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER bot_config_updated_at BEFORE UPDATE ON bot_config
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER kalshi_markets_updated_at BEFORE UPDATE ON kalshi_markets
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER sportsbook_events_updated_at BEFORE UPDATE ON sportsbook_events
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER market_mappings_updated_at BEFORE UPDATE ON market_mappings
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER orders_updated_at BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
