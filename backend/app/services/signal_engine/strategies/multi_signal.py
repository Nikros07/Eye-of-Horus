"""Strategy D — Multi-Signal.

Hypothesis: combining independent evidence streams (event confidence,
weather corroboration, infrastructure corroboration, and how many similar
historical events exist to compare against) produces a better-calibrated
confidence estimate than any single stream alone. Each stream contributes a
capped weight so no single noisy input can dominate the blended score.
"""
from __future__ import annotations

from app.services.signal_engine.strategy_base import SignalCandidate, StrategyBase, StrategyContext

MIN_STREAMS = 2


class MultiSignalStrategy(StrategyBase):
    name = "multi_signal"
    version = "1.0.0"
    description = "Blends event, weather, infrastructure, market, and historical-analogue evidence into one confidence estimate."
    required_features = ["event.confidence", "evidence_items", "historical_analogue_count"]
    timeframe = "1h"

    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        if ctx.event is None:
            return []

        streams: dict[str, float] = {"event": ctx.event.confidence}
        for kind in ("weather", "infrastructure", "news"):
            items = [e for e in ctx.evidence_items if e.kind == kind]
            if items:
                streams[kind] = max(e.strength for e in items)

        analogue_weight = min(ctx.historical_analogue_count / 5, 1.0) * 0.5
        if analogue_weight > 0:
            streams["historical_analogues"] = analogue_weight

        if len(streams) < MIN_STREAMS:
            return []

        blended = sum(min(v, 1.0) for v in streams.values()) / len(streams)

        out: list[SignalCandidate] = []
        for link in ctx.impact_links:
            confidence = round(min(blended * (0.6 + 0.4 * link.exposure_score), 0.93), 3)
            out.append(
                SignalCandidate(
                    asset_symbol=link.asset_symbol,
                    direction=link.direction,
                    confidence=confidence,
                    expected_horizon="6-48h",
                    reasoning=(
                        f"Blended {len(streams)} independent evidence streams ({', '.join(streams)}) "
                        f"into a {blended:.0%} composite confidence, applied to {link.asset_symbol}."
                    ),
                    evidence=[f"{k}:{v:.3f}" for k, v in streams.items()],
                    strategy=self.name,
                    strategy_version=self.version,
                )
            )
        return out
