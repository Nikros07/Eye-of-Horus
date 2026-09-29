from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.serializers import serialize_event
from app.core.db import get_db
from app.models.event import Event

router = APIRouter()


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    event_type: str | None = None,
    min_confidence: float = 0.0,
    limit: int = Query(50, le=200),
):
    q = db.query(Event)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if min_confidence:
        q = q.filter(Event.confidence >= min_confidence)
    events = q.order_by(Event.last_updated.desc()).limit(limit).all()
    return [serialize_event(e) for e in events]


@router.get("/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if event is None:
        raise HTTPException(404, "Event not found")
    return serialize_event(event, include_details=True)


@router.get("/{event_id}/historical-analogues")
def historical_analogues(event_id: str, db: Session = Depends(get_db), limit: int = 5):
    event = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if event is None:
        raise HTTPException(404, "Event not found")
    analogues = (
        db.query(Event)
        .filter(Event.event_type == event.event_type, Event.id != event.id)
        .order_by(Event.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [serialize_event(a) for a in analogues]
