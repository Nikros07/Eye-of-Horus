from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.market import Asset, PriceBar
from app.models.system import DataSource
from app.services.market_engine.demo_adapter import DEMO_ASSETS, HISTORY_DAYS, generate_history

_UTCNOW = lambda: datetime.now(timezone.utc)  # noqa: E731


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
