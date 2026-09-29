from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.backtest import Backtest
from app.services.quant_engine.backtester import BacktestParams
from app.services.quant_engine.service import compare_strategies, run_and_store_backtest
from app.services.signal_engine.registry import STRATEGY_REGISTRY

router = APIRouter()


class BacktestRunRequest(BaseModel):
    strategy: str
    asset_symbols: list[str] | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    initial_capital: float = 10_000.0
    max_position_pct: float = 0.10
    transaction_cost_bps: float = 5.0
    slippage_bps: float = 3.0


class CompareRequest(BaseModel):
    strategies: list[str]
    asset_symbols: list[str] | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    initial_capital: float = 10_000.0


def _serialize(row: Backtest) -> dict:
    return {
        "id": row.id,
        "strategy": row.strategy,
        "status": row.status,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "initial_capital": row.initial_capital,
        "transaction_cost_bps": row.transaction_cost_bps,
        "slippage_bps": row.slippage_bps,
        "metrics": row.metrics,
        "equity_curve": row.equity_curve,
        "trades": row.trades,
        "signal_stats": row.signal_stats,
        "look_ahead_bias_detected": row.look_ahead_bias_detected,
        "error": row.error,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/strategies")
def list_strategies():
    return [
        {"name": name, "version": cls().version, "description": cls().description, "timeframe": cls().timeframe}
        for name, cls in STRATEGY_REGISTRY.items()
    ]


@router.post("/run")
def run_backtest_endpoint(req: BacktestRunRequest, db: Session = Depends(get_db)):
    if req.strategy not in STRATEGY_REGISTRY:
        raise HTTPException(400, f"Unknown strategy '{req.strategy}'")

    period_end = req.period_end or datetime.now(timezone.utc)
    period_start = req.period_start or (period_end - timedelta(days=30))

    params = BacktestParams(
        strategy_name=req.strategy,
        period_start=period_start,
        period_end=period_end,
        asset_symbols=req.asset_symbols,
        initial_capital=req.initial_capital,
        max_position_pct=req.max_position_pct,
        transaction_cost_bps=req.transaction_cost_bps,
        slippage_bps=req.slippage_bps,
    )
    row = run_and_store_backtest(db, params)
    db.commit()
    return _serialize(row)


@router.get("")
def list_backtests(db: Session = Depends(get_db), limit: int = 20):
    rows = db.query(Backtest).order_by(Backtest.created_at.desc()).limit(limit).all()
    return [_serialize(r) for r in rows]


@router.get("/{backtest_id}")
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    row = db.query(Backtest).filter(Backtest.id == backtest_id).one_or_none()
    if row is None:
        raise HTTPException(404, "Backtest not found")
    return _serialize(row)


@router.post("/compare")
def compare(req: CompareRequest, db: Session = Depends(get_db)):
    unknown = [s for s in req.strategies if s not in STRATEGY_REGISTRY]
    if unknown:
        raise HTTPException(400, f"Unknown strategies: {unknown}")

    period_end = req.period_end or datetime.now(timezone.utc)
    period_start = req.period_start or (period_end - timedelta(days=30))
    base_params = BacktestParams(
        strategy_name=req.strategies[0],
        period_start=period_start,
        period_end=period_end,
        asset_symbols=req.asset_symbols,
        initial_capital=req.initial_capital,
    )
    return compare_strategies(db, req.strategies, base_params)
