from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.signal import Signal
from app.models.trading import Portfolio
from app.services.trading_engine.broker_base import BrokerAdapter, OrderRequest
from app.services.trading_engine.service import execute_signal, get_broker_for_portfolio

router = APIRouter()


def _get_portfolio(db: Session) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one_or_none()
    if portfolio is None:
        raise HTTPException(404, "No portfolio found — startup seeding may not have completed yet.")
    return portfolio


def _get_broker(db: Session, portfolio: Portfolio) -> BrokerAdapter:
    try:
        return get_broker_for_portfolio(db, portfolio)
    except Exception as exc:  # noqa: BLE001 — LiveTradingNotConfiguredError or similar
        raise HTTPException(403, f"DO NOT PLACE ORDER: {exc}") from exc


class ModeChangeRequest(BaseModel):
    mode: str  # research / paper / live


class ManualOrderRequest(BaseModel):
    asset_symbol: str
    side: str  # buy / sell
    qty: float


@router.get("/mode")
def get_mode(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    settings = get_settings()
    return {"mode": portfolio.mode, "live_trading_enabled": settings.live_trading_enabled}


@router.post("/mode")
def set_mode(req: ModeChangeRequest, db: Session = Depends(get_db)):
    if req.mode not in ("research", "paper", "live"):
        raise HTTPException(400, "mode must be one of research, paper, live")

    settings = get_settings()
    if req.mode == "live" and not settings.live_trading_enabled:
        raise HTTPException(403, "Live trading is disabled at the platform level (LIVE_TRADING_ENABLED=false). DO NOT PLACE ORDER.")

    portfolio = _get_portfolio(db)
    portfolio.mode = req.mode
    db.commit()
    return {"mode": portfolio.mode}


@router.get("/account")
def get_account(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    broker = _get_broker(db, portfolio)
    account = broker.get_account()
    return {"cash": account.cash, "equity": account.equity, "buying_power": account.buying_power, "mode": account.mode}


@router.get("/positions")
def get_positions(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    broker = _get_broker(db, portfolio)
    return [p.__dict__ for p in broker.get_positions()]


@router.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    broker = _get_broker(db, portfolio)
    return [{**o.__dict__, "submitted_at": o.submitted_at.isoformat()} for o in broker.get_orders()]


@router.post("/orders")
def place_manual_order(req: ManualOrderRequest, db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
    if portfolio.mode == "research":
        raise HTTPException(403, "Portfolio is in RESEARCH mode — no orders are placed.")
    broker = _get_broker(db, portfolio)
    order = broker.place_order(OrderRequest(asset_symbol=req.asset_symbol, side=req.side, qty=req.qty))
    db.commit()
    return {**order.__dict__, "submitted_at": order.submitted_at.isoformat()}


@router.post("/orders/execute-signal/{signal_id}")
def execute_signal_order(signal_id: str, db: Session = Depends(get_db)):
    portfolio = _get_portfolio(db)
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
    portfolio = _get_portfolio(db)
    broker = _get_broker(db, portfolio)
    order = broker.close_position(symbol)
    db.commit()
    if order is None:
        raise HTTPException(404, "No open position for this symbol")
    return {**order.__dict__, "submitted_at": order.submitted_at.isoformat()}
