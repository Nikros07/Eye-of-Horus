from __future__ import annotations

from app.models.trading import Portfolio, Trade
from app.services.bootstrap import ensure_demo_data_seeded
from app.services.trading_engine.auto_trade import run_auto_trade_cycle, run_auto_trade_for_portfolio


def test_auto_trade_disabled_by_default_does_nothing(db_session):
    ensure_demo_data_seeded()
    portfolio = db_session.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one()
    assert portfolio.auto_trade_enabled is False

    outcomes = run_auto_trade_for_portfolio(db_session, portfolio)
    assert outcomes == []
    assert db_session.query(Trade).count() == 0


def test_enabling_auto_trade_executes_fresh_signals(db_session):
    ensure_demo_data_seeded()
    portfolio = db_session.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one()
    portfolio.auto_trade_enabled = True
    portfolio.auto_trade_min_confidence = 0.0  # accept anything for this test
    db_session.commit()

    outcomes = run_auto_trade_cycle(db_session)
    db_session.commit()

    assert len(outcomes) > 0
    # every bullish outcome should have produced a real trade row (bearish
    # signals with no existing long position are correctly rejected — no
    # short-selling in this MVP, per PaperBroker)
    approved = [o for o in outcomes if o.approved]
    assert len(approved) > 0
    assert db_session.query(Trade).count() >= len(approved)


def test_auto_trade_never_repeats_the_same_signal(db_session):
    ensure_demo_data_seeded()
    portfolio = db_session.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one()
    portfolio.auto_trade_enabled = True
    portfolio.auto_trade_min_confidence = 0.0
    db_session.commit()

    run_auto_trade_cycle(db_session)
    db_session.commit()
    trades_after_first_cycle = db_session.query(Trade).count()

    second_outcomes = run_auto_trade_cycle(db_session)
    db_session.commit()

    # nothing new to trade (every eligible signal was already acted on)
    assert second_outcomes == []
    assert db_session.query(Trade).count() == trades_after_first_cycle


def test_research_mode_portfolio_never_auto_trades(db_session):
    ensure_demo_data_seeded()
    portfolio = db_session.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one()
    portfolio.mode = "research"
    portfolio.auto_trade_enabled = True
    portfolio.auto_trade_min_confidence = 0.0
    db_session.commit()

    outcomes = run_auto_trade_for_portfolio(db_session, portfolio)
    assert outcomes == []
