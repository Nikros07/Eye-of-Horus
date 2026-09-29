from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class TradeResult:
    asset_symbol: str
    direction: str
    entry_price: float
    exit_price: float
    qty: float
    fees: float
    pnl: float
    opened_at: str
    closed_at: str
    mfe: float  # max favorable excursion, in price-return terms
    mae: float  # max adverse excursion
    strategy: str
    event_id: int | None


def compute_metrics(trades: list[TradeResult], equity_curve: list[tuple[str, float]], initial_capital: float) -> dict:
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": None,
            "avg_win": None,
            "avg_loss": None,
            "expectancy": None,
            "max_drawdown_pct": _max_drawdown([v for _, v in equity_curve]) if equity_curve else 0.0,
            "total_return_pct": _total_return(equity_curve, initial_capital),
            "sharpe_like": None,
            "avg_mfe": None,
            "avg_mae": None,
        }

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    win_rate = len(wins) / len(trades)
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    equity_values = [v for _, v in equity_curve] if equity_curve else [initial_capital]
    returns = _period_returns(equity_values)
    sharpe_like = _sharpe_like(returns)

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown_pct": round(_max_drawdown(equity_values), 4),
        "total_return_pct": round(_total_return(equity_curve, initial_capital), 4),
        "sharpe_like": round(sharpe_like, 3) if sharpe_like is not None else None,
        "avg_mfe": round(sum(t.mfe for t in trades) / len(trades), 4),
        "avg_mae": round(sum(t.mae for t in trades) / len(trades), 4),
        "total_fees": round(sum(t.fees for t in trades), 2),
    }


def _total_return(equity_curve: list[tuple[str, float]], initial_capital: float) -> float:
    if not equity_curve:
        return 0.0
    final = equity_curve[-1][1]
    return (final - initial_capital) / initial_capital if initial_capital else 0.0


def _max_drawdown(equity_values: list[float]) -> float:
    if not equity_values:
        return 0.0
    peak = equity_values[0]
    max_dd = 0.0
    for v in equity_values:
        peak = max(peak, v)
        if peak > 0:
            max_dd = max(max_dd, (peak - v) / peak)
    return max_dd


def _period_returns(equity_values: list[float]) -> list[float]:
    rets = []
    for i in range(1, len(equity_values)):
        prev = equity_values[i - 1]
        if prev:
            rets.append((equity_values[i] - prev) / prev)
    return rets


def _sharpe_like(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var)
    if std == 0:
        return None
    return (mean / std) * math.sqrt(len(returns))
