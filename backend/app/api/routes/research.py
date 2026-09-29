from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.event import Event
from app.services.research.evidence import build_evidence_bundle
from app.services.research.synthesizer import synthesize_research

router = APIRouter()


@router.get("/events/{event_id}")
def get_event_research(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if event is None:
        raise HTTPException(404, "Event not found")
    bundle = build_evidence_bundle(db, event)
    research = synthesize_research(bundle)
    return {"event_id": event_id, **asdict(research)}
