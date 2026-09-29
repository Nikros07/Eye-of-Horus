from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.backtest import Backtest
from app.services.quant_engine.backtester import BacktestParams, run_backtest


def run_and_store_backtest(db: Session, params: BacktestParams) -> Backtest:
    row = Backtest(
        strategy=params.strategy_name,
        asset_symbols=params.asset_symbols or [],
        period_start=params.period_start,
        period_end=params.period_end,
        initial_capital=params.initial_capital,
        risk_params={"max_position_pct": params.max_position_pct},
        transaction_cost_bps=params.transaction_cost_bps,
        slippage_bps=params.slippage_bps,
        status="running",
    )
    db.add(row)
    db.flush()

    result = run_backtest(db, params)

    row.status = "failed" if result.error and result.look_ahead_bias_detected else "completed"
    row.metrics = result.metrics
    row.equity_curve = [{"ts": ts, "equity": eq} for ts, eq in result.equity_curve]
    row.trades = [asdict(t) for t in result.trades]
    row.signal_stats = result.signal_stats
    row.look_ahead_bias_detected = result.look_ahead_bias_detected
    row.error = result.error
    row.completed_at = datetime.now(timezone.utc)

    db.flush()
    return row


def compare_strategies(db: Session, strategy_names: list[str], base_params: BacktestParams) -> list[dict]:
    comparisons = []
    for name in strategy_names:
        params = BacktestParams(**{**base_params.__dict__, "strategy_name": name})
        result = run_backtest(db, params)
        comparisons.append(
            {
                "strategy": name,
                "metrics": result.metrics,
                "signal_stats": result.signal_stats,
                "look_ahead_bias_detected": result.look_ahead_bias_detected,
                "error": result.error,
            }
        )
    return comparisons
