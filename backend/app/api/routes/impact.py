from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.serializers import serialize_impact_link
from app.core.db import get_db
from app.models.event import Event

router = APIRouter()


@router.get("/{event_id}")
def get_impact_graph(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if event is None:
        raise HTTPException(404, "Event not found")
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "links": [serialize_impact_link(link) for link in event.impact_links],
    }
