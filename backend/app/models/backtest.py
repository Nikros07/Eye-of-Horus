from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(primary_key=True)

    strategy: Mapped[str] = mapped_column(String(64))
    strategy_version: Mapped[str] = mapped_column(String(16), default="1.0.0")

    asset_symbols: Mapped[list] = mapped_column(JSON, default=list)
    period_start: Mapped[datetime] = mapped_column(UTCDateTime())
    period_end: Mapped[datetime] = mapped_column(UTCDateTime())

    initial_capital: Mapped[float] = mapped_column(Float, default=10_000.0)
    risk_params: Mapped[dict] = mapped_column(JSON, default=dict)
    transaction_cost_bps: Mapped[float] = mapped_column(Float, default=5.0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=3.0)

    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/completed/failed

    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    equity_curve: Mapped[list] = mapped_column(JSON, default=list)
    trades: Mapped[list] = mapped_column(JSON, default=list)
    signal_stats: Mapped[dict] = mapped_column(JSON, default=dict)

    look_ahead_bias_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
