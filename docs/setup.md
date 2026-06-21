# Setup Guide

## Rollout Phases

KalshiBot is deployed in three phases. **Start in Phase 1** unless you have already completed prior exit criteria.

| Phase | When | Key env change |
|-------|------|----------------|
| [Phase 1 — Demo + paper](rollout-phases.md#phase-1-demo-api--plumbing-current-default) | Now (plumbing) | `KALSHI_BASE_URL` = demo |
| [Phase 2 — Production + paper](rollout-phases.md#phase-2-production-api--paper-mode) | After Phase 1 exit criteria | `KALSHI_BASE_URL` = production |
| [Phase 3 — Production + live](rollout-phases.md#phase-3-production-api--live-trading) | After paper soak | `bot_config.trading_mode` = live |

Full checklists and exit criteria: **[rollout-phases.md](rollout-phases.md)**

### Phase 1 → Phase 2 env switch

In `apps/bot/.env` (and Railway variables):

```env
# Before (Phase 1)
KALSHI_BASE_URL=https://demo-api.kalshi.co/trade-api/v2
KALSHI_WS_URL=wss://demo-api.kalshi.co/trade-api/ws/v2

# After (Phase 2)
KALSHI_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
KALSHI_WS_URL=wss://api.elections.kalshi.com/trade-api/ws/v2
```

Redeploy Railway, rerun discovery, remap/import World Cup markets.

### Phase 2 → Phase 3 config switch

In dashboard `/dashboard/config` (not env vars):

- `trading_mode` → **live**
- `trading_enabled` → **true**
- `kill_switch` → **false** only when ready

See [rollout-phases.md](rollout-phases.md) for prerequisites.

---

## Third-Party Services (in order)

### 1. Supabase (Sprint 1)

1. Create a project at [supabase.com](https://supabase.com).
2. Install CLI: `npm install -g supabase` (or use npx).
3. Link project: `supabase link --project-ref <your-ref>`.
4. Apply migrations: `supabase db push`.
5. Create your single user in **Authentication → Users → Add user** (email + password).
6. Copy the user's UUID and set `ALLOWED_USER_ID` in Supabase secrets or update the seed migration.
7. Copy **Project URL**, **anon key**, and **service_role key** for env files.

Optional: configure [Supabase MCP](https://supabase.com/docs/guides/getting-started/mcp) in Cursor for schema/advisor access.

### 2. Kalshi API (Sprint 2)

1. Create API credentials at [Kalshi](https://kalshi.com) (demo/sandbox first if available).
2. Store on Railway only: `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY`, `KALSHI_BASE_URL`.
3. Demo URL: `https://demo-api.kalshi.co/trade-api/v2`
4. Production URL: `https://api.elections.kalshi.com/trade-api/v2`

### 3. The Odds API (Sprint 2)

1. Sign up at [the-odds-api.com](https://the-odds-api.com).
2. Choose a plan with enough quota for World Cup polling.
3. Store `ODDS_API_KEY` on Railway only.
4. Configure sharp bookmakers in dashboard `bot_config` (e.g. `pinnacle`, `betfair_ex_uk`).

World Cup sport keys:
- `soccer_fifa_world_cup` — match odds
- `soccer_fifa_world_cup_winner` — outrights

### 4. Vercel (Sprint 2)

1. Import repo, set root to `apps/web`.
2. Env vars (public only):
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Deploy after auth/RLS is verified.

### 5. Railway (Sprint 3)

1. Create a service pointing to `apps/bot`.
2. Set start command: `python -m bot.main`
3. Add variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `KALSHI_API_KEY_ID`
   - `KALSHI_PRIVATE_KEY`
   - `KALSHI_BASE_URL`
   - `ODDS_API_KEY`
   - `BOT_ENV` (`paper` or `live`)
4. Click **Deploy** after adding/changing variables.

## Local Development

```bash
# Supabase local (optional)
supabase start

# Dashboard
cd apps/web
cp .env.example .env.local
npm install
npm run dev

# Bot
cd apps/bot
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m bot.main
```

## Discovery Script

```bash
cd apps/bot
python -m bot.scripts.discover_markets
```

Populates `kalshi_markets` and `sportsbook_events` for manual mapping in the dashboard.

### Kalshi markets not found?

The **demo API** often has zero World Cup/soccer markets. Auto-discovery scans events and markets for soccer keywords, but may still return 0.

**Option A — switch to production API** (if your account has access):
```env
KALSHI_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
KALSHI_WS_URL=wss://api.elections.kalshi.com/trade-api/ws/v2
```

**Option B — manual import by ticker** (recommended):
1. Find market tickers on kalshi.com (in the URL or market page)
2. Import them:
```bash
python -m bot.scripts.import_kalshi_markets KXWORLDCUP-25-ENG
python -m bot.scripts.import_kalshi_markets --event KXWORLDCUP-25-ENG
python -m bot.scripts.import_kalshi_markets --file kalshi_markets.txt
```
3. Or queue tickers in the dashboard **Mappings → Add Kalshi Market Manually**, then run the import command shown.

**Option C — filter by series/event in `.env`:**
```env
KALSHI_SERIES_TICKERS=KXSOCCER
KALSHI_EVENT_TICKERS=KXWORLDCUP-25-ENG
```
