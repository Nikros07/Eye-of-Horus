from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.event import Event
from app.models.market import Asset, PriceBar
from app.models.system import DataSource
from app.services.market_engine.base import Bar, MarketSource
from app.services.market_engine.demo_adapter import DEMO_ASSETS, HISTORY_DAYS, generate_history

_UTCNOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _aware(dt: datetime) -> datetime:
    """SQLite round-trips DateTime(timezone=True) columns as naive; normalize
    defensively before comparing a DB-loaded timestamp against datetime.now()."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def run_price_ingestion(db: Session) -> None:
    """Single entry point the bootstrap seed and the scheduler both call:
    keeps PriceBar populated regardless of which market data mode is active,
    so neither caller needs to know which provider is behind it."""
    settings = get_settings()
    if settings.data_mode == "demo":
        seed_demo_price_history(db)
        return

    from app.services.market_engine.factory import get_market_source

    sync_live_price_history(db, get_market_source())


def ensure_assets(db: Session) -> dict[str, Asset]:
    assets: dict[str, Asset] = {}
    for symbol, meta in DEMO_ASSETS.items():
        asset = db.query(Asset).filter(Asset.symbol == symbol).one_or_none()
        if asset is None:
            asset = Asset(symbol=symbol, name=meta["name"], asset_class=meta["asset_class"], currency="USD")
            db.add(asset)
            db.flush()
        assets[symbol] = asset
    return assets


def seed_demo_price_history(db: Session, now: datetime | None = None) -> None:
    now = now or _UTCNOW()
    start = time.monotonic()
    assets = ensure_assets(db)

    events = db.query(Event).filter(Event.is_demo.is_(True)).all()
    impacts_by_symbol: dict[str, list[tuple[datetime, float, str]]] = {}
    for event in events:
        for symbol, exposure in (event.market_exposure or {}).items():
            impacts_by_symbol.setdefault(symbol, []).append((event.publication_time or event.timestamp, exposure, _direction_for(event, symbol)))

    period_start = now - timedelta(days=HISTORY_DAYS)

    for symbol, asset in assets.items():
        existing = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).count()
        if existing > 0:
            continue
        bars = generate_history(symbol, period_start, now, interval_hours=1, event_impacts=impacts_by_symbol.get(symbol))
        for bar in bars:
            db.add(
                PriceBar(
                    asset_id=asset.id,
                    ts=bar.ts,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    source="DEMO_MARKET",
                    availability_time=bar.ts,
                    is_demo=True,
                )
            )
    db.flush()

    source = db.query(DataSource).filter(DataSource.name == "DEMO_MARKET").one_or_none()
    if source is None:
        source = DataSource(name="DEMO_MARKET", kind="market", is_demo=True)
        db.add(source)
    source.status = "online"
    source.last_success_at = _UTCNOW()
    source.latency_ms = (time.monotonic() - start) * 1000
    db.flush()


def _direction_for(event: Event, symbol: str) -> str:
    from app.services.impact_engine.rules import rules_for

    for rule in rules_for(event.event_type):
        if rule.asset_symbol == symbol:
            return rule.direction
    return "bullish"


def _price_bar_row(asset_id: int, bar: Bar, market_source: MarketSource) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        ts=bar.ts,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        source=market_source.name,
        availability_time=bar.ts,
        is_demo=market_source.is_demo,
    )


# Touching every symbol in one call means up to 13 sequential external HTTP
# calls (each allowed by yfinance's own defaults to take 10-30s) inside a
# single open transaction. On Render's free tier that was slow/heavy enough
# to starve the process and fail its health check (incident 2026-10-03,
# commit 7bc03b4 -> service down ~9 min after the first live sync ran).
# Capping and committing per-symbol bounds each call's worst case to a few
# tens of seconds; the full universe backfills gradually over several
# ingestion cycles instead of all at once.
MAX_SYMBOLS_PER_SYNC_CYCLE = 3


def sync_live_price_history(db: Session, market_source: MarketSource, now: datetime | None = None) -> None:
    """Keeps PriceBar current from a real MarketSource (yfinance), a few
    symbols at a time (see MAX_SYMBOLS_PER_SYNC_CYCLE). Unlike
    seed_demo_price_history this is not a one-time seed: it is meant to run
    on every ingestion cycle so prices stay fresh. A rate-limited or failing
    symbol only degrades that one symbol — it never blocks the others or the
    ingestion cycle calling this.
    """
    now = now or _UTCNOW()
    start = time.monotonic()
    assets = ensure_assets(db)
    db.commit()

    # Symbols with no history at all are more urgent than ones that just
    # need a fresh quote, so they're backfilled first. needs_backfill=True
    # marks which of the two this item is, since that's decided once here
    # rather than re-derived per item in the loop below.
    work: list[tuple[str, Asset, bool]] = []
    needs_quote: list[tuple[str, Asset, bool]] = []
    for symbol, asset in assets.items():
        latest = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.ts.desc()).first()
        if latest is None:
            work.append((symbol, asset, True))
        elif _aware(latest.ts) <= now - timedelta(minutes=1):
            needs_quote.append((symbol, asset, False))
    work = (work + needs_quote)[:MAX_SYMBOLS_PER_SYNC_CYCLE]

    ok_count = 0
    last_error: str | None = None
    for symbol, asset, needs_backfill in work:
        try:
            if needs_backfill:
                backfill_start = now - timedelta(days=HISTORY_DAYS)
                bars = market_source.get_history(symbol, backfill_start, now, interval="1h")
                for bar in bars:
                    db.add(_price_bar_row(asset.id, bar, market_source))
            else:
                quote = market_source.get_quote(symbol)
                bar = Bar(ts=quote.ts, open=quote.price, high=quote.price, low=quote.price, close=quote.price, volume=0.0)
                db.add(_price_bar_row(asset.id, bar, market_source))
            db.commit()
            ok_count += 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            last_error = f"{symbol}: {exc}"

    source = db.query(DataSource).filter(DataSource.name == market_source.name).one_or_none()
    if source is None:
        source = DataSource(name=market_source.name, kind="market", is_demo=market_source.is_demo)
        db.add(source)
    source.is_demo = market_source.is_demo
    if work:
        source.status = "online" if (ok_count > 0 and last_error is None) else ("degraded" if ok_count > 0 else "offline")
        if ok_count > 0:
            source.last_success_at = _UTCNOW()
        source.last_error = last_error
    source.latency_ms = (time.monotonic() - start) * 1000
    db.commit()
