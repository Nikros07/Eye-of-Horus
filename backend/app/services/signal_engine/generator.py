"""Live signal generation: given a persisted, impact-linked Event, run every
event-driven strategy against it and persist the resulting Signal rows. This
reuses the exact same strategy code the backtester replays historically —
see strategy_base.py for why that equivalence matters.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.market import Asset, PriceBar
from app.models.signal import Signal
from app.services.market_engine.base import Bar
from app.services.signal_engine.registry import EVENT_DRIVEN_STRATEGIES, get_strategy
from app.services.signal_engine.strategy_base import StrategyContext
from app.services.signal_engine.utils import return_over_window


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_price_series(db: Session, symbol: str, end: datetime, lookback_hours: int = 72) -> list[Bar]:
    asset = db.query(Asset).filter(Asset.symbol == symbol).one_or_none()
    if asset is None:
        return []
    start = end - timedelta(hours=lookback_hours)
    rows = (
        db.query(PriceBar)
        .filter(PriceBar.asset_id == asset.id, PriceBar.ts <= end, PriceBar.ts >= start, PriceBar.availability_time <= end)
        .order_by(PriceBar.ts.asc())
        .all()
    )
    return [Bar(ts=r.ts, open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume) for r in rows]


def _pricing_status(direction: str, bars: list[Bar]) -> str:
    move = return_over_window(bars, hours=6)
    if move is None:
        return "unpriced"
    signed_move = move if direction == "bullish" else -move
    if signed_move > 0.03:
        return "priced"
    if signed_move > 0.01:
        return "partially_priced"
    return "unpriced"


def build_context_for_event(db: Session, event: Event, as_of: datetime | None = None) -> StrategyContext:
    as_of = as_of or _now()
    price_history = {
        link.asset_symbol: load_price_series(db, link.asset_symbol, as_of) for link in event.impact_links
    }
    analogue_count = db.query(Event).filter(Event.event_type == event.event_type, Event.id != event.id).count()
    return StrategyContext(
        as_of=as_of,
        event=event,
        impact_links=list(event.impact_links),
        evidence_items=list(event.evidence),
        price_history=price_history,
        historical_analogue_count=analogue_count,
    )


def generate_signals_for_event(db: Session, event: Event) -> list[Signal]:
    ctx = build_context_for_event(db, event)
    created: list[Signal] = []

    for strategy_name in EVENT_DRIVEN_STRATEGIES:
        strategy = get_strategy(strategy_name)
        for candidate in strategy.generate(ctx):
            asset = db.query(Asset).filter(Asset.symbol == candidate.asset_symbol).one_or_none()
            if asset is None:
                continue

            exists = (
                db.query(Signal)
                .filter(Signal.event_id == event.id, Signal.asset_id == asset.id, Signal.strategy == candidate.strategy)
                .one_or_none()
            )
            if exists is not None:
                continue

            bars = ctx.price_history.get(candidate.asset_symbol, [])
            signal = Signal(
                event_id=event.id,
                asset_id=asset.id,
                direction=candidate.direction,
                confidence=candidate.confidence,
                expected_horizon=candidate.expected_horizon,
                reasoning=candidate.reasoning,
                evidence=candidate.evidence,
                strategy=candidate.strategy,
                strategy_version=candidate.strategy_version,
                data_version=event.data_version,
                pricing_status=_pricing_status(candidate.direction, bars),
                signal_time=ctx.as_of,
                availability_time=event.availability_time,
            )
            db.add(signal)
            created.append(signal)

    db.flush()
    return created


def generate_signals_for_all_events(db: Session) -> list[Signal]:
    events = db.query(Event).all()
    all_created: list[Signal] = []
    for event in events:
        all_created.extend(generate_signals_for_event(db, event))
    return all_created
