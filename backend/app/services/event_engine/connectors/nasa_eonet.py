"""Real connector for NASA EONET (Earth Observatory Natural Event Tracker).

Free, no API key. Requires outbound network access to eonet.gsfc.nasa.gov —
not reachable from every sandboxed environment, which is why the demo
connector exists alongside this one behind the same interface.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.services.event_engine.connectors.base import EventConnector, RawEvent

EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

# EONET category id -> our internal event_type taxonomy
CATEGORY_MAP = {
    "wildfires": "wildfire",
    "severeStorms": "extreme_weather",
    "floods": "flood",
    "drought": "drought",
    "earthquakes": "earthquake",
    "volcanoes": "volcanic_activity",
    "seaLakeIce": "extreme_weather",
    "tempExtremes": "extreme_weather",
}


class NasaEonetConnector(EventConnector):
    name = "NASA_EONET"
    kind = "event"
    is_demo = False

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def fetch(self, since: datetime | None = None) -> list[RawEvent]:
        params = {"status": "open", "limit": 100}
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(EONET_EVENTS_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        events: list[RawEvent] = []
        for item in payload.get("events", []):
            categories = item.get("categories", [])
            category_id = categories[0]["id"] if categories else "unknown"
            event_type = CATEGORY_MAP.get(category_id, "other")

            geometries = item.get("geometry", [])
            if not geometries:
                continue
            latest_geom = geometries[-1]
            coords = latest_geom.get("coordinates")
            if not coords:
                continue
            lon, lat = coords[0], coords[1]

            ts_raw = latest_geom.get("date")
            timestamp = _parse_dt(ts_raw) if ts_raw else datetime.now(timezone.utc)

            events.append(
                RawEvent(
                    source_event_id=item["id"],
                    event_type=event_type,
                    title=item.get("title", "Untitled event"),
                    timestamp=timestamp,
                    lat=float(lat),
                    lon=float(lon),
                    source=self.name,
                    geometry={"type": latest_geom.get("type"), "coordinates": coords},
                    source_url=item.get("sources", [{}])[0].get("url") if item.get("sources") else None,
                    publication_time=timestamp,
                    is_demo=False,
                    raw=item,
                )
            )
        return events


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
