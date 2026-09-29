from __future__ import annotations

from datetime import datetime, timezone

from app.services.signal_engine.registry import STRATEGY_REGISTRY, all_strategies
from app.services.signal_engine.strategies.baseline import BaselineStrategy
from app.services.signal_engine.strategy_base import StrategyContext
from app.services.market_engine.base import Bar


def _flat_bars(symbol_price: float, hours: int, ts_start: datetime) -> list[Bar]:
    from datetime import timedelta

    return [Bar(ts=ts_start + timedelta(hours=i), open=symbol_price, high=symbol_price, low=symbol_price, close=symbol_price, volume=1000) for i in range(hours)]


def test_all_five_strategies_are_registered():
    assert len(STRATEGY_REGISTRY) == 5
    names = set(STRATEGY_REGISTRY)
    assert names == {
        "event_momentum",
        "event_mean_reversion",
        "supply_chain_disruption",
        "multi_signal",
        "baseline_trend",
    }


def test_every_strategy_handles_empty_context_without_error():
    ctx = StrategyContext(as_of=datetime.now(timezone.utc))
    for strategy in all_strategies():
        result = strategy.generate(ctx)
        assert isinstance(result, list)


def test_baseline_strategy_trades_on_trend_with_no_event():
    now = datetime.now(timezone.utc)
    bars = _flat_bars(100.0, 30, now)
    # inject an uptrend in the last 24h
    for i, b in enumerate(bars[-24:]):
        b.close = 100.0 * (1 + 0.001 * i)

    ctx = StrategyContext(as_of=bars[-1].ts, price_history={"CL=F": bars})
    candidates = BaselineStrategy().generate(ctx)
    assert len(candidates) == 1
    assert candidates[0].direction == "bullish"
    assert candidates[0].strategy == "baseline_trend"


def test_position_size_is_proportional_to_confidence_with_no_floor():
    strategy = BaselineStrategy()
    low = strategy.position_size(confidence=0.2, equity=10_000, max_position_pct=0.1)
    high = strategy.position_size(confidence=0.8, equity=10_000, max_position_pct=0.1)
    assert low > 0  # sub-0.5 confidence must not be zeroed out
    assert high > low
    assert high == 10_000 * 0.1 * 0.8
