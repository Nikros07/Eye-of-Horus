from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eye_of_horus")

settings = get_settings()

app = FastAPI(
    title="Eye of Horus — Event Intelligence & Trading Platform",
    description="Event-to-market intelligence, quant research, and paper/live trading terminal.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Eye of Horus started | data_mode=%s live_trading_enabled=%s", settings.data_mode, settings.live_trading_enabled)

    from app.services.bootstrap import ensure_demo_data_seeded

    ensure_demo_data_seeded()

    from app.workers.scheduler import start_scheduler

    start_scheduler()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "data_mode": settings.data_mode,
        "live_trading_enabled": settings.live_trading_enabled,
    }


from app.api.routes import (  # noqa: E402
    alerts,
    backtests,
    events,
    impact,
    markets,
    portfolio,
    replay,
    research,
    risk,
    signals,
    stream,
    system,
    trading,
)

app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(impact.router, prefix="/api/impact-graph", tags=["impact"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(replay.router, prefix="/api/replay", tags=["replay"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(stream.router, prefix="/api/stream", tags=["stream"])
