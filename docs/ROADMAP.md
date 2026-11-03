# Eye of Horus — architecture notes & roadmap

Written 2026-11-03 to hand off a clear, accurate picture of the system and
what's genuinely next — for a future session (any model) picking this up
without re-deriving the whole history from the repo. Keep this updated as
things change; a stale roadmap is worse than none.

## How the system fits together

Six backend layers, each with its own `app/services/<layer>/` directory,
feeding into each other in one direction:

1. **Event Engine** (`event_engine/`) — ingests real-world events.
   `DATA_MODE=demo`: `connectors/demo_connector.py`, deterministic seeded
   generator. `DATA_MODE=live`: `connectors/nasa_eonet.py` (source of
   truth for events) cross-corroborated by `connectors/open_meteo.py`
   (weather-sensitive types only) and `connectors/gdacs.py` (any type
   GDACS also tracks — added 2026-11-03, see below). `normalizer.py`
   dedupes and persists; `verification.py` turns source count + evidence
   into a confidence score.
2. **Impact Engine** (`impact_engine/`) — `rules.py` is a hand-authored,
   auditable `event_type -> (asset, exposure, direction)` table (not a
   learned model, deliberately — see the file's own docstring for why).
   `graph.py` materializes the EVENT -> ... -> ASSET causal chain shown in
   the UI.
3. **Market Engine** (`market_engine/`) — price data. `ingest.py`'s
   `run_price_ingestion()` is the single entry point both the startup seed
   and the scheduler call; it branches on `DATA_MODE` internally so
   neither caller needs to know which provider is behind it.
   `demo_adapter.py` generates synthetic history once. `yfinance_adapter.py`
   is the live path — `sync_live_price_history()` backfills/refreshes at
   most `MAX_SYMBOLS_PER_SYNC_CYCLE` (3) symbols per call, deliberately
   throttled (see Known Incidents below).
4. **Signal Engine** (`signal_engine/`) — five strategies in
   `strategies/*.py`, registered in `registry.py`, sharing one
   `StrategyContext` built in `generator.py`. `baseline_trend` is the only
   event-independent one (pure price momentum, flat 0.5 confidence); the
   other four all gate candidate generation on `event.confidence` via a
   per-strategy `MIN_CONFIDENCE` constant before ever producing a signal.
5. **Quant Engine** (`quant_engine/` or similar — backtester) — replays
   strategies historically through the same `StrategyContext` builder
   signals use live, so backtest and live paths can never silently diverge
   (see `strategy_base.py`'s docstring).
6. **Trading Engine** (`trading_engine/`) — `broker_base.py` defines the
   `BrokerAdapter` interface; `paper_broker.py` (in-process simulation,
   default), `alpaca_broker.py` (real orders against Alpaca's free paper
   venue, opt-in), `live_broker.py` (deliberate real-money stub, always
   refuses). `risk_engine.py` gates every order — kill switch, exposure,
   drawdown, daily loss, cooldown — reading only from the local DB, which
   is why `AlpacaBroker` resyncs local `Portfolio`/`Position` rows after
   every order rather than `RiskEngine` ever touching Alpaca directly.
   `auto_trade.py`'s `run_auto_trade_cycle()` is what the scheduler calls
   every 90s; it only acts on portfolios with `auto_trade_enabled=True`.

Plus a **Research/AI layer** (`research/llm_provider.py` — Claude or
Gemini, falls back to a deterministic synthesizer with no key), the
**API** (`api/routes/*.py`, FastAPI, SSE for realtime), and the
**scheduler** (`workers/scheduler.py`, APScheduler `BackgroundScheduler`,
in-process — two jobs: event+price ingestion every
`INGESTION_INTERVAL_SECONDS` (default 300s), auto-trade every 90s).

Frontend: Next.js static export (`frontend/`, GitHub Pages), React Three
Fiber globe as the centerpiece, deployed independently of the backend.

## Deployment shape

- **Backend**: Render free tier, `render.yaml` blueprint,
  `autoDeploy: true` off the branch this repo's sessions push to. SQLite,
  **ephemeral** — wiped on every redeploy/restart; `bootstrap.py`'s
  `ensure_demo_data_seeded()` reseeds everything (including the Main
  Portfolio's defaults) on every startup, which is *why* those defaults
  matter so much — see Known Incidents.
- **Frontend**: GitHub Pages via `.github/workflows/gh-pages.yml`, static,
  talks to the backend via `NEXT_PUBLIC_API_BASE` (baked in at build time,
  needs a manual workflow re-run after changing it).
- **No CI** runs against pull requests in this repo — the only GitHub
  Actions workflow is the frontend's Pages deploy, scoped to pushes to
  `main` touching `frontend/**`. "CI green" for a backend-only PR has
  always meant the author's own local `pytest`/`ruff` run; there is no
  server-side gate. Worth knowing before assuming a merged PR was
  independently verified by anything other than whoever wrote it.

## Current live-system state (as of this writing — verify before trusting)

- Alpaca paper broker: was confirmed live once (`cash: 100000` observed),
  then silently reverted twice by deploys before the render.yaml
  `sync: false` fix (PR #14) shipped. **Needs a human to re-set
  `BROKER_PROVIDER=alpaca` in the Render dashboard one more time** after
  that fix's deploy — it was still sitting at `internal` last checked.
  After that one-time reset it should survive all future deploys.
- `DATA_MODE=live` / `MARKET_DATA_PROVIDER=yfinance`: set in `render.yaml`,
  should be active. Not independently re-verified against the live
  instance after the GDACS/SPX PR (#15).
- Auto-trade: `auto_trade_enabled=True`, `auto_trade_min_confidence=0.15`
  seeded by default (`bootstrap.py`) since PR #13. Combined with GDACS
  corroboration (PR #15), more live signals should now actually clear
  their strategy's confidence gate than before — not yet confirmed live.
- Keep-alive: user set up a cron-job.org ping to `/api/health` every 10
  minutes, confirmed working as of that check. Without it the free-tier
  instance spins down after ~15 min idle, which also pauses the scheduler
  (no ingestion, no auto-trade) until the next request wakes it.

**Nobody has yet confirmed a real order actually landed in Alpaca's own
dashboard.** `/api/trading/orders` returning a non-empty list, and
`/api/trading/account`'s `cash` moving away from a round number, are the
two cheapest ways to check from outside Render's dashboard.

## Known incidents this session (read before changing `render.yaml` or the ingestion/scheduler code)

1. **Live price sync starved the process (2026-10-22-ish).** Syncing all
   13 tracked symbols sequentially in one call, each yfinance request
   allowed up to 10-30s by the library's own defaults, inside one open DB
   transaction, was enough to fail the health check on Render's free tier
   ~9 minutes after deploy. Fixed by `MAX_SYMBOLS_PER_SYNC_CYCLE` (3) and
   per-symbol commits (`market_engine/ingest.py`). **If you ever increase
   that cap or add more tracked symbols, re-think this risk — it will
   come back.**
2. **render.yaml silently reset manual dashboard choices.** `BROKER_PROVIDER`
   and `LLM_PROVIDER` had a `value:` directly in the blueprint instead of
   `sync: false`. Render's blueprint sync re-applies every non-`sync:false`
   value on *every* deploy, so three merges in a row silently undid the
   user's manual Alpaca opt-in with no error or warning anywhere. Fixed in
   PR #14. **Any new env var meant to be a personal, per-deployment,
   dashboard-only opt-in (not something a code change should ever
   override) must be `sync: false` from the start** — this bug class is
   easy to reintroduce by copy-pasting an existing `value:` entry.
3. **A whole category of live events had no possible second corroboration
   source** (earthquakes, volcanic activity — anything Open-Meteo can't
   speak to) until GDACS was added (PR #15). If you add more live event
   types to `nasa_eonet.py`'s `CATEGORY_MAP`, check whether GDACS's
   `GDACS_TYPE_MAP` (`connectors/gdacs.py`) needs a matching entry, or
   that type is back to being effectively single-source-only.

## Things nobody has verified against the real live endpoints from this dev environment

This sandboxed environment has no outbound network access to Render,
Yahoo Finance, Alpaca, GDACS, or NASA EONET (only github.com, pypi,
npm, and a short allowlist are reachable). Every live-network integration
in this codebase (Alpaca, Gemini, yfinance, GDACS, Open-Meteo) has
necessarily been tested against mocked HTTP responses, never the real
thing, from here. That's a reasonable way to develop it, but it means:
**the first real confirmation of correctness for any of these always has
to come from checking the actual deployed instance** — don't assume a
green local test suite means the real external API still matches the
shape assumed in the mocks. GDACS in particular: the exact RSS/GeoRSS
schema was written from well-known, long-stable public documentation, not
verified against a live response — the parser is deliberately
namespace-agnostic and degrades to "no match" rather than crashing if the
real structure has drifted, but if GDACS corroboration never seems to
fire in practice, check the real feed's structure first.

## Prioritized next steps

Roughly in order of value for effort; none of these are started.

1. **Verify the current live state** (see "Current live-system state"
   above) — cheapest, highest-value next action, blocks trusting anything
   else here.
2. **Persist the database.** Every redeploy wipes trade history, which
   makes "did it actually trade" hard to answer in retrospect and resets
   `AutoTradeAttempt` dedup state. `render.yaml`'s own comment already
   notes `DATABASE_URL` pointing at a managed Postgres (e.g. Render's free
   Postgres tier, or Supabase/Neon's) is a drop-in change — `database_url`
   in `core/config.py` already accepts any SQLAlchemy URL.
3. **A richer live-mode corroboration source for event types GDACS and
   Open-Meteo both miss** — e.g. a free news API (GDELT, or a
   rate-limited free tier of NewsAPI) for `port_disruption` and similar
   types neither current source can speak to at all.
4. **Reconsider `MAX_SYMBOLS_PER_SYNC_CYCLE`.** At 3 symbols per 5-minute
   cycle, backfilling all 13 tracked symbols from cold takes ~20-25
   minutes after every redeploy (and the DB is wiped on every redeploy —
   see above). Fine once Postgres persistence lands; worth tuning
   carefully if it doesn't.
5. **A real CI workflow for the backend** (`pytest` + `ruff` on every PR).
   Doesn't exist today — every "tests pass" claim in this repo's PR
   history has been the author's own local run, never independently
   verified. Cheap to add, meaningfully raises confidence in future
   changes.
6. **Frontend verification of the auto-trade toggle UI**
   (`frontend/app/trading/page.tsx`) against the current backend contract
   — not re-checked since the `auto_trade_min_confidence` default changed.
