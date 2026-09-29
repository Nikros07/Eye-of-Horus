"""Connector interface for real-world event sources.

Every source (NASA EONET, weather services, AIS, news feeds, ...) implements
this same shape so the ingestion pipeline never needs to know which provider
it is talking to. Swapping or adding a provider means adding one connector,
not touching the pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawEvent:
    source_event_id: str
    event_type: str
    title: str
    timestamp: datetime
    lat: float
    lon: float
    source: str
    location_name: str | None = None
    magnitude: float | None = None
    severity_hint: str | None = None
    geometry: dict | None = None
    source_url: str | None = None
    publication_time: datetime | None = None
    is_demo: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class RawEvidence:
    kind: str
    source: str
    content: str
    strength: float = 0.5
    source_url: str | None = None
    availability_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_demo: bool = False


class EventConnector(ABC):
    """A single external data source producing RawEvents."""

    name: str
    kind: str = "event"
    is_demo: bool = False

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> list[RawEvent]:
        """Return events observed since `since` (or a reasonable default window)."""
        raise NotImplementedError

    def check_health(self) -> tuple[bool, float | None, str | None]:
        """Lightweight liveness probe. Returns (is_ok, latency_ms, error)."""
        import time

        start = time.monotonic()
        try:
            self.fetch()
            return True, (time.monotonic() - start) * 1000, None
        except Exception as exc:  # noqa: BLE001 - surfaced as source status, not raised
            return False, None, str(exc)
