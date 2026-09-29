"""Strategy E — Baseline.

A plain price-trend follower with zero event awareness. Every event-driven
strategy must beat this (and the buy-and-hold baseline computed alongside
it in the backtester) to be considered to carry any informational value —
per the project's core empirical mandate, no strategy is assumed better
just because it is more sophisticated.
"""
from __future__ import annotations

from app.services.signal_engine.strategy_base import SignalCandidate, StrategyBase, StrategyContext
from app.services.signal_engine.utils import return_over_window

TREND_WINDOW_HOURS = 24
MIN_MOVE = 0.005


class BaselineStrategy(StrategyBase):
    name = "baseline_trend"
    version = "1.0.0"
    description = "Naive trend-following baseline with no event awareness; the bar every other strategy must clear."
    required_features = ["price_history"]
    timeframe = "1h"

    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        out: list[SignalCandidate] = []
        for symbol, bars in ctx.price_history.items():
            move = return_over_window(bars, hours=TREND_WINDOW_HOURS)
            if move is None or abs(move) < MIN_MOVE:
                continue
            direction = "bullish" if move > 0 else "bearish"
            out.append(
                SignalCandidate(
                    asset_symbol=symbol,
                    direction=direction,
                    confidence=0.5,
                    expected_horizon="24h",
                    reasoning=f"{symbol} trended {move:+.2%} over the last {TREND_WINDOW_HOURS}h; naive continuation.",
                    evidence=[f"return_{TREND_WINDOW_HOURS}h:{move:.4f}"],
                    strategy=self.name,
                    strategy_version=self.version,
                )
            )
        return out
