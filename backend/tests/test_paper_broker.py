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


def test_two_buys_of_the_same_asset_in_one_session_merge_into_one_position(db_session):
    """Regression test: within a single db session — exactly what happens
    when the auto-trade cycle executes several signals for the same asset
    back-to-back with no commit in between — a second buy of an asset
    already held must add to the existing position, not silently open a
    second, duplicate Position row because the existing-position lookup
    used the ORM's cached `portfolio.positions` collection, which does not
    see a position added earlier in the very same session/flush."""
    portfolio, broker = _setup(db_session)

    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=10))
    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=5))
    db_session.commit()

    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].qty == 15


def test_close_position_realizes_pnl(db_session):
    _, broker = _setup(db_session)
    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=10))
    db_session.commit()

    close_order = broker.close_position("CL=F")
    db_session.commit()

    assert close_order is not None
    assert close_order.status == "filled"
    assert broker.get_positions() == []


def test_negative_qty_buy_is_rejected_not_credited_as_free_cash(db_session):
    """Regression test: place_order used to have no qty > 0 guard. A "buy"
    with a negative qty made `cost = qty * fill_price + fees` negative,
    which passed the `cost > cash` check and then *increased* cash via
    `cash -= cost` — a negative-qty order minted free paper cash."""
    portfolio, broker = _setup(db_session)
    starting_cash = portfolio.cash

    order = broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=-1000))

    assert order.status.startswith("rejected")
    assert portfolio.cash == starting_cash
    assert broker.get_positions() == []


def test_zero_qty_order_is_rejected(db_session):
    _, broker = _setup(db_session)
    order = broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=0))
    assert order.status.startswith("rejected")


def test_two_buys_in_the_same_uncommitted_session_accumulate_into_one_position(db_session):
    """Regression test: PaperBroker used to attach new Position/Trade rows to
    the portfolio via `portfolio_id=` alone, which never updates the
    in-memory `portfolio.positions`/`portfolio.trades` collections. Two
    signals for the same asset in one auto-trade cycle (no commit between
    them) would each see zero existing positions and each open a separate
    Position row instead of accumulating into one — and risk checks reading
    `portfolio.trades` (cooldown, max_trades_per_day, daily_pnl) would stay
    blind to trades placed earlier in the same cycle."""
    portfolio, broker = _setup(db_session)

    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=10))
    broker.place_order(OrderRequest(asset_symbol="CL=F", side="buy", qty=5))

    assert len(portfolio.trades) == 2
    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].qty == 15
