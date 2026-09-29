from __future__ import annotations

from app.models.market import Asset
from app.models.trading import Portfolio
from app.services.market_engine.demo_adapter import DemoMarketSource
from app.services.trading_engine.broker_base import OrderRequest
from app.services.trading_engine.paper_broker import PaperBroker


def _setup(db_session) -> tuple[Portfolio, PaperBroker]:
    portfolio = Portfolio(name="Test", mode="paper", cash=10_000, initial_capital=10_000)
    db_session.add(portfolio)
    asset = Asset(symbol="CL=F", name="Crude Oil WTI", asset_class="energy", currency="USD")
    db_session.add(asset)
    db_session.commit()
    broker = PaperBroker(db_session, portfolio, DemoMarketSource())
    return portfolio, broker


def test_buy_opens_a_long_position_and_debits_cash(db_session):
    portfolio, broker = _setup(db_session)
    starting_cash = portfolio.cash

    order = broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=10))
    db_session.commit()

    assert order.status == "filled"
    assert portfolio.cash < starting_cash
    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].side == "long"
    assert positions[0].qty == 10


def test_sell_without_position_is_rejected_not_short(db_session):
    _, broker = _setup(db_session)
    order = broker.place_order(OrderRequest(asset_symbol="CL=F", side="sell", qty=5))
    assert order.status.startswith("rejected")


def test_buy_exceeding_cash_is_rejected(db_session):
    portfolio, broker = _setup(db_session)
    portfolio.cash = 10.0  # not enough for any meaningful qty at ~$78/barrel
    order = broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=100))
    assert order.status.startswith("rejected")


def test_close_position_realizes_pnl(db_session):
    _, broker = _setup(db_session)
    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=10))
    db_session.commit()

    close_order = broker.close_position("CL=F")
    db_session.commit()

    assert close_order is not None
    assert close_order.status == "filled"
    assert broker.get_positions() == []
