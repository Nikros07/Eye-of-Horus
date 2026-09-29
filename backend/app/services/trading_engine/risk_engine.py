"""Risk Engine — every order, in paper or live mode, passes through here
before it reaches a BrokerAdapter. Trading must never be justified by
signal confidence alone; this module is the enforcement point for position
sizing, exposure, drawdown, daily-loss, and cooldown limits, plus the kill
switch. A rejection here is final for that order — there is no override
path from inside a strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.trading import Portfolio, Position, RiskLimitConfig, Trade


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str | None = None
    approved_qty: float | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_risk_config(db: Session, portfolio: Portfolio) -> RiskLimitConfig:
    if portfolio.risk_config is not None:
        return portfolio.risk_config
    config = RiskLimitConfig(portfolio_id=portfolio.id)
    db.add(config)
    db.flush()
    return config


def portfolio_equity(db: Session, portfolio: Portfolio, price_lookup) -> float:
    equity = portfolio.cash
    for pos in portfolio.positions:
        if pos.closed_at is not None:
            continue
        price = price_lookup(pos.asset.symbol) or pos.avg_entry_price
        sign = 1 if pos.side == "long" else -1
        equity += pos.qty * pos.avg_entry_price + pos.qty * (price - pos.avg_entry_price) * sign
    return equity


def daily_pnl(db: Session, portfolio: Portfolio) -> float:
    since = _now() - timedelta(hours=24)
    trades = [t for t in portfolio.trades if t.created_at >= since and t.realized_pnl is not None]
    return sum(t.realized_pnl for t in trades)


def check_order(
    db: Session,
    portfolio: Portfolio,
    asset_symbol: str,
    side: str,
    notional: float,
    current_price: float,
    price_lookup,
) -> RiskCheckResult:
    config = get_or_create_risk_config(db, portfolio)

    if config.kill_switch_active:
        return RiskCheckResult(False, "Kill switch is active for this portfolio.")

    equity = portfolio_equity(db, portfolio, price_lookup)
    if equity <= 0:
        return RiskCheckResult(False, "Portfolio equity is zero or negative.")

    max_position_notional = equity * config.max_position_size_pct
    if notional > max_position_notional:
        notional = max_position_notional  # scale down rather than reject outright

    open_exposure = sum(
        p.qty * (price_lookup(p.asset.symbol) or p.avg_entry_price) for p in portfolio.positions if p.closed_at is None
    )
    if (open_exposure + notional) > equity * config.max_portfolio_exposure_pct:
        return RiskCheckResult(False, f"Order would breach max portfolio exposure ({config.max_portfolio_exposure_pct:.0%}).")

    pnl_today = daily_pnl(db, portfolio)
    if pnl_today < 0 and abs(pnl_today) >= equity * config.max_daily_loss_pct:
        return RiskCheckResult(False, f"Daily loss limit reached ({config.max_daily_loss_pct:.0%} of equity).")

    since_start_of_day = _now() - timedelta(hours=24)
    trades_today = sum(1 for t in portfolio.trades if t.created_at >= since_start_of_day)
    if trades_today >= config.max_trades_per_day:
        return RiskCheckResult(False, f"Max trades per day reached ({config.max_trades_per_day}).")

    initial_capital = portfolio.initial_capital
    if initial_capital > 0:
        drawdown = (initial_capital - equity) / initial_capital
        if drawdown >= config.max_drawdown_pct:
            return RiskCheckResult(False, f"Max drawdown limit reached ({config.max_drawdown_pct:.0%}).")

    last_trade_same_asset = max(
        (t.created_at for t in portfolio.trades if t.asset.symbol == asset_symbol),
        default=None,
    )
    if last_trade_same_asset is not None:
        elapsed = (_now() - last_trade_same_asset).total_seconds()
        if elapsed < config.cooldown_seconds:
            return RiskCheckResult(False, f"Cooldown active for {asset_symbol} ({config.cooldown_seconds}s between trades).")

    if current_price <= 0:
        return RiskCheckResult(False, "Invalid market price.")

    approved_qty = notional / current_price
    return RiskCheckResult(True, approved_qty=approved_qty)


def activate_kill_switch(db: Session, portfolio: Portfolio) -> None:
    config = get_or_create_risk_config(db, portfolio)
    config.kill_switch_active = True
    db.flush()


def deactivate_kill_switch(db: Session, portfolio: Portfolio) -> None:
    config = get_or_create_risk_config(db, portfolio)
    config.kill_switch_active = False
    db.flush()
