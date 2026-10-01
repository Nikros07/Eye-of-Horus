from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.models.market import Asset
from app.models.trading import Portfolio
from app.services.trading_engine.alpaca_broker import AlpacaBroker, AlpacaNotConfiguredError
from app.services.trading_engine.broker_base import OrderRequest


def _setup(db_session) -> tuple[Portfolio, Asset]:
    portfolio = Portfolio(name="Test", mode="paper", cash=10_000, initial_capital=10_000)
    db_session.add(portfolio)
    asset = Asset(symbol="AAPL", name="Apple", asset_class="equity", currency="USD")
    db_session.add(asset)
    db_session.commit()
    return portfolio, asset


def _configured_settings():
    return SimpleNamespace(alpaca_api_key="test-key", alpaca_secret_key="test-secret")


def test_raises_when_not_configured(db_session):
    portfolio, _ = _setup(db_session)
    with pytest.raises(AlpacaNotConfiguredError):
        AlpacaBroker(db_session, portfolio)


def _broker_with_mock_transport(db_session, portfolio, monkeypatch, handler) -> AlpacaBroker:
    monkeypatch.setattr(
        "app.services.trading_engine.alpaca_broker.get_settings",
        _configured_settings,
    )
    broker = AlpacaBroker(db_session, portfolio)
    broker._client = httpx.Client(
        base_url="https://paper-api.alpaca.markets",
        headers=broker._client.headers,
        transport=httpx.MockTransport(handler),
    )
    return broker


def test_buy_places_order_records_local_trade_and_syncs_ledger(db_session, monkeypatch):
    portfolio, _ = _setup(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/orders":
            return httpx.Response(200, json={"id": "order-1", "status": "filled", "symbol": "AAPL", "side": "buy",
                                              "qty": "10", "type": "market", "filled_avg_price": "190.0",
                                              "submitted_at": "2026-01-01T00:00:00Z"})
        if request.method == "GET" and request.url.path == "/v2/orders/order-1":
            return httpx.Response(200, json={"id": "order-1", "status": "filled", "symbol": "AAPL", "side": "buy",
                                              "qty": "10", "type": "market", "filled_avg_price": "190.0",
                                              "submitted_at": "2026-01-01T00:00:00Z"})
        if request.method == "GET" and request.url.path == "/v2/account":
            return httpx.Response(200, json={"cash": "8100.0", "portfolio_value": "10000.0", "buying_power": "8100.0"})
        if request.method == "GET" and request.url.path == "/v2/positions":
            return httpx.Response(200, json=[{"symbol": "AAPL", "qty": "10", "avg_entry_price": "190.0",
                                               "current_price": "190.0", "unrealized_pl": "0.0"}])
        raise AssertionError(f"unexpected request {request.method} {request.url.path}")

    broker = _broker_with_mock_transport(db_session, portfolio, monkeypatch, handler)
    order = broker.place_order(OrderRequest(asset_symbol="AAPL", side="buy", qty=10))
    db_session.commit()

    assert order.status == "filled"
    assert order.filled_price == 190.0
    assert portfolio.cash == 8100.0
    assert len(portfolio.trades) == 1
    assert portfolio.trades[0].qty == 10
    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].qty == 10


def test_rejected_order_does_not_touch_local_state(db_session, monkeypatch):
    portfolio, _ = _setup(db_session)
    starting_cash = portfolio.cash

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/orders":
            return httpx.Response(403, json={"message": "insufficient buying power"})
        raise AssertionError(f"unexpected request {request.method} {request.url.path}")

    broker = _broker_with_mock_transport(db_session, portfolio, monkeypatch, handler)
    order = broker.place_order(OrderRequest(asset_symbol="AAPL", side="buy", qty=10))

    assert order.status.startswith("rejected")
    assert "insufficient buying power" in order.status
    assert portfolio.cash == starting_cash
    assert len(portfolio.trades) == 0


def test_non_positive_qty_is_rejected_without_a_network_call(db_session, monkeypatch):
    portfolio, _ = _setup(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should never reach the network for a non-positive qty")

    broker = _broker_with_mock_transport(db_session, portfolio, monkeypatch, handler)
    order = broker.place_order(OrderRequest(asset_symbol="AAPL", side="buy", qty=0))
    assert order.status.startswith("rejected")


def test_get_account_maps_alpaca_fields(db_session, monkeypatch):
    portfolio, _ = _setup(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/account"
        return httpx.Response(200, json={"cash": "5000.0", "portfolio_value": "12000.0", "buying_power": "9000.0"})

    broker = _broker_with_mock_transport(db_session, portfolio, monkeypatch, handler)
    account = broker.get_account()
    assert account.cash == 5000.0
    assert account.equity == 12000.0
    assert account.buying_power == 9000.0
    assert account.mode == "paper"
