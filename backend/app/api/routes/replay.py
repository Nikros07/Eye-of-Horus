"""Research Replay — reconstructs exactly what the system knew at a chosen
past instant: which events existed, which evidence had arrived, and which
signals its strategies would have generated, using the same TemporalGuard
the backtester uses. No data with availability_time after `as_of` is ever
included in the response.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.serializers import serialize_event
from app.core.db import get_db
from app.models.event import Event
from app.services.quant_engine.temporal import TemporalGuard
from app.services.signal_engine.generator import build_context_for_event
from app.services.signal_engine.registry import EVENT_DRIVEN_STRATEGIES, get_strategy

router = APIRouter()


@router.get("")
def replay_as_of(as_of: datetime = Query(...), db: Session = Depends(get_db)):
    guard = TemporalGuard(as_of=as_of)

    events = db.query(Event).filter(Event.availability_time <= as_of).order_by(Event.availability_time.desc()).all()

    would_have_signals = []
    for event in events:
        ctx = build_context_for_event(db, event, as_of=as_of)
        ctx.evidence_items = guard.filter_available(ctx.evidence_items, lambda e: e.availability_time)
        ctx.price_history = {
            symbol: [b for b in bars if b.ts <= as_of] for symbol, bars in ctx.price_history.items()
        }
        for strategy_name in EVENT_DRIVEN_STRATEGIES:
            for candidate in get_strategy(strategy_name).generate(ctx):
                would_have_signals.append(
                    {
                        "event_id": event.event_id,
                        "asset_symbol": candidate.asset_symbol,
                        "direction": candidate.direction,
                        "confidence": candidate.confidence,
                        "strategy": candidate.strategy,
                        "reasoning": candidate.reasoning,
                    }
                )

    return {
        "as_of": as_of.isoformat(),
        "known_events": [serialize_event(e, include_details=True) for e in events],
        "would_have_generated_signals": would_have_signals,
        "note": "No data with availability_time after as_of is included in this view.",
    }
