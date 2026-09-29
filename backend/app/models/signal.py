from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: f"SIG-{uuid.uuid4().hex[:12]}")

    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)

    direction: Mapped[str] = mapped_column(String(16))  # bullish / bearish / neutral
    confidence: Mapped[float] = mapped_column(Float)
    expected_horizon: Mapped[str] = mapped_column(String(32))  # e.g. "6-24h"

    reasoning: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSON, default=list)

    strategy: Mapped[str] = mapped_column(String(64), index=True)
    strategy_version: Mapped[str] = mapped_column(String(16), default="1.0.0")
    data_version: Mapped[str] = mapped_column(String(32), default="v1")

    pricing_status: Mapped[str] = mapped_column(String(24), default="unpriced")
    # unpriced / partially_priced / priced

    signal_time: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, index=True)
    availability_time: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)

    asset = relationship("Asset")
    event = relationship("Event")
