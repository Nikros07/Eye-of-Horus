from __future__ import annotations

from app.models.trading import Portfolio
from app.services.trading_engine.risk_engine import (
    activate_kill_switch,
    check_order,
    get_or_create_risk_config,
)


def _price_lookup(_symbol: str) -> float:
    return 100.0


def test_kill_switch_blocks_all_orders(db_session):
    portfolio = Portfolio(name="Test", mode="paper", cash=10_000, initial_capital=10_000)
    db_session.add(portfolio)
    db_session.flush()
    activate_kill_switch(db_session, portfolio)
    db_session.commit()

    result = check_order(db_session, portfolio, "CL=F", "buy", 500, 100.0, _price_lookup)
    assert result.approved is False
    assert "Kill switch" in result.reason


def test_order_within_limits_is_approved(db_session):
    portfolio = Portfolio(name="Test", mode="paper", cash=10_000, initial_capital=10_000)
    db_session.add(portfolio)
    db_session.flush()
    get_or_create_risk_config(db_session, portfolio)
    db_session.commit()

    result = check_order(db_session, portfolio, "CL=F", "buy", 500, 100.0, _price_lookup)
    assert result.approved is True
    assert result.approved_qty == 5.0


def test_order_exceeding_max_exposure_is_rejected(db_session):
    portfolio = Portfolio(name="Test", mode="paper", cash=10_000, initial_capital=10_000)
    db_session.add(portfolio)
    db_session.flush()
    config = get_or_create_risk_config(db_session, portfolio)
    config.max_portfolio_exposure_pct = 0.05  # very tight
    db_session.commit()

    result = check_order(db_session, portfolio, "CL=F", "buy", 5_000, 100.0, _price_lookup)
    assert result.approved is False
    assert "exposure" in result.reason
