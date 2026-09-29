"""Deterministic demo market data.

Generates a seeded random-walk price series per symbol, with a small,
deterministic post-event drift layered on top for symbols the demo events
are supposed to affect. This is what lets the Backtest Lab produce a
non-trivial result in an environment with no live market-data access — it
is a synthetic demonstration of the event -> price mechanism the platform
is built to detect, NOT a claim of real predictive edge. Every bar is
flagged is_demo=True and the live yfinance adapter (yfinance_adapter.py)
is the production path once network access and a real deployment exist.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from app.services.market_engine.base import Bar, MarketSource, Quote

DEMO_ASSETS: dict[str, dict] = {
    "CL=F": {"name": "Crude Oil WTI", "asset_class": "energy", "base_price": 78.0, "vol": 0.22},
    "NG=F": {"name": "Natural Gas", "asset_class": "energy", "base_price": 2.6, "vol": 0.35},
    "RB=F": {"name": "RBOB Gasoline", "asset_class": "energy", "base_price": 2.3, "vol": 0.28},
    "ZC=F": {"name": "Corn", "asset_class": "agriculture", "base_price": 4.4, "vol": 0.20},
    "ZS=F": {"name": "Soybeans", "asset_class": "agriculture", "base_price": 12.8, "vol": 0.20},
    "HG=F": {"name": "Copper", "asset_class": "metal", "base_price": 4.1, "vol": 0.24},
    "GC=F": {"name": "Gold", "asset_class": "metal", "base_price": 2350.0, "vol": 0.14},
    "LBS=F": {"name": "Lumber", "asset_class": "commodity", "base_price": 520.0, "vol": 0.30},
    "FDX": {"name": "FedEx Corp", "asset_class": "equity", "base_price": 245.0, "vol": 0.26},
    "XLU": {"name": "Utilities Select Sector SPDR", "asset_class": "etf", "base_price": 68.0, "vol": 0.16},
    "XLE": {"name": "Energy Select Sector SPDR", "asset_class": "etf", "base_price": 88.0, "vol": 0.24},
    "SOXX": {"name": "iShares Semiconductor ETF", "asset_class": "etf", "base_price": 210.0, "vol": 0.32},
    "SPX": {"name": "S&P 500 Index", "asset_class": "index", "base_price": 5450.0, "vol": 0.15},
}

_SEED = 42
HISTORY_DAYS = 30


def _symbol_seed(symbol: str) -> int:
    return _SEED + sum(ord(c) for c in symbol)


def _aware(dt: datetime) -> datetime:
    """SQLite round-trips DateTime(timezone=True) columns as naive, so
    values loaded from the DB can end up without tzinfo even though every
    value written was UTC. Normalize defensively wherever datetimes from
    different origins (DB rows vs datetime.now()) might get compared."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def generate_history(
    symbol: str,
    start: datetime,
    end: datetime,
    interval_hours: int = 1,
    event_impacts: list[tuple[datetime, float, str]] | None = None,
) -> list[Bar]:
    """event_impacts: list of (impact_time, magnitude[0-1], direction) applied
    as a decaying drift starting at impact_time, deterministic per symbol."""
    meta = DEMO_ASSETS.get(symbol, {"base_price": 100.0, "vol": 0.2})
    rng = random.Random(_symbol_seed(symbol))
    hourly_vol = meta["vol"] / math.sqrt(365 * 24)

    bars: list[Bar] = []
    price = meta["base_price"]
    ts = _aware(start)
    end = _aware(end)
    step = timedelta(hours=interval_hours)
    normalized_impacts = [(_aware(t), m, d) for t, m, d in (event_impacts or [])]

    while ts <= end:
        drift = 0.0
        for impact_time, magnitude, direction in normalized_impacts:
            if ts < impact_time:
                continue
            hours_since = (ts - impact_time).total_seconds() / 3600
            decay = math.exp(-hours_since / 48)  # impact fades over ~2 days
            sign = 1.0 if direction == "bullish" else -1.0
            drift += sign * magnitude * 0.06 * decay

        shock = rng.gauss(0, hourly_vol)
        price = max(price * (1 + shock + drift / max(interval_hours, 1)), 0.01)

        open_p = price / (1 + shock * 0.5)
        high = max(open_p, price) * (1 + abs(rng.gauss(0, hourly_vol * 0.3)))
        low = min(open_p, price) * (1 - abs(rng.gauss(0, hourly_vol * 0.3)))
        volume = abs(rng.gauss(1_000_000, 300_000))

        bars.append(Bar(ts=ts, open=round(open_p, 4), high=round(high, 4), low=round(low, 4), close=round(price, 4), volume=round(volume, 1)))
        ts += step

    return bars


class DemoMarketSource(MarketSource):
    name = "DEMO_MARKET"
    is_demo = True

    def __init__(self, event_impacts_by_symbol: dict[str, list[tuple[datetime, float, str]]] | None = None) -> None:
        self._impacts = event_impacts_by_symbol or {}

    def get_history(self, symbol: str, start: datetime, end: datetime, interval: str = "1h") -> list[Bar]:
        interval_hours = 24 if interval == "1d" else 1
        return generate_history(symbol, start, end, interval_hours, self._impacts.get(symbol))

    def get_quote(self, symbol: str) -> Quote:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=2)
        history = self.get_history(symbol, start, end, interval="1h")
        if not history:
            meta = DEMO_ASSETS.get(symbol, {"base_price": 100.0})
            return Quote(symbol=symbol, price=meta["base_price"], change_pct=0.0, ts=end, is_demo=True)
        last = history[-1]
        first = history[0]
        change_pct = ((last.close - first.open) / first.open) * 100 if first.open else 0.0
        return Quote(symbol=symbol, price=last.close, change_pct=round(change_pct, 3), ts=last.ts, is_demo=True)
