# Security

## Secret Placement

| Secret | Location | Never In |
|--------|----------|----------|
| Supabase anon key | Vercel env | — |
| Supabase service role | Railway env | Vercel, git, browser |
| Kalshi API credentials | Railway env | Vercel, git, browser |
| Odds API key | Railway env | Vercel, git, browser |

## Authentication

- Single-user Supabase Auth (email + password).
- User created manually in Supabase dashboard — no public signup.
- `profiles.is_allowed = true` gates RLS access.
- Dashboard uses `@supabase/ssr` with cookie-based PKCE flow.
- Server components validate identity via `supabase.auth.getUser()`.

## Row Level Security

- RLS enabled on all public tables.
- Policies require authenticated user with `profiles.is_allowed = true`.
- Bot bypasses RLS via service role key (Railway only).

## API Key Handling

- Kalshi auth uses signed headers — never query string params.
- Odds API key is passed as query param by their API; restrict to server-side bot only.
- No secrets in URL query strings for our own routes.

## Trading Safety

- Default: paper trading mode.
- Kill switch in `bot_config` halts all order placement.
- Live mode requires explicit config change + passing risk checks.
