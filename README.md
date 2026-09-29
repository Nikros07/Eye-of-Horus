# Eye of Horus

**Event-to-Market Intelligence & Autonomous Trading Platform**

A system that tracks the causal chain from real-world events to market impact:

```
EVENT → VERIFICATION → GEOSPATIAL/IMPACT ANALYSIS → INFRASTRUCTURE → SUPPLY CHAIN
  → COMMODITIES/MARKETS → SIGNAL → BACKTEST → PAPER TRADE → OUTCOME → LEARNING
```

The core research question the platform is built to test empirically, not assume:
**did the system detect real-world information early enough and reliably enough to
provide measurable informational value?**

## Architecture

Three layers, two apps:

- **`backend/`** (FastAPI/Python) — Intelligence Engine (event ingestion, verification,
  impact graph), Quant Engine (signal generation, event-driven backtester with an
  enforced temporal-integrity guard), Trading Engine (paper broker, risk engine, a
  safety-stubbed live broker interface), and an AI Research layer.
- **`frontend/`** (Next.js/TypeScript) — the premium terminal UI: a 3D rotating globe
  event map, glass/3D-tilt cards, trading terminal, backtest lab, research replay,
  alert center, and system status.

See `backend/app/` and `frontend/app/` for the full module layout; most modules carry
a short docstring/comment explaining *why*, not just what.

## Data mode: demo vs. live

`DATA_MODE=demo` (the default) uses deterministic, seeded generators for events and
market prices — every row is flagged `is_demo: true` end-to-end into the API and UI,
with a visible "DEMO" badge wherever that data is shown. This exists because outbound
network access to NASA/NOAA/market-data APIs isn't available in every environment
(including the sandbox this was built in). The real connectors are fully implemented
(`app/services/event_engine/connectors/nasa_eonet.py`, `open_meteo.py`,
`app/services/market_engine/yfinance_adapter.py`) — switching to `DATA_MODE=live` and
`MARKET_DATA_PROVIDER=yfinance` is a config change, not a rewrite, once the deployment
environment has real network access.

The demo market-data generator layers a small, deterministic post-event price drift on
top of a random walk, specifically so the Backtest Lab has something non-trivial to
find in an environment with no live data. That drift is a demonstration of the
event→price mechanism the platform is built to detect — **not** a claim of real
predictive edge. In live mode, prices come from Yahoo Finance with no synthetic signal
baked in.

## Running locally (no Docker)

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # defaults are fine for demo mode
uvicorn app.main:app --reload --port 8000
```

On first startup it seeds demo events, computes impact chains, seeds demo price
history, generates signals, and creates a default paper portfolio with $10,000 —
all idempotent, safe to restart.

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

Open http://localhost:3000.

## Running with Docker

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:3000`, Postgres+PostGIS on `:5432` (production-parity
DB; local dev defaults to SQLite for zero infra). Postgres/PostGIS is included ahead of
actual need, since geospatial event queries are the obvious next step once event volume
grows past what lat/lon float columns comfortably support.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

39 tests covering every engine, including a **verified, adversarial** look-ahead-bias
test: it deliberately persists a price bar whose `availability_time` is after the
event that would use it, and asserts the backtester's `TemporalGuard` catches it and
sets `look_ahead_bias_detected: true` rather than silently trading on it.

## MVP scope

Built: Event Engine (NASA EONET connector + demo generator), Market Engine (adapter
interface + demo generator + yfinance adapter), Impact Engine (rule-based
event→infrastructure→supply-chain→commodity graph), Signal Engine (5 strategies incl.
a naive baseline every other strategy must beat), Quant Engine (event-driven backtester
with enforced temporal integrity, walk-forward-capable structure), Trading Engine
(`BrokerAdapter` interface, `PaperBroker` with simulated spread/fees/slippage, a
safety-stubbed `LiveBroker`, `RiskEngine` with position sizing/exposure/drawdown/daily-
loss limits and a kill switch), AI Research layer (deterministic evidence synthesis +
pluggable Claude API provider), and the full premium frontend (3D globe, 3D cards,
event detail, trading terminal, backtest lab, research replay, alert center, system
status).

Deferred, interfaces in place but not implemented: live AIS/flight feeds, satellite
imagery, a persisted supply-chain graph database, advanced ML models, and a real live
broker integration (no broker credentials exist anywhere in this repo, and
`LiveBroker` refuses to place orders — see `LIVE_TRADING_ENABLED` — until one is wired
in deliberately).

## Validation checklist

| Capability | Status |
|---|---|
| Detect events | ✅ NASA EONET connector + demo generator |
| Verify events | ✅ multi-source/multi-evidence confidence scoring, verified/pending/unverified/disputed |
| Geolocate events | ✅ lat/lon + GeoJSON, rendered on the 3D globe |
| Connect infrastructure | ✅ rule-based impact graph (event→infra→supply chain→commodity) |
| Determine market exposure | ✅ exposure scoring on every impact link |
| Generate a signal | ✅ 5 strategies incl. baseline |
| Backtest the signal | ✅ event-driven backtester, per-strategy metrics |
| Prevent look-ahead bias | ✅ `TemporalGuard`, adversarially tested |
| Simulate a trade | ✅ `PaperBroker` with spread/fees/slippage |
| Calculate P&L / drawdown | ✅ portfolio + backtest metrics |
| Explain a signal | ✅ AI Research layer, OBSERVED/DERIVED/HYPOTHESIS/UNCERTAIN |
| Replay history | ✅ Research Replay, point-in-time reconstruction |
| Identify false positives | ✅ backtest `signal_stats` |
| Track outcomes | ✅ trade ledger + performance page |
| Frontend displays it clearly | ✅ dashboard, event detail, trading terminal, backtest lab |
| Survive a failed data source | ✅ per-source status tracking, degrades independently |
| Run locally | ✅ |
| Deployable | ✅ Dockerfiles + docker-compose |
