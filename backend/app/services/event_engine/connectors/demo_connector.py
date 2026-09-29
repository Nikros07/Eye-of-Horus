"""Deterministic demo/seed event generator.

Used whenever DATA_MODE=demo (the default for this sandboxed environment,
where outbound access to NASA/NOAA/etc is blocked). Every event and evidence
item produced here is flagged is_demo=True end-to-end into the API and UI —
it must never be presented as live data (see project rule: no fake live
data). The fixed seed makes ingestion reproducible for tests and for the
backtester.
"""
from __future__ import annotations

import random
import zlib
from datetime import datetime, timedelta, timezone

from app.services.event_engine.connectors.base import EventConnector, RawEvent, RawEvidence

_SEED = 42

# (event_type, title, lat, lon, location_name, magnitude, severity)
_SCENARIOS = [
    ("flood", "Major flooding disrupts Gulf Coast crude terminals", 29.75, -95.36, "Houston Ship Channel, US", 7.8, "high"),
    ("hurricane", "Hurricane approaches Gulf of Mexico oil platforms", 26.0, -90.5, "Gulf of Mexico", 4.0, "critical"),
    ("port_disruption", "Container backlog builds at Port of Long Beach", 33.75, -118.19, "Port of Long Beach, US", 6.5, "medium"),
    ("earthquake", "Magnitude 6.4 earthquake strikes northern Chile mining belt", -22.46, -68.93, "Atacama Region, Chile", 6.4, "high"),
    ("wildfire", "Wildfire threatens Canadian lumber operations", 53.93, -116.57, "Alberta, Canada", 5.2, "medium"),
    ("drought", "Severe drought reduces Argentine soybean yield outlook", -33.0, -64.0, "Córdoba Province, Argentina", 4.5, "high"),
    ("pipeline_disruption", "Pipeline outage cuts crude flow from Cushing hub", 35.98, -96.77, "Cushing, Oklahoma, US", 5.0, "high"),
    ("refinery_disruption", "Unplanned refinery outage reported on US Gulf Coast", 29.3, -94.8, "Port Arthur, Texas, US", 5.5, "high"),
    ("mine_disruption", "Strike halts operations at major Chilean copper mine", -23.7, -69.6, "Escondida Mine, Chile", 5.8, "high"),
    ("power_outage", "Grid failure disrupts semiconductor fabs in Taiwan", 24.8, 121.0, "Hsinchu, Taiwan", 5.0, "medium"),
    ("industrial_accident", "Explosion reported at petrochemical plant", 29.95, -93.94, "Lake Charles, Louisiana, US", 4.8, "medium"),
    ("strike", "Dockworkers strike shuts down European container terminal", 51.9, 4.48, "Port of Rotterdam, Netherlands", 4.0, "medium"),
    ("geopolitical_disruption", "Shipping lane tensions escalate near key maritime chokepoint", 12.58, 43.33, "Bab-el-Mandeb Strait", 6.0, "critical"),
    ("airport_disruption", "Cargo hub grounded by air traffic system failure", 41.98, -87.9, "O'Hare Cargo Hub, US", 3.5, "low"),
    ("extreme_weather", "Cold snap threatens natural gas demand spike", 41.5, -87.6, "Midwest US", 4.2, "medium"),
]


class DemoEventConnector(EventConnector):
    name = "DEMO_GENERATOR"
    kind = "event"
    is_demo = True

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(timezone.utc)

    def fetch(self, since: datetime | None = None) -> list[RawEvent]:
        rng = random.Random(_SEED)
        events: list[RawEvent] = []
        for idx, (event_type, title, lat, lon, loc, magnitude, severity) in enumerate(_SCENARIOS):
            age_hours = rng.uniform(1, 96)
            timestamp = self._now - timedelta(hours=age_hours)
            jitter = rng.uniform(-0.5, 0.5)
            events.append(
                RawEvent(
                    source_event_id=f"DEMO-{idx:03d}",
                    event_type=event_type,
                    title=title,
                    timestamp=timestamp,
                    lat=lat + jitter * 0.1,
                    lon=lon + jitter * 0.1,
                    location_name=loc,
                    magnitude=magnitude,
                    severity_hint=severity,
                    source=self.name,
                    geometry={"type": "Point", "coordinates": [lon, lat]},
                    source_url=None,
                    publication_time=timestamp + timedelta(minutes=rng.uniform(10, 90)),
                    is_demo=True,
                    raw={"demo_index": idx},
                )
            )
        return events

    def fetch_corroborating_evidence(self, raw_event: RawEvent) -> list[RawEvidence]:
        """Deterministic secondary-source + weather evidence for demo events.

        Seeds from crc32, not the builtin hash(): str hashing is randomized
        per-process (PYTHONHASHSEED), which would make this "deterministic"
        generator produce different evidence on every restart."""
        source_id_seed = zlib.crc32(raw_event.source_event_id.encode()) % 1000
        rng = random.Random(_SEED + source_id_seed)
        items: list[RawEvidence] = []

        items.append(
            RawEvidence(
                kind="news",
                source="DEMO_NEWSWIRE",
                content=f"Independent wire report corroborates: {raw_event.title}",
                strength=0.45,
                availability_time=raw_event.publication_time or self._now,
                is_demo=True,
            )
        )

        if raw_event.event_type in {"flood", "hurricane", "drought", "extreme_weather", "wildfire"}:
            windspeed = round(rng.uniform(20, 140), 1)
            items.append(
                RawEvidence(
                    kind="weather",
                    source="DEMO_WEATHER",
                    content=f"Synthetic weather confirmation near ({raw_event.lat:.2f},{raw_event.lon:.2f}): "
                    f"windspeed={windspeed}km/h, conditions consistent with reported event.",
                    strength=0.5,
                    availability_time=(raw_event.publication_time or self._now) + timedelta(minutes=15),
                    is_demo=True,
                )
            )

        if raw_event.event_type in {"port_disruption", "airport_disruption", "strike"}:
            items.append(
                RawEvidence(
                    kind="infrastructure",
                    source="DEMO_AIS_PROXY",
                    content="Synthetic vessel/traffic queuing pattern consistent with reported disruption.",
                    strength=0.4,
                    availability_time=(raw_event.publication_time or self._now) + timedelta(minutes=30),
                    is_demo=True,
                )
            )

        return items
