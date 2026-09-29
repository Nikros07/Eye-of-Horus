from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.serializers import serialize_position, serialize_trade
from app.core.db import get_db
from app.models.trading import Portfolio
from app.services.market_engine.factory import get_market_source
from app.services.trading_engine.risk_engine import daily_pnl, portfolio_equity

router = APIRouter()


def _get_portfolio(db: Session) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one_or_none()
    if portfolio is None:
        raise HTTPException(404, "No portfolio found")
    return portfolio


@router.get("")
def get_portfolio_summary(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    market_source = get_market_source()
    price_lookup = lambda sym: market_source.get_quote(sym).price  # noqa: E731

    equity = portfolio_equity(db, portfolio, price_lookup)
    open_positions = [p for p in portfolio.positions if p.closed_at is None]
    exposure = sum(p.qty * (price_lookup(p.asset.symbol) or p.avg_entry_price) for p in open_positions)

    return {
        "name": portfolio.name,
        "mode": portfolio.mode,
        "cash": round(portfolio.cash, 2),
        "equity": round(equity, 2),
        "initial_capital": portfolio.initial_capital,
        "total_return_pct": round((equity - portfolio.initial_capital) / portfolio.initial_capital, 4) if portfolio.initial_capital else 0.0,
        "daily_pnl": round(daily_pnl(db, portfolio), 2),
        "open_exposure": round(exposure, 2),
        "exposure_pct": round(exposure / equity, 4) if equity else 0.0,
        "open_position_count": len(open_positions),
        "positions": [serialize_position(p, price_lookup(p.asset.symbol)) for p in open_positions],
    }


@router.get("/trades")
def get_trades(db: Session = Depends(get_db), limit: int = 50):
    portfolio = _get_portfolio(db)
    trades = sorted(portfolio.trades, key=lambda t: t.created_at, reverse=True)[:limit]
    return [serialize_trade(t) for t in trades]


@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    closed_trades = sorted(
        [t for t in portfolio.trades if t.realized_pnl is not None],
        key=lambda t: t.created_at,
    )

    equity_curve = []
    running = portfolio.initial_capital
    for t in closed_trades:
        running += t.realized_pnl
        equity_curve.append({"ts": t.created_at.isoformat(), "equity": round(running, 2)})

    wins = [t for t in closed_trades if t.realized_pnl > 0]
    losses = [t for t in closed_trades if t.realized_pnl <= 0]
    win_rate = len(wins) / len(closed_trades) if closed_trades else None

    peak = portfolio.initial_capital
    max_dd = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        if peak > 0:
            max_dd = max(max_dd, (peak - point["equity"]) / peak)

    return {
        "equity_curve": equity_curve,
        "closed_trade_count": len(closed_trades),
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "avg_win": round(sum(t.realized_pnl for t in wins) / len(wins), 2) if wins else None,
        "avg_loss": round(sum(t.realized_pnl for t in losses) / len(losses), 2) if losses else None,
        "max_drawdown_pct": round(max_dd, 4),
        "total_fees": round(sum(t.fees for t in portfolio.trades), 2),
    }
