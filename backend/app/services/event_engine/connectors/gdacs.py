"""Real connector for GDACS (Global Disaster Alert and Coordination System)
— a free, no-key RSS feed of active disaster alerts, used as a second,
independent corroboration source for NASA EONET events.

Unlike Open-Meteo (weather conditions only, see open_meteo.py), GDACS
tracks the same disaster categories EONET does — earthquakes, floods,
tropical cyclones, volcanoes, wildfires, droughts — so an independent
specialized tracking service reporting a compatible event at a similar
place and time is real corroboration, not limited to the weather-sensitive
event types Open-Meteo is restricted to. This is what lets single-source
live events (e.g. an earthquake, which Open-Meteo can never corroborate)
reach a high enough confidence to actually clear a strategy's gate — see
app/services/event_engine/verification.py and
app/services/signal_engine/strategies/*.py's MIN_CONFIDENCE constants.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.services.event_engine.connectors.base import RawEvidence

GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"

# GDACS event-type code -> our internal event_type taxonomy, mirroring NASA
# EONET's CATEGORY_MAP (nasa_eonet.py) so alerts from both sources line up
# on the same underlying disasters.
GDACS_TYPE_MAP = {
    "EQ": "earthquake",
    "TC": "hurricane",
    "FL": "flood",
    "VO": "volcanic_activity",
    "DR": "drought",
    "WF": "wildfire",
    "TS": "extreme_weather",
}

# A specialized disaster service independently tracking the same event is
# real corroboration at any alert level; the level only adjusts how strong.
_ALERT_STRENGTH = {"red": 0.9, "orange": 0.75, "green": 0.6}
_DEFAULT_STRENGTH = 0.55

_MATCH_RADIUS_KM = 250.0
_MATCH_WINDOW = timedelta(days=3)


@dataclass
class GdacsAlert:
    event_type: str
    lat: float
    lon: float
    published: datetime
    alert_level: str
    title: str


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _find_text(item: ET.Element, *local_names: str) -> str | None:
    """Namespace-agnostic child lookup. GDACS's exact xmlns prefixes aren't
    verifiable from this sandboxed, network-blocked environment, so this
    matches on local tag name only rather than risking a hardcoded
    namespace URI that turns out stale or slightly wrong — a feed whose
    structure has shifted degrades to "no match" per item, never a crash.
    """
    wanted = {n.lower() for n in local_names}
    for child in item.iter():
        if _local_name(child.tag) in wanted and child.text and child.text.strip():
            return child.text.strip()
    return None


def _find_point(item: ET.Element) -> tuple[float, float] | None:
    lat_text = _find_text(item, "lat")
    lon_text = _find_text(item, "long", "lon")
    if lat_text and lon_text:
        try:
            return float(lat_text), float(lon_text)
        except ValueError:
            pass
    point_text = _find_text(item, "point")
    if point_text:
        parts = point_text.split()
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass
    return None


def _parse_item(item: ET.Element) -> GdacsAlert | None:
    type_code = _find_text(item, "eventtype")
    event_type = GDACS_TYPE_MAP.get((type_code or "").upper())
    if event_type is None:
        return None

    point = _find_point(item)
    if point is None:
        return None

    pub_date_text = _find_text(item, "pubdate")
    try:
        published = parsedate_to_datetime(pub_date_text) if pub_date_text else datetime.now(timezone.utc)
    except (TypeError, ValueError, IndexError):
        published = datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)

    alert_level = (_find_text(item, "alertlevel") or "").lower()
    title = _find_text(item, "title") or f"GDACS {type_code} alert"

    return GdacsAlert(event_type=event_type, lat=point[0], lon=point[1], published=published, alert_level=alert_level, title=title)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class GdacsConnector:
    """Fetches current GDACS alerts to cross-reference against events other
    connectors already found — like OpenMeteoConnector, it produces
    RawEvidence for existing events rather than RawEvents of its own.
    """

    name = "GDACS"
    kind = "disaster_alert"
    is_demo = False

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def fetch_alerts(self) -> list[GdacsAlert]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(GDACS_RSS_URL)
            resp.raise_for_status()
            body = resp.content

        root = ET.fromstring(body)
        alerts: list[GdacsAlert] = []
        for item in root.iter():
            if _local_name(item.tag) != "item":
                continue
            alert = _parse_item(item)
            if alert is not None:
                alerts.append(alert)
        return alerts

    def corroborate(self, event_type: str, lat: float, lon: float, as_of: datetime, alerts: list[GdacsAlert]) -> RawEvidence | None:
        """Matches against an already-fetched alert list — fetch once per
        ingestion cycle (fetch_alerts), match against every event — rather
        than re-fetching the whole feed per event. Returns None if nothing
        matches: corroboration is additive, never load-bearing.
        """
        best: GdacsAlert | None = None
        best_strength = -1.0
        for alert in alerts:
            if alert.event_type != event_type:
                continue
            if abs((alert.published - as_of).total_seconds()) > _MATCH_WINDOW.total_seconds():
                continue
            if _haversine_km(lat, lon, alert.lat, alert.lon) > _MATCH_RADIUS_KM:
                continue
            strength = _ALERT_STRENGTH.get(alert.alert_level, _DEFAULT_STRENGTH)
            if strength > best_strength:
                best, best_strength = alert, strength

        if best is None:
            return None

        return RawEvidence(
            kind="news",
            source=self.name,
            content=f"GDACS independently tracks a matching {event_type} alert ({best.alert_level or 'unrated'} level): {best.title}",
            strength=best_strength,
            availability_time=datetime.now(timezone.utc),
            is_demo=False,
        )
