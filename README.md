# KalshiBot

Personal Kalshi World Cup trading bot with a Next.js dashboard (Vercel), Supabase backend, and Python worker (Railway).

## Architecture

```
Dashboard (Next.js/Vercel) ──► Supabase ◄── Bot Worker (Python/Railway)
                                    │
                              Kalshi API + The Odds API
```

- **Dashboard** talks only to Supabase (anon key + authenticated session).
- **Bot** talks to Kalshi, The Odds API, and Supabase (service role key).
- **Secrets** live on Railway only — never in Vercel or git.

## Monorepo Layout

| Path | Purpose |
|------|---------|
| `apps/web` | Next.js dashboard |
| `apps/bot` | Python trading worker |
| `supabase` | Migrations, config, generated types |
| `docs` | Setup, architecture, security |

## Quick Start

1. See [docs/setup.md](docs/setup.md) for third-party service setup.
2. See [docs/rollout-phases.md](docs/rollout-phases.md) for the current deployment phase (demo → production paper → live).
3. Apply Supabase migrations: `supabase db push` (or `supabase start` locally).
4. Copy env examples: `apps/web/.env.example` → `.env.local`, `apps/bot/.env.example` → `.env`.
5. Run dashboard: `cd apps/web && npm install && npm run dev`.
6. Run bot: `cd apps/bot && pip install -r requirements.txt && python -m bot.main`.

## Rollout Phases (operations)

| Phase | Kalshi API | Mode | Purpose |
|-------|------------|------|---------|
| 1 | Demo | Paper | Plumbing — loops, dashboard, Supabase |
| 2 | Production | Paper | Real World Cup markets, strategy soak |
| 3 | Production | Live | Real orders after paper validation |

Details and checklists: [docs/rollout-phases.md](docs/rollout-phases.md)

## Build Sprints (implementation — complete)

1. **Foundation** — monorepo, schema, auth, docs
2. **Mapping + Dashboard** — discovery scripts, mapping UI, monitoring views
3. **Paper Bot** — fetcher, strategy, executor loops
4. **Live Hardening** — WebSocket mode, risk controls, reconciliation

## Documentation

- [Rollout Phases](docs/rollout-phases.md)
- [Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
