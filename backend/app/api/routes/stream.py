"""SSE realtime stream. A lightweight polling-based push: every
`poll_interval` seconds it emits the current top signals and asset quotes.
For MVP volumes this is simpler and more robust than a pub/sub layer, and
easy to swap for one later if ingestion volume ever demands it.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.db import SessionLocal
from app.models.market import Asset
from app.models.signal import Signal
from app.services.market_engine.factory import get_market_source

router = APIRouter()

POLL_INTERVAL_SECONDS = 5


async def _event_generator(request: Request):
    market_source = get_market_source()
    while True:
        if await request.is_disconnected():
            break

        db = SessionLocal()
        try:
            latest_signals = db.query(Signal).order_by(Signal.signal_time.desc()).limit(5).all()
            assets = db.query(Asset).limit(20).all()

            quotes = []
            for asset in assets:
                try:
                    q = market_source.get_quote(asset.symbol)
                    quotes.append({"symbol": asset.symbol, "price": q.price, "change_pct": q.change_pct})
                except Exception:  # noqa: BLE001
                    continue

            payload = {
                "signals": [
                    {
                        "signal_id": s.signal_id,
                        "asset_symbol": s.asset.symbol,
                        "direction": s.direction,
                        "confidence": s.confidence,
                        "strategy": s.strategy,
                    }
                    for s in latest_signals
                ],
                "quotes": quotes,
                "is_demo": market_source.is_demo,
            }
        finally:
            db.close()

        yield {"event": "update", "data": json.dumps(payload)}
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get("/live")
async def stream_live(request: Request):
    return EventSourceResponse(_event_generator(request))
