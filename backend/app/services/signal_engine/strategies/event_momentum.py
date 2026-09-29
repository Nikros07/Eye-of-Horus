"""Strategy A — Event Momentum.

Hypothesis: a verified, high-exposure event pushes price in the direction
implied by the impact chain, and that move continues (rather than reverses)
over the following hours as slower participants catch up.
"""
from __future__ import annotations

from app.services.signal_engine.strategy_base import SignalCandidate, StrategyBase, StrategyContext

MIN_CONFIDENCE = 0.5
MIN_EXPOSURE = 0.3


class EventMomentumStrategy(StrategyBase):
    name = "event_momentum"
    version = "1.0.0"
    description = "Trades in the direction of a verified event's implied market impact."
    required_features = ["event.confidence", "impact_links.exposure_score"]
    timeframe = "1h"

    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        if ctx.event is None or ctx.event.verification_status == "unverified":
            return []
        if ctx.event.confidence < MIN_CONFIDENCE:
            return []

        out: list[SignalCandidate] = []
        for link in ctx.impact_links:
            if link.exposure_score < MIN_EXPOSURE:
                continue
            direction = link.direction
            confidence = round(min(ctx.event.confidence * (0.5 + 0.5 * link.exposure_score), 0.95), 3)
            out.append(
                SignalCandidate(
                    asset_symbol=link.asset_symbol,
                    direction=direction,
                    confidence=confidence,
                    expected_horizon="6-24h",
                    reasoning=(
                        f"{ctx.event.event_type.replace('_', ' ').title()} event "
                        f"({ctx.event.verification_status}, confidence {ctx.event.confidence:.0%}) "
                        f"implies {direction} pressure on {link.asset_symbol} via "
                        f"{' -> '.join(n['node'] for n in link.chain)}."
                    ),
                    evidence=[f"impact_chain:{link.chain}", f"exposure_score:{link.exposure_score}"],
                    strategy=self.name,
                    strategy_version=self.version,
                )
            )
        return out
