"""Real connector for Open-Meteo — used to corroborate weather-sensitive
events (flood, hurricane, drought, wildfire, extreme_weather) with an
independent, free, no-key data source. Feeds the verification engine rather
than producing events of its own.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.services.event_engine.connectors.base import RawEvidence

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoConnector:
    name = "OPEN_METEO"
    kind = "weather"
    is_demo = False

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def fetch_current(self, lat: float, lon: float) -> RawEvidence | None:
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        current = payload.get("current_weather")
        if not current:
            return None

        summary = (
            f"windspeed={current.get('windspeed')}km/h "
            f"weathercode={current.get('weathercode')} "
            f"temperature={current.get('temperature')}C"
        )
        return RawEvidence(
            kind="weather",
            source=self.name,
            content=f"Open-Meteo current conditions at ({lat},{lon}): {summary}",
            strength=0.4,
            availability_time=datetime.now(timezone.utc),
            is_demo=False,
        )
