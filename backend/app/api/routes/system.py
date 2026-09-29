from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.event import Event
from app.models.signal import Signal
from app.models.system import DataSource

router = APIRouter()


@router.get("/status")
def system_status(db: Session = Depends(get_db)):
    settings = get_settings()
    sources = db.query(DataSource).all()
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "data_mode": settings.data_mode,
        "live_trading_enabled": settings.live_trading_enabled,
        "market_data_provider": settings.market_data_provider,
        "data_sources": [
            {
                "name": s.name,
                "kind": s.kind,
                "status": s.status,
                "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                "last_error": s.last_error,
                "latency_ms": round(s.latency_ms, 1) if s.latency_ms is not None else None,
                "is_demo": s.is_demo,
            }
            for s in sources
        ],
        "totals": {
            "events": db.query(Event).count(),
            "signals": db.query(Signal).count(),
        },
    }
