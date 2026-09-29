from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    """A verified-or-verifying real-world event with full data provenance.

    availability_time is the moment this event's data became knowable to the
    system — it is what the temporal-integrity guard checks against, and is
    distinct from event `timestamp` (when the event actually happened).
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: f"EVT-{uuid.uuid4().hex[:12]}")

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256))

    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)
    last_updated: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, onupdate=_now)

    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    location_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GeoJSON

    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="low")  # low/medium/high/critical

    sources: Mapped[list] = mapped_column(JSON, default=list)
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified")
    # unverified / pending / verified / disputed
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    affected_assets: Mapped[list] = mapped_column(JSON, default=list)
    affected_supply_chains: Mapped[list] = mapped_column(JSON, default=list)
    affected_commodities: Mapped[list] = mapped_column(JSON, default=list)
    market_exposure: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- provenance / temporal integrity ---
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)
    publication_time: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    availability_time: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, index=True)
    data_version: Mapped[str] = mapped_column(String(32), default="v1")
    raw_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_demo: Mapped[bool] = mapped_column(default=False)

    evidence: Mapped[list["EvidenceItem"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    impact_links: Mapped[list["ImpactLink"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)

    kind: Mapped[str] = mapped_column(String(32))  # weather / satellite / news / ais / infrastructure / historical
    source: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    strength: Mapped[float] = mapped_column(Float, default=0.5)  # how much this moves confidence

    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)
    availability_time: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now, index=True)
    data_version: Mapped[str] = mapped_column(String(32), default="v1")
    is_demo: Mapped[bool] = mapped_column(default=False)

    event: Mapped[Event] = relationship(back_populates="evidence")


class ImpactLink(Base):
    """One edge of the EVENT -> INFRASTRUCTURE -> SUPPLY CHAIN -> COMMODITY -> MARKET graph."""

    __tablename__ = "impact_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    asset_symbol: Mapped[str] = mapped_column(String(32), index=True)

    chain: Mapped[list] = mapped_column(JSON, default=list)  # ordered list of {"node": .., "type": ..}
    exposure_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1
    direction: Mapped[str] = mapped_column(String(8), default="bullish")  # bullish / bearish
    rationale: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_now)

    event: Mapped[Event] = relationship(back_populates="impact_links")
