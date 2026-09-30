"""The platform's core correctness guarantee: a backtest must never use
data that would not yet have been available at the simulated point in
time. These tests both prove the guard fires when it should, and that the
real backtester genuinely enforces it end-to-end rather than trusting
callers to behave.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.market_engine.demo_adapter import generate_history
from app.services.quant_engine.backtester import BacktestParams, run_backtest
from app.services.quant_engine.temporal import LookAheadBiasError, TemporalGuard


def test_guard_allows_past_and_present_data():
    as_of = datetime(2026, 1, 10, tzinfo=timezone.utc)
    guard = TemporalGuard(as_of=as_of)
    guard.check(as_of - timedelta(hours=1), "past")
    guard.check(as_of, "exact")  # equal is allowed


def test_guard_rejects_future_data():
    as_of = datetime(2026, 1, 10, tzinfo=timezone.utc)
    guard = TemporalGuard(as_of=as_of)
    with pytest.raises(LookAheadBiasError, match="LOOK-AHEAD BIAS DETECTED"):
        guard.check(as_of + timedelta(minutes=1), "future_data")


def test_guard_filter_available_drops_future_items_without_raising():
    as_of = datetime(2026, 1, 10, tzinfo=timezone.utc)
    guard = TemporalGuard(as_of=as_of)
    items = [as_of - timedelta(hours=1), as_of + timedelta(hours=1), as_of]
    kept = guard.filter_available(items, lambda x: x)
    assert kept == [as_of - timedelta(hours=1), as_of]


def test_backtest_on_seeded_demo_data_reports_no_look_ahead_bias(db_session):
    """The real, non-adversarial path: seeding + backtesting the shipped
    demo dataset must never trip the guard."""
    from app.services.bootstrap import ensure_demo_data_seeded

    ensure_demo_data_seeded()

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=30)
    params = BacktestParams(strategy_name="multi_signal", period_start=period_start, period_end=period_end)
    result = run_backtest(db_session, params)

    assert result.look_ahead_bias_detected is False
    assert result.error is None


def test_backtest_detects_look_ahead_bias_when_price_data_is_future_dated(db_session):
    """Adversarial path: deliberately persist a price bar whose
    availability_time is AFTER the event that would use it, and confirm the
    backtester's TemporalGuard catches it rather than silently trading on
    it."""
    from app.services.bootstrap import ensure_demo_data_seeded
    from app.models.event import Event
    from app.models.market import Asset, PriceBar

    ensure_demo_data_seeded()

    event = db_session.query(Event).filter(Event.impact_links.any()).first()
    assert event is not None
    link = event.impact_links[0]
    asset = db_session.query(Asset).filter(Asset.symbol == link.asset_symbol).one()

    # A bar timestamped to look like it existed before the event, but whose
    # availability_time (when it was actually knowable) is AFTER the event —
    # exactly the shape of a real look-ahead bug (e.g. a restated/backfilled
    # price).
    poisoned_ts = event.availability_time - timedelta(hours=1)
    poisoned_availability = event.availability_time + timedelta(hours=2)
    db_session.add(
        PriceBar(
            asset_id=asset.id,
            ts=poisoned_ts,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
            source="POISONED_TEST_DATA",
            availability_time=poisoned_availability,
            is_demo=True,
        )
    )
    db_session.commit()

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=30)
    params = BacktestParams(strategy_name="event_momentum", period_start=period_start, period_end=period_end)
    result = run_backtest(db_session, params)

    assert result.look_ahead_bias_detected is True
    assert "LOOK-AHEAD BIAS DETECTED" in result.error


def test_build_context_for_event_analogue_count_excludes_future_analogues(db_session):
    """generator.build_context_for_event feeds the /api/replay endpoint,
    which promises no data whose availability_time is after `as_of` is ever
    used. historical_analogue_count must therefore respect `as_of` exactly
    like the backtester's own analogue-count query does (see
    backtester.run_backtest) — this is the same look-ahead-bias class
    already fixed there, caught here in the live/replay code path instead."""
    from app.models.event import Event
    from app.services.signal_engine.generator import build_context_for_event

    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    subject = Event(
        event_type="wildfire",
        title="Subject event",
        timestamp=base_time,
        lat=0.0,
        lon=0.0,
        availability_time=base_time,
        is_demo=True,
    )
    future_analogue = Event(
        event_type="wildfire",
        title="Future analogue — must NOT be counted at as_of=base_time",
        timestamp=base_time + timedelta(days=10),
        lat=0.0,
        lon=0.0,
        availability_time=base_time + timedelta(days=10),
        is_demo=True,
    )
    past_analogue = Event(
        event_type="wildfire",
        title="Past analogue — must be counted",
        timestamp=base_time - timedelta(days=5),
        lat=0.0,
        lon=0.0,
        availability_time=base_time - timedelta(days=5),
        is_demo=True,
    )
    db_session.add_all([subject, future_analogue, past_analogue])
    db_session.commit()

    ctx = build_context_for_event(db_session, subject, as_of=base_time)

    assert ctx.historical_analogue_count == 1


def test_demo_price_generation_is_deterministic():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=48)
    bars1 = generate_history("CL=F", start, end)
    bars2 = generate_history("CL=F", start, end)
    assert [b.close for b in bars1] == [b.close for b in bars2]
