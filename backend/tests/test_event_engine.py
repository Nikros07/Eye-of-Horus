from __future__ import annotations

from datetime import datetime, timezone

from app.models.event import Event
from app.models.system import DataSource
from app.services.event_engine.connectors.base import RawEvent, RawEvidence
from app.services.event_engine.connectors.demo_connector import DemoEventConnector
from app.services.event_engine.connectors.nasa_eonet import NasaEonetConnector
from app.services.event_engine.connectors.open_meteo import OpenMeteoConnector
from app.services.event_engine.normalizer import upsert_event
from app.services.event_engine.verification import score_verification


def test_demo_connector_produces_events_with_provenance():
    connector = DemoEventConnector()
    events = connector.fetch()
    assert len(events) > 0
    for e in events:
        assert e.is_demo is True
        assert e.source == "DEMO_GENERATOR"
        assert e.publication_time is not None


def test_corroborating_evidence_is_deterministic_across_processes():
    """Regression test: fetch_corroborating_evidence used Python's builtin
    hash() on a string to seed its RNG, which is randomized per-process
    (PYTHONHASHSEED) and so silently broke the "deterministic ... for tests
    and for the backtester" guarantee the module promises. Runs the same
    generation in two subprocesses with different hash seeds and checks
    their output is byte-for-byte identical."""
    import os
    import subprocess
    import sys

    script = (
        "from app.services.event_engine.connectors.demo_connector import DemoEventConnector\n"
        "from datetime import datetime, timezone\n"
        "c = DemoEventConnector(now=datetime(2026, 1, 1, tzinfo=timezone.utc))\n"
        "raw = c.fetch()[0]\n"
        "for e in c.fetch_corroborating_evidence(raw):\n"
        "    print(e.content)\n"
    )

    def run_with_hash_seed(seed: str) -> str:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, check=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        return result.stdout

    output_seed_1 = run_with_hash_seed("1")
    output_seed_2 = run_with_hash_seed("2")
    assert output_seed_1 == output_seed_2
    assert output_seed_1.strip() != ""


def test_upsert_event_dedupes_by_source_and_source_event_id(db_session):
    connector = DemoEventConnector()
    raw = connector.fetch()[0]

    first = upsert_event(db_session, raw, connector.fetch_corroborating_evidence(raw))
    db_session.commit()
    second = upsert_event(db_session, raw, [])
    db_session.commit()

    assert first.id == second.id
    assert db_session.query(Event).count() == 1


def test_verification_status_improves_with_corroboration(db_session):
    connector = DemoEventConnector()
    raw = connector.fetch()[0]  # flood -> has weather + news evidence

    event = upsert_event(db_session, raw, connector.fetch_corroborating_evidence(raw))
    db_session.commit()

    assert event.confidence > 0.35  # above the bare single-source floor
    assert event.verification_status in ("pending", "verified")


def test_score_verification_flags_unverified_with_no_evidence():
    class FakeEvent:
        sources = ["ONE_SOURCE"]

    status, confidence = score_verification(FakeEvent(), [])
    assert status == "unverified"
    assert confidence == 0.38


def test_live_ingestion_corroborates_weather_sensitive_events_with_open_meteo(db_session, monkeypatch):
    """Regression test: config.py documents that DATA_MODE=live calls NASA
    EONET AND Open-Meteo, but OpenMeteoConnector was never actually wired
    into the live ingestion path. A weather-sensitive event should come out
    with Open-Meteo evidence attached; an event type Open-Meteo can't
    corroborate should not trigger a call at all."""
    import app.services.event_engine.ingest as ingest_module

    now = datetime.now(timezone.utc)
    raw_flood = RawEvent(
        source_event_id="EONET-1", event_type="flood", title="Flood", timestamp=now,
        lat=10.0, lon=20.0, source="NASA_EONET", publication_time=now,
    )
    raw_earthquake = RawEvent(
        source_event_id="EONET-2", event_type="earthquake", title="Earthquake", timestamp=now,
        lat=30.0, lon=40.0, source="NASA_EONET", publication_time=now,
    )

    monkeypatch.setattr(ingest_module, "get_settings", lambda: type("S", (), {"data_mode": "live"})())
    monkeypatch.setattr(NasaEonetConnector, "fetch", lambda self, since=None: [raw_flood, raw_earthquake])

    calls: list[tuple[float, float]] = []

    def fake_fetch_current(self, lat: float, lon: float) -> RawEvidence:
        calls.append((lat, lon))
        return RawEvidence(kind="weather", source="OPEN_METEO", content="synthetic", availability_time=now)

    monkeypatch.setattr(OpenMeteoConnector, "fetch_current", fake_fetch_current)

    events = ingest_module.run_event_ingestion(db_session)
    db_session.commit()

    assert calls == [(10.0, 20.0)]  # only the weather-sensitive event triggered a call
    by_type = {e.event_type: e for e in events}
    assert len(by_type["flood"].evidence) == 1
    assert by_type["flood"].evidence[0].kind == "weather"
    assert len(by_type["earthquake"].evidence) == 0

    meteo_source = db_session.query(DataSource).filter(DataSource.name == "OPEN_METEO").one()
    assert meteo_source.status == "online"
    assert meteo_source.is_demo is False
