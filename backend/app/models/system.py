from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    kind: Mapped[str] = mapped_column(String(32))  # event / weather / market / news / ais

    status: Mapped[str] = mapped_column(String(16), default="offline")  # online/degraded/offline
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_demo: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, onupdate=_now)
