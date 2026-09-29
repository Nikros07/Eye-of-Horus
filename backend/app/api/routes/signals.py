from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.serializers import serialize_signal
from app.core.db import get_db
from app.models.signal import Signal
from app.services.research.trade_analysis import analyze_signal

router = APIRouter()


@router.get("")
def list_signals(
    db: Session = Depends(get_db),
    asset_symbol: str | None = None,
    strategy: str | None = None,
    min_confidence: float = 0.0,
    limit: int = Query(50, le=200),
):
    q = db.query(Signal)
    if strategy:
        q = q.filter(Signal.strategy == strategy)
    if min_confidence:
        q = q.filter(Signal.confidence >= min_confidence)
    signals = q.order_by(Signal.signal_time.desc()).limit(limit).all()
    if asset_symbol:
        signals = [s for s in signals if s.asset.symbol == asset_symbol]
    return [serialize_signal(s) for s in signals]


@router.get("/{signal_id}")
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.signal_id == signal_id).one_or_none()
    if signal is None:
        raise HTTPException(404, "Signal not found")
    return serialize_signal(signal)


@router.get("/{signal_id}/analysis")
def get_signal_analysis(signal_id: str, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.signal_id == signal_id).one_or_none()
    if signal is None:
        raise HTTPException(404, "Signal not found")
    return asdict(analyze_signal(db, signal))
