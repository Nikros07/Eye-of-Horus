"""Strategy C — Supply Chain Disruption.

Hypothesis: multi-hop disruptions (event -> infrastructure -> supply chain
-> commodity) are slower to fully price than direct events because they
require the market to reason through an indirect causal chain — so the
edge, if any, persists longer than plain event momentum. Requires at least
one infrastructure hop AND independent infrastructure-kind evidence, which
is a stricter bar than Strategy A.
"""
from __future__ import annotations

from app.services.signal_engine.strategy_base import SignalCandidate, StrategyBase, StrategyContext

MIN_CONFIDENCE = 0.5
MIN_CHAIN_LENGTH = 4  # event + at least infra + supply_chain + market


class SupplyChainDisruptionStrategy(StrategyBase):
    name = "supply_chain_disruption"
    version = "1.0.0"
    description = "Trades multi-hop infrastructure-to-commodity disruption chains with corroborating evidence."
    required_features = ["impact_links.chain", "evidence_items.kind"]
    timeframe = "4h"

    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        if ctx.event is None or ctx.event.confidence < MIN_CONFIDENCE:
            return []

        has_infra_evidence = any(e.kind == "infrastructure" for e in ctx.evidence_items)

        out: list[SignalCandidate] = []
        for link in ctx.impact_links:
            if len(link.chain) < MIN_CHAIN_LENGTH:
                continue
            infra_hops = [n for n in link.chain if n["type"] in ("infrastructure", "supply_chain")]
            if len(infra_hops) < 2:
                continue

            confidence = ctx.event.confidence * (0.55 + 0.25 * link.exposure_score)
            if has_infra_evidence:
                confidence += 0.1
            confidence = round(min(confidence, 0.9), 3)

            out.append(
                SignalCandidate(
                    asset_symbol=link.asset_symbol,
                    direction=link.direction,
                    confidence=confidence,
                    expected_horizon="24-72h",
                    reasoning=(
                        f"Multi-hop supply chain disruption: {' -> '.join(n['node'] for n in link.chain)}. "
                        f"{'Corroborated by independent infrastructure evidence.' if has_infra_evidence else 'No independent infrastructure evidence yet.'}"
                    ),
                    evidence=[f"chain_length:{len(link.chain)}", f"infra_evidence:{has_infra_evidence}"],
                    strategy=self.name,
                    strategy_version=self.version,
                )
            )
        return out
