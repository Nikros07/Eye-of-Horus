from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), default="Main Portfolio")
    mode: Mapped[str] = mapped_column(String(16), default="paper")  # research / paper / live

    cash: Mapped[float] = mapped_column(Float, default=10_000.0)
    initial_capital: Mapped[float] = mapped_column(Float, default=10_000.0)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)

    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    risk_config: Mapped["RiskLimitConfig"] = relationship(back_populates="portfolio", uselist=False, cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)

    side: Mapped[str] = mapped_column(String(8))  # long / short
    qty: Mapped[float] = mapped_column(Float)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)

    opened_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")
    asset = relationship("Asset")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)

    side: Mapped[str] = mapped_column(String(8))  # buy / sell
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)
    order_type: Mapped[str] = mapped_column(String(16), default="market")
    status: Mapped[str] = mapped_column(String(16), default="filled")  # filled/rejected/cancelled

    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)

    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)

    mode: Mapped[str] = mapped_column(String(16), default="paper")  # paper / live
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, index=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="trades")
    asset = relationship("Asset")


class RiskLimitConfig(Base):
    __tablename__ = "risk_limit_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), unique=True)

    max_position_size_pct: Mapped[float] = mapped_column(Float, default=0.10)  # of equity
    max_daily_loss_pct: Mapped[float] = mapped_column(Float, default=0.03)
    max_portfolio_exposure_pct: Mapped[float] = mapped_column(Float, default=0.60)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=20)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.15)
    correlation_limit: Mapped[float] = mapped_column(Float, default=0.80)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)

    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="risk_config")
