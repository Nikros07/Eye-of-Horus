"""Alert Center — alerts are derived from recent signals rather than being
a separate stored entity, so they can never drift out of sync with what the
signal engine actually produced.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.signal import Signal

router = APIRouter()


def _severity_for(signal: Signal) -> str:
    event_severity = signal.event.severity if signal.event else "low"
    if signal.confidence >= 0.8 and event_severity in ("high", "critical"):
        return "critical"
    if signal.confidence >= 0.65:
        return "high"
    if signal.confidence >= 0.5:
        return "medium"
    return "low"


@router.get("")
def list_alerts(
    db: Session = Depends(get_db),
    severity: str | None = None,
    asset_symbol: str | None = None,
    hours: int = Query(72, le=24 * 30),
    limit: int = Query(50, le=200),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = (
        db.query(Signal)
        .filter(Signal.signal_time >= since)
        .order_by(Signal.confidence.desc(), Signal.signal_time.desc())
        .limit(limit * 3)
        .all()
    )

    alerts = []
    for s in signals:
        if asset_symbol and s.asset.symbol != asset_symbol:
            continue
        alert_severity = _severity_for(s)
        if severity and alert_severity != severity:
            continue
        alerts.append(
            {
                "signal_id": s.signal_id,
                "severity": alert_severity,
                "asset_symbol": s.asset.symbol,
                "event_type": s.event.event_type if s.event else None,
                "event_title": s.event.title if s.event else None,
                "direction": s.direction,
                "confidence": s.confidence,
                "expected_horizon": s.expected_horizon,
                "status": s.pricing_status,
                "strategy": s.strategy,
                "signal_time": s.signal_time.isoformat(),
            }
        )
        if len(alerts) >= limit:
            break

    return alerts
