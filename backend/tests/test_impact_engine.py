from __future__ import annotations

from app.services.event_engine.connectors.demo_connector import DemoEventConnector
from app.services.event_engine.normalizer import upsert_event
from app.services.impact_engine.graph import build_impact_links, compute_exposure
from app.services.impact_engine.rules import rules_for


def test_rules_exist_for_every_demo_scenario_event_type():
    connector = DemoEventConnector()
    for raw in connector.fetch():
        assert rules_for(raw.event_type), f"no impact rule for {raw.event_type}"


def test_build_impact_links_sets_event_exposure_and_chain(db_session):
    connector = DemoEventConnector()
    raw = next(r for r in connector.fetch() if r.event_type == "flood")
    event = upsert_event(db_session, raw, connector.fetch_corroborating_evidence(raw))
    db_session.commit()

    links = build_impact_links(db_session, event)
    db_session.commit()

    assert len(links) > 0
    assert event.affected_assets == sorted({l.asset_symbol for l in links})
    for link in links:
        assert link.chain[0]["type"] == "event"
        assert link.chain[-1]["type"] == "market"
        assert 0.0 <= link.exposure_score <= 1.0
        assert link.direction in ("bullish", "bearish")


def test_compute_exposure_scales_with_confidence_and_severity():
    class FakeEvent:
        confidence = 0.9
        severity = "critical"

    high = compute_exposure(0.5, FakeEvent())

    class LowEvent:
        confidence = 0.1
        severity = "low"

    low = compute_exposure(0.5, LowEvent())
    assert high > low
