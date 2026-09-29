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
from app.services.event_engine.connectors.base import RawEvent, RawEvidence
from app.services.event_engine.connectors.demo_connector import DemoEventConnector
from app.services.event_engine.connectors.nasa_eonet import NasaEonetConnector
from app.services.event_engine.connectors.open_meteo import OpenMeteoConnector
from app.services.event_engine.normalizer import upsert_event

# Event types Open-Meteo's current-conditions endpoint can plausibly
# corroborate. Mirrors the weather-triggering set in the demo connector.
WEATHER_SENSITIVE_EVENT_TYPES = {"flood", "drought", "extreme_weather", "wildfire", "hurricane"}


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
    meteo = OpenMeteoConnector()
    meteo_calls: list[str | None] = []  # one entry per call attempted: error message, or None on success
    start = time.monotonic()
    try:
        raw_events = nasa.fetch()
        for raw in raw_events:
            evidence = _corroborate_with_weather(meteo, raw, meteo_calls)
            events.append(upsert_event(db, raw, evidence))
        _record_source_status(db, nasa.name, "event", False, True, (time.monotonic() - start) * 1000, None)
    except Exception as exc:  # noqa: BLE001
        _record_source_status(db, nasa.name, "event", False, False, None, str(exc))

    if meteo_calls:
        _record_source_status(db, meteo.name, "weather", False, meteo_calls[-1] is None, None, meteo_calls[-1])

    return events


def _corroborate_with_weather(meteo: OpenMeteoConnector, raw: RawEvent, meteo_calls: list[str | None]) -> list[RawEvidence]:
    """Best-effort weather corroboration for a live-ingested event: a failed
    Open-Meteo call never blocks ingestion of the underlying event, it just
    leaves that event with no weather evidence."""
    if raw.event_type not in WEATHER_SENSITIVE_EVENT_TYPES:
        return []
    try:
        item = meteo.fetch_current(raw.lat, raw.lon)
        meteo_calls.append(None)
        return [item] if item else []
    except Exception as exc:  # noqa: BLE001
        meteo_calls.append(str(exc))
        return []
