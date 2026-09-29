from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.serializers import serialize_asset_with_quote
from app.core.db import get_db
from app.models.market import Asset
from app.services.market_engine.factory import get_market_source

router = APIRouter()


@router.get("/assets")
def list_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    return [serialize_asset_with_quote(a) for a in assets]


@router.get("/{symbol}/quote")
def get_quote(symbol: str):
    market_source = get_market_source()
    try:
        quote = market_source.get_quote(symbol)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch quote: {exc}") from exc
    return {"symbol": quote.symbol, "price": quote.price, "change_pct": quote.change_pct, "ts": quote.ts.isoformat(), "is_demo": quote.is_demo}


@router.get("/{symbol}/history")
def get_history(symbol: str, hours: int = Query(168, le=24 * 90), interval: str = "1h"):
    market_source = get_market_source()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    try:
        bars = market_source.get_history(symbol, start, end, interval=interval)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch history: {exc}") from exc
    return {
        "symbol": symbol,
        "is_demo": market_source.is_demo,
        "bars": [{"ts": b.ts.isoformat(), "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} for b in bars],
    }
