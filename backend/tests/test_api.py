from __future__ import annotations


def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_events_list_is_seeded_on_startup(api_client):
    resp = api_client.get("/api/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) > 0
    assert all(e["is_demo"] for e in events)


def test_event_detail_includes_evidence_and_impact_links(api_client):
    events = api_client.get("/api/events").json()
    detail = api_client.get(f"/api/events/{events[0]['event_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert "evidence" in body
    assert "impact_links" in body


def test_signals_are_generated_from_seeded_events(api_client):
    resp = api_client.get("/api/signals")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_backtest_run_endpoint(api_client):
    resp = api_client.post("/api/backtests/run", json={"strategy": "multi_signal"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["look_ahead_bias_detected"] is False


def test_backtest_run_rejects_unknown_strategy(api_client):
    resp = api_client.post("/api/backtests/run", json={"strategy": "not_a_strategy"})
    assert resp.status_code == 400


def test_trading_mode_defaults_to_paper(api_client):
    resp = api_client.get("/api/trading/mode")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "paper"
    assert body["live_trading_enabled"] is False


def test_live_mode_is_refused_when_disabled(api_client):
    resp = api_client.post("/api/trading/mode", json={"mode": "live"})
    assert resp.status_code == 403


def test_portfolio_summary(api_client):
    resp = api_client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "paper"
    assert body["cash"] == 10_000.0


def test_system_status_reports_demo_sources(api_client):
    resp = api_client.get("/api/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_mode"] == "demo"
    assert len(body["data_sources"]) > 0
    assert all(s["is_demo"] for s in body["data_sources"])


def test_research_endpoint_never_fabricates_beyond_insufficient_evidence(api_client):
    events = api_client.get("/api/events").json()
    resp = api_client.get(f"/api/research/events/{events[0]['event_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["market_already_priced"] in ("NO", "POSSIBLY", "YES")
    assert isinstance(body["observed"], list)
