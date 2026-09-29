from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_main_portfolio
from app.core.db import get_db
from app.services.market_engine.factory import get_market_source
from app.services.trading_engine.risk_engine import (
    activate_kill_switch,
    daily_pnl,
    deactivate_kill_switch,
    get_or_create_risk_config,
    open_exposure,
    open_positions,
    portfolio_equity,
)

router = APIRouter()


class RiskLimitUpdate(BaseModel):
    max_position_size_pct: float | None = None
    max_daily_loss_pct: float | None = None
    max_portfolio_exposure_pct: float | None = None
    max_trades_per_day: int | None = None
    max_drawdown_pct: float | None = None
    cooldown_seconds: int | None = None


@router.get("")
def get_risk_snapshot(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    config = get_or_create_risk_config(db, portfolio)
    market_source = get_market_source()
    price_lookup = market_source.get_price

    equity = portfolio_equity(db, portfolio, price_lookup)
    positions = open_positions(portfolio)
    exposure = open_exposure(portfolio, price_lookup)
    drawdown = (portfolio.initial_capital - equity) / portfolio.initial_capital if portfolio.initial_capital else 0.0

    return {
        "limits": {
            "max_position_size_pct": config.max_position_size_pct,
            "max_daily_loss_pct": config.max_daily_loss_pct,
            "max_portfolio_exposure_pct": config.max_portfolio_exposure_pct,
            "max_trades_per_day": config.max_trades_per_day,
            "max_drawdown_pct": config.max_drawdown_pct,
            "cooldown_seconds": config.cooldown_seconds,
        },
        "kill_switch_active": config.kill_switch_active,
        "current": {
            "equity": round(equity, 2),
            "open_exposure": round(exposure, 2),
            "exposure_pct": round(exposure / equity, 4) if equity else 0.0,
            "current_drawdown_pct": round(max(drawdown, 0.0), 4),
            "daily_pnl": round(daily_pnl(db, portfolio), 2),
            "position_concentration": {
                p.asset.symbol: round((p.qty * (price_lookup(p.asset.symbol) or p.avg_entry_price)) / exposure, 4)
                for p in positions
            }
            if exposure
            else {},
        },
    }


@router.put("")
def update_risk_limits(req: RiskLimitUpdate, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    config = get_or_create_risk_config(db, portfolio)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(config, field, value)
    db.commit()
    return {"status": "updated"}


@router.post("/kill-switch")
def set_kill_switch(active: bool, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    if active:
        activate_kill_switch(db, portfolio)
    else:
        deactivate_kill_switch(db, portfolio)
    db.commit()
    return {"kill_switch_active": active}
