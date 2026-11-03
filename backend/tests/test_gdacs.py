from __future__ import annotations

from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

from app.services.event_engine.connectors.gdacs import (
    GdacsAlert,
    GdacsConnector,
    _haversine_km,
    _parse_item,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#" xmlns:gdacs="http://www.gdacs.org">
  <channel>
    <title>GDACS</title>
    <item>
      <title>Earthquake in Testland</title>
      <description>Magnitude 6.1</description>
      <pubDate>Mon, 01 Jun 2026 12:00:00 GMT</pubDate>
      <geo:Point>
        <geo:lat>12.345</geo:lat>
        <geo:long>56.789</geo:long>
      </geo:Point>
      <gdacs:eventtype>EQ</gdacs:eventtype>
      <gdacs:alertlevel>Orange</gdacs:alertlevel>
      <gdacs:eventid>123456</gdacs:eventid>
    </item>
    <item>
      <title>Unrelated bulletin with no coordinates</title>
      <pubDate>Mon, 01 Jun 2026 11:00:00 GMT</pubDate>
      <gdacs:eventtype>EQ</gdacs:eventtype>
    </item>
    <item>
      <title>Something GDACS doesn't categorize for us</title>
      <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
      <geo:Point><geo:lat>1.0</geo:lat><geo:long>2.0</geo:long></geo:Point>
      <gdacs:eventtype>XX</gdacs:eventtype>
    </item>
  </channel>
</rss>
"""


def test_parse_item_extracts_a_well_formed_alert():
    root = ET.fromstring(SAMPLE_RSS)
    items = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "item"]
    alert = _parse_item(items[0])

    assert alert is not None
    assert alert.event_type == "earthquake"
    assert alert.lat == 12.345
    assert alert.lon == 56.789
    assert alert.alert_level == "orange"
    assert alert.published.year == 2026


def test_parse_item_returns_none_without_coordinates():
    root = ET.fromstring(SAMPLE_RSS)
    items = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "item"]
    assert _parse_item(items[1]) is None


def test_parse_item_returns_none_for_an_unmapped_event_type():
    root = ET.fromstring(SAMPLE_RSS)
    items = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "item"]
    assert _parse_item(items[2]) is None


def test_fetch_alerts_parses_only_the_well_formed_items(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=SAMPLE_RSS.encode())

    original_init = httpx.Client.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", patched_init)

    alerts = GdacsConnector().fetch_alerts()
    assert len(alerts) == 1
    assert alerts[0].event_type == "earthquake"


def test_corroborate_matches_same_type_nearby_and_recent():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    alerts = [GdacsAlert(event_type="earthquake", lat=12.3, lon=56.7, published=now, alert_level="red", title="EQ")]

    evidence = GdacsConnector().corroborate("earthquake", 12.4, 56.8, now + timedelta(hours=1), alerts)

    assert evidence is not None
    assert evidence.kind == "news"
    assert evidence.source == "GDACS"
    assert evidence.strength == 0.9  # red


def test_corroborate_returns_none_for_a_different_event_type():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    alerts = [GdacsAlert(event_type="flood", lat=12.3, lon=56.7, published=now, alert_level="red", title="FL")]
    assert GdacsConnector().corroborate("earthquake", 12.3, 56.7, now, alerts) is None


def test_corroborate_returns_none_when_too_far_away():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    alerts = [GdacsAlert(event_type="earthquake", lat=12.3, lon=56.7, published=now, alert_level="red", title="EQ")]
    # roughly 2500km away, well outside the 250km match radius
    assert GdacsConnector().corroborate("earthquake", 12.3, 80.0, now, alerts) is None


def test_corroborate_returns_none_when_too_old():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    alerts = [GdacsAlert(event_type="earthquake", lat=12.3, lon=56.7, published=now, alert_level="red", title="EQ")]
    assert GdacsConnector().corroborate("earthquake", 12.3, 56.7, now + timedelta(days=30), alerts) is None


def test_corroborate_with_no_alerts_returns_none():
    assert GdacsConnector().corroborate("earthquake", 0.0, 0.0, datetime.now(timezone.utc), []) is None


def test_haversine_zero_distance_for_identical_points():
    assert _haversine_km(10.0, 20.0, 10.0, 20.0) == 0.0


def test_haversine_known_city_pair_is_roughly_right():
    # Berlin to Paris is ~880km
    km = _haversine_km(52.5200, 13.4050, 48.8566, 2.3522)
    assert 800 < km < 950
