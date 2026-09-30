from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_main_portfolio
from app.core.config import get_settings
from app.core.db import get_db
from app.models.signal import Signal
from app.models.trading import Portfolio
from app.services.market_engine.factory import get_market_source
from app.services.trading_engine.broker_base import BrokerAdapter, OrderRequest
from app.services.trading_engine.risk_engine import check_order
from app.services.trading_engine.service import execute_signal, get_broker_for_portfolio

router = APIRouter()


def _get_broker(db: Session, portfolio: Portfolio) -> BrokerAdapter:
    try:
        return get_broker_for_portfolio(db, portfolio)
    except Exception as exc:  # noqa: BLE001 — LiveTradingNotConfiguredError or similar
        raise HTTPException(403, f"DO NOT PLACE ORDER: {exc}") from exc


class ModeChangeRequest(BaseModel):
    mode: str  # research / paper / live


class ManualOrderRequest(BaseModel):
    asset_symbol: str
    # PaperBroker treats anything that isn't exactly "buy" as a sell
    # (`sign = 1 if side == "buy" else -1`), so an unvalidated str let a
    # typo silently execute the opposite side instead of failing loudly.
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0)


class AutoTradeRequest(BaseModel):
    enabled: bool
    min_confidence: float | None = None


@router.get("/mode")
def get_mode(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    settings = get_settings()
    return {"mode": portfolio.mode, "live_trading_enabled": settings.live_trading_enabled}


@router.post("/mode")
def set_mode(req: ModeChangeRequest, db: Session = Depends(get_db)):
    if req.mode not in ("research", "paper", "live"):
        raise HTTPException(400, "mode must be one of research, paper, live")

    settings = get_settings()
    if req.mode == "live" and not settings.live_trading_enabled:
        raise HTTPException(403, "Live trading is disabled at the platform level (LIVE_TRADING_ENABLED=false). DO NOT PLACE ORDER.")

    portfolio = get_main_portfolio(db)
    portfolio.mode = req.mode
    db.commit()
    return {"mode": portfolio.mode}


@router.get("/auto-trade")
def get_auto_trade(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    return {"enabled": portfolio.auto_trade_enabled, "min_confidence": portfolio.auto_trade_min_confidence}


@router.post("/auto-trade")
def set_auto_trade(req: AutoTradeRequest, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    if portfolio.mode == "research" and req.enabled:
        raise HTTPException(403, "Portfolio is in RESEARCH mode — switch to paper (or live) before enabling auto-trade.")
    portfolio.auto_trade_enabled = req.enabled
    if req.min_confidence is not None:
        if not 0 <= req.min_confidence <= 1:
            raise HTTPException(400, "min_confidence must be between 0 and 1")
        portfolio.auto_trade_min_confidence = req.min_confidence
    db.commit()
    return {"enabled": portfolio.auto_trade_enabled, "min_confidence": portfolio.auto_trade_min_confidence}


@router.get("/account")
def get_account(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    broker = _get_broker(db, portfolio)
    account = broker.get_account()
    return {"cash": account.cash, "equity": account.equity, "buying_power": account.buying_power, "mode": account.mode}


@router.get("/positions")
def get_positions(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    broker = _get_broker(db, portfolio)
    return [p.__dict__ for p in broker.get_positions()]


@router.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    broker = _get_broker(db, portfolio)
    return [{**o.__dict__, "submitted_at": o.submitted_at.isoformat()} for o in broker.get_orders()]


@router.post("/orders")
def place_manual_order(req: ManualOrderRequest, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    if portfolio.mode == "research":
        raise HTTPException(403, "Portfolio is in RESEARCH mode — no orders are placed.")

    # A manual order is still an order: it must clear the same RiskEngine
    # gate (kill switch, exposure, drawdown, daily-loss, cooldown) that
    # execute_signal() applies to a signal-driven one. Placing it straight
    # on the broker, as this endpoint previously did, let a manual click
    # bypass the kill switch and every other limit entirely.
    market_source = get_market_source()
    price_lookup = lambda sym: market_source.get_quote(sym).price  # noqa: E731
    try:
        current_price = price_lookup(req.asset_symbol)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not fetch quote for {req.asset_symbol}: {exc}") from exc

    check = check_order(db, portfolio, req.asset_symbol, req.side, req.qty * current_price, current_price, price_lookup)
    if not check.approved:
        raise HTTPException(403, check.reason)

    broker = _get_broker(db, portfolio)
    order = broker.place_order(OrderRequest(asset_symbol=req.asset_symbol, side=req.side, qty=check.approved_qty))
    db.commit()
    return {**order.__dict__, "submitted_at": order.submitted_at.isoformat()}


@router.post("/orders/execute-signal/{signal_id}")
def execute_signal_order(signal_id: str, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    signal = db.query(Signal).filter(Signal.signal_id == signal_id).one_or_none()
    if signal is None:
        raise HTTPException(404, "Signal not found")
    decision = execute_signal(db, portfolio, signal)
    db.commit()
    return {
        "approved": decision.approved,
        "reason": decision.reason,
        "order": {**decision.order.__dict__, "submitted_at": decision.order.submitted_at.isoformat()} if decision.order else None,
    }


@router.post("/positions/{symbol}/close")
def close_position(symbol: str, db: Session = Depends(get_db)):
    portfolio = get_main_portfolio(db)
    position = next(
        (p for p in portfolio.positions if p.asset.symbol == symbol and p.closed_at is None),
        None,
    )
    if position is None:
        raise HTTPException(404, "No open position for this symbol")

    # Same RiskEngine gate as place_manual_order — closing a position is
    # still an order the broker executes, and previously skipped the kill
    # switch (and every other limit) entirely.
    market_source = get_market_source()
    price_lookup = lambda sym: market_source.get_quote(sym).price  # noqa: E731
    current_price = price_lookup(symbol)
    check = check_order(db, portfolio, symbol, "sell", position.qty * current_price, current_price, price_lookup)
    if not check.approved:
        raise HTTPException(403, check.reason)

    broker = _get_broker(db, portfolio)
    order = broker.close_position(symbol)
    db.commit()
    if order is None:
        raise HTTPException(404, "No open position for this symbol")
    return {**order.__dict__, "submitted_at": order.submitted_at.isoformat()}
