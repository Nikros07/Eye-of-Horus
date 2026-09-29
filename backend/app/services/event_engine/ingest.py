"""Orchestrates one ingestion cycle: connector -> normalize -> verify ->
update DataSource health. Used by both the startup seed and the scheduler.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.event import Event
from app.models.system import DataSource
from app.services.event_engine.connectors.demo_connector import DemoEventConnector
from app.services.event_engine.connectors.nasa_eonet import NasaEonetConnector
from app.services.event_engine.normalizer import upsert_event


def _record_source_status(db: Session, name: str, kind: str, is_demo: bool, ok: bool, latency_ms: float | None, error: str | None) -> None:
    source = db.query(DataSource).filter(DataSource.name == name).one_or_none()
    if source is None:
        source = DataSource(name=name, kind=kind, is_demo=is_demo)
        db.add(source)
    source.status = "online" if ok else ("degraded" if source.status == "online" else "offline")
    source.latency_ms = latency_ms
    source.is_demo = is_demo
    if ok:
        source.last_success_at = datetime.now(timezone.utc)
        source.last_error = None
    else:
        source.last_error = error
    db.flush()


def run_event_ingestion(db: Session) -> list[Event]:
    settings = get_settings()
    events: list[Event] = []

    if settings.data_mode == "demo":
        connector = DemoEventConnector()
        start = time.monotonic()
        try:
            raw_events = connector.fetch()
            for raw in raw_events:
                evidence = connector.fetch_corroborating_evidence(raw)
                events.append(upsert_event(db, raw, evidence))
            _record_source_status(db, connector.name, "event", True, True, (time.monotonic() - start) * 1000, None)
        except Exception as exc:  # noqa: BLE001
            _record_source_status(db, connector.name, "event", True, False, None, str(exc))
        _record_source_status(db, "OPEN_METEO", "weather", True, True, 12.0, None)
        return events

    # live mode: real connectors
    nasa = NasaEonetConnector()
    start = time.monotonic()
    try:
        raw_events = nasa.fetch()
        for raw in raw_events:
            events.append(upsert_event(db, raw, []))
        _record_source_status(db, nasa.name, "event", False, True, (time.monotonic() - start) * 1000, None)
    except Exception as exc:  # noqa: BLE001
        _record_source_status(db, nasa.name, "event", False, False, None, str(exc))

    return events
