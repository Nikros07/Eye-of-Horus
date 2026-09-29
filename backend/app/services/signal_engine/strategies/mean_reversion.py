"""Strategy B — Event Mean Reversion.

Hypothesis: when price has already moved sharply in the event's implied
direction before the signal is generated, the move has likely overshot the
event's real informational content, and a statistical pullback is more
likely than continued momentum. This deliberately trades AGAINST Strategy A
on the same event, so backtests can show which hypothesis actually holds
per event type / regime rather than assuming either is right.
"""
from __future__ import annotations

from app.services.signal_engine.strategy_base import SignalCandidate, StrategyBase, StrategyContext
from app.services.signal_engine.utils import return_over_window

MIN_CONFIDENCE = 0.45
OVEREXTENSION_THRESHOLD = 0.02  # 2% move already priced in triggers reversion hypothesis


class MeanReversionStrategy(StrategyBase):
    name = "event_mean_reversion"
    version = "1.0.0"
    description = "Fades an overextended post-event price move back toward the pre-event level."
    required_features = ["event.confidence", "price_history.return_since_event"]
    timeframe = "1h"

    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        if ctx.event is None or ctx.event.confidence < MIN_CONFIDENCE:
            return []

        out: list[SignalCandidate] = []
        for link in ctx.impact_links:
            bars = ctx.price_history.get(link.asset_symbol)
            if not bars:
                continue
            move = return_over_window(bars, hours=6)
            if move is None or abs(move) < OVEREXTENSION_THRESHOLD:
                continue

            expected_sign = 1.0 if link.direction == "bullish" else -1.0
            already_moved_with_thesis = (move > 0) == (expected_sign > 0)
            if not already_moved_with_thesis:
                continue  # move contradicts the thesis; not an overextension case

            reversion_direction = "bearish" if link.direction == "bullish" else "bullish"
            confidence = round(min(0.4 + min(abs(move), 0.08) * 4, 0.85) * (0.6 + 0.4 * ctx.event.confidence), 3)

            out.append(
                SignalCandidate(
                    asset_symbol=link.asset_symbol,
                    direction=reversion_direction,
                    confidence=confidence,
                    expected_horizon="12-48h",
                    reasoning=(
                        f"{link.asset_symbol} already moved {move:+.2%} in the direction implied by the "
                        f"{ctx.event.event_type} event over the last 6h — statistically overextended relative to "
                        f"event confidence ({ctx.event.confidence:.0%}); mean reversion favored."
                    ),
                    evidence=[f"return_6h:{move:.4f}", f"event_confidence:{ctx.event.confidence}"],
                    strategy=self.name,
                    strategy_version=self.version,
                )
            )
        return out
