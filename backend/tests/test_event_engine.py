from __future__ import annotations

from app.models.event import Event
from app.services.event_engine.connectors.demo_connector import DemoEventConnector
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
