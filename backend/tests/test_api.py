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


def test_compare_rejects_empty_strategy_list_instead_of_500(api_client):
    """An empty `strategies` list used to reach req.strategies[0] unchecked
    and raise an unhandled IndexError (a raw 500), instead of the clean
    4xx every other bad-input case on this endpoint gets."""
    resp = api_client.post("/api/backtests/compare", json={"strategies": []})
    assert resp.status_code == 400
    assert "non-empty" in resp.json()["detail"]


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


def test_manual_order_rejects_non_positive_qty(api_client):
    resp = api_client.post("/api/trading/orders", json={"asset_symbol": "CL=F", "side": "buy", "qty": -10})
    assert resp.status_code == 422


def test_manual_order_rejects_invalid_side(api_client):
    """PaperBroker treats anything other than exactly "buy" as a sell, so
    an unvalidated side would let a typo silently execute the opposite
    side instead of failing loudly."""
    resp = api_client.post("/api/trading/orders", json={"asset_symbol": "CL=F", "side": "purchase", "qty": 1})
    assert resp.status_code == 422


def test_kill_switch_blocks_manual_order(api_client):
    """The kill switch must block every order path, not just signal-driven
    execution — a manual click bypassing it entirely (as the /api/trading/orders
    endpoint previously did, calling the broker directly instead of going
    through RiskEngine.check_order) would defeat the whole point of a kill
    switch."""
    activate = api_client.post("/api/risk/kill-switch", params={"active": True})
    assert activate.status_code == 200
    assert activate.json()["kill_switch_active"] is True

    resp = api_client.post("/api/trading/orders", json={"asset_symbol": "CL=F", "side": "buy", "qty": 1})
    assert resp.status_code == 403
    assert "Kill switch" in resp.json()["detail"]


def test_kill_switch_blocks_position_close(api_client):
    """Same guarantee as above for closing an existing position — it must
    still be gated by RiskEngine.check_order, not sent straight to the
    broker."""
    deactivate = api_client.post("/api/risk/kill-switch", params={"active": False})
    assert deactivate.status_code == 200

    opened = api_client.post("/api/trading/orders", json={"asset_symbol": "CL=F", "side": "buy", "qty": 1})
    assert opened.status_code == 200
    assert opened.json()["status"] == "filled"

    api_client.post("/api/risk/kill-switch", params={"active": True})

    resp = api_client.post("/api/trading/positions/CL=F/close")
    assert resp.status_code == 403
    assert "Kill switch" in resp.json()["detail"]


def test_manual_order_rejected_when_it_would_breach_max_exposure(api_client):
    """RiskEngine.check_order's exposure limit must apply to a manual order
    exactly like it applies to a signal-driven one."""
    api_client.put("/api/risk", json={"max_portfolio_exposure_pct": 0.0001})

    resp = api_client.post("/api/trading/orders", json={"asset_symbol": "CL=F", "side": "buy", "qty": 100})
    assert resp.status_code == 403
    assert "exposure" in resp.json()["detail"]


def test_risk_limit_update_rejects_a_negative_daily_loss_pct(api_client):
    """Regression test: a negative max_daily_loss_pct makes
    risk_engine.check_order's daily-loss guard unsatisfiable (abs(pnl) is
    never >= a negative bound), silently disabling it — must be rejected
    at the API boundary instead of silently accepted."""
    resp = api_client.put("/api/risk", json={"max_daily_loss_pct": -1})
    assert resp.status_code == 422


def test_risk_limit_update_accepts_a_valid_change(api_client):
    resp = api_client.put("/api/risk", json={"max_position_size_pct": 0.25})
    assert resp.status_code == 200
    snapshot = api_client.get("/api/risk").json()
    assert snapshot["limits"]["max_position_size_pct"] == 0.25


def test_research_endpoint_never_fabricates_beyond_insufficient_evidence(api_client):
    events = api_client.get("/api/events").json()
    resp = api_client.get(f"/api/research/events/{events[0]['event_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["market_already_priced"] in ("NO", "POSSIBLY", "YES")
    assert isinstance(body["observed"], list)
