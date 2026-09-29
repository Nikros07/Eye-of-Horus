from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    asset_class: Mapped[str] = mapped_column(String(32))
    # equity / etf / index / commodity / energy / metal / agriculture / fx / futures / crypto
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    prices: Mapped[list["PriceBar"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class PriceBar(Base):
    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)

    source: Mapped[str] = mapped_column(String(32), default="demo")
    availability_time: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, index=True)
    is_demo: Mapped[bool] = mapped_column(default=False)

    asset: Mapped[Asset] = relationship(back_populates="prices")
