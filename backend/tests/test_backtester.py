from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.bootstrap import ensure_demo_data_seeded
from app.services.quant_engine.backtester import BacktestParams, run_backtest
from app.services.quant_engine.service import compare_strategies, run_and_store_backtest
from app.services.signal_engine.registry import STRATEGY_REGISTRY


def _params(strategy: str) -> BacktestParams:
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=30)
    return BacktestParams(strategy_name=strategy, period_start=period_start, period_end=period_end)


def test_backtest_runs_for_every_registered_strategy(db_session):
    ensure_demo_data_seeded()
    for name in STRATEGY_REGISTRY:
        result = run_backtest(db_session, _params(name))
        assert result.error is None
        assert result.look_ahead_bias_detected is False
        assert "total_trades" in result.metrics
        assert result.equity_curve[0][1] == 10_000.0  # starts at initial capital


def test_unknown_strategy_returns_error_not_exception(db_session):
    ensure_demo_data_seeded()
    result = run_backtest(db_session, _params("does_not_exist"))
    assert result.error is not None
    assert result.look_ahead_bias_detected is False


def test_run_and_store_backtest_persists_row(db_session):
    ensure_demo_data_seeded()
    row = run_and_store_backtest(db_session, _params("multi_signal"))
    db_session.commit()
    assert row.id is not None
    assert row.status == "completed"
    assert isinstance(row.trades, list)


def test_run_and_store_backtest_marks_unknown_strategy_as_failed(db_session):
    """Regression test: a backtest that errors out (any error, not just a
    look-ahead bias violation) must be persisted with status="failed", not
    silently marked "completed" with empty results."""
    ensure_demo_data_seeded()
    row = run_and_store_backtest(db_session, _params("does_not_exist"))
    db_session.commit()
    assert row.status == "failed"
    assert row.error is not None


def test_baseline_is_included_in_strategy_comparison(db_session):
    ensure_demo_data_seeded()
    rows = compare_strategies(db_session, ["multi_signal", "baseline_trend"], _params("multi_signal"))
    names = {r["strategy"] for r in rows}
    assert names == {"multi_signal", "baseline_trend"}
    for r in rows:
        assert r["look_ahead_bias_detected"] is False
