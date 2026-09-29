"""Raw connector output -> persisted Event + EvidenceItem rows.

Handles dedup by (source, source_event_id) and keeps first_seen stable while
last_updated tracks the most recent observation, per the provenance model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.event import Event, EvidenceItem
from app.services.event_engine.connectors.base import RawEvent, RawEvidence
from app.services.event_engine.verification import score_verification

_SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_event(db: Session, raw: RawEvent, evidence: list[RawEvidence] | None = None) -> Event:
    existing = (
        db.query(Event)
        .filter(Event.raw_reference.isnot(None))
        .filter(Event.event_type == raw.event_type)
        .all()
    )
    match = next(
        (e for e in existing if e.raw_reference and e.raw_reference.get("source_event_id") == raw.source_event_id and e.raw_reference.get("source") == raw.source),
        None,
    )

    now = _now()
    severity = raw.severity_hint or _severity_from_magnitude(raw.magnitude)

    if match is None:
        event = Event(
            event_type=raw.event_type,
            title=raw.title,
            timestamp=raw.timestamp,
            first_seen=now,
            last_updated=now,
            lat=raw.lat,
            lon=raw.lon,
            location_name=raw.location_name,
            geometry=raw.geometry,
            magnitude=raw.magnitude,
            severity=severity,
            sources=[raw.source],
            verification_status="unverified",
            confidence=0.0,
            source_url=raw.source_url,
            retrieved_at=now,
            publication_time=raw.publication_time,
            availability_time=raw.publication_time or now,
            data_version="v1",
            raw_reference={"source": raw.source, "source_event_id": raw.source_event_id},
            is_demo=raw.is_demo,
        )
        db.add(event)
    else:
        event = match
        event.last_updated = now
        event.title = raw.title
        event.magnitude = raw.magnitude
        event.severity = severity
        if raw.source not in event.sources:
            event.sources = [*event.sources, raw.source]

    db.flush()

    for ev in evidence or []:
        db.add(
            EvidenceItem(
                event_id=event.id,
                kind=ev.kind,
                source=ev.source,
                source_url=ev.source_url,
                content=ev.content,
                strength=ev.strength,
                retrieved_at=now,
                availability_time=ev.availability_time,
                data_version="v1",
                is_demo=ev.is_demo,
            )
        )
    db.flush()

    status, confidence = score_verification(event, list(event.evidence))
    event.verification_status = status
    event.confidence = confidence

    db.flush()
    return event


def _severity_from_magnitude(magnitude: float | None) -> str:
    if magnitude is None:
        return "low"
    if magnitude >= 7:
        return "critical"
    if magnitude >= 5.5:
        return "high"
    if magnitude >= 4:
        return "medium"
    return "low"
