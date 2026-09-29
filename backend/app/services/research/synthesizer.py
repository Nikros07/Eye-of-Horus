"""Evidence synthesis: turns an EvidenceBundle into the
OBSERVED / DERIVED / HYPOTHESIS / UNCERTAIN research output the frontend
renders. Tries the configured LLM provider first; falls back to a
deterministic, template-based synthesis built directly from bundle fields
(never invented text) if no provider is configured or it fails to return
usable structured output. Either path can only ever talk about what is
actually in the bundle.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.research.evidence import EvidenceBundle, bundle_to_dict
from app.services.research.llm_provider import get_llm_provider


@dataclass
class ResearchOutput:
    observed: list[str] = field(default_factory=list)
    derived: list[str] = field(default_factory=list)
    hypothesis: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    invalidation: list[str] = field(default_factory=list)
    market_already_priced: str = "NO"  # NO / POSSIBLY / YES
    historical_analogues: str = "INSUFFICIENT EVIDENCE"
    source: str = "deterministic"  # deterministic | claude


def synthesize_research(bundle: EvidenceBundle) -> ResearchOutput:
    provider = get_llm_provider()
    if provider is not None:
        raw = provider.synthesize(bundle_to_dict(bundle))
        if raw:
            try:
                return ResearchOutput(
                    observed=raw.get("observed", []),
                    derived=raw.get("derived", []),
                    hypothesis=raw.get("hypothesis", []),
                    uncertain=raw.get("uncertain", []),
                    risks=raw.get("risks", []),
                    invalidation=raw.get("invalidation", []),
                    market_already_priced=raw.get("market_already_priced", "NO"),
                    historical_analogues=raw.get("historical_analogues", "INSUFFICIENT EVIDENCE"),
                    source="claude",
                )
            except Exception:  # noqa: BLE001
                pass  # fall through to deterministic synthesis

    return _deterministic_synthesis(bundle)


def _deterministic_synthesis(bundle: EvidenceBundle) -> ResearchOutput:
    observed = [f"{bundle.event_type.replace('_', ' ').title()} event reported: \"{bundle.title}\"."]
    if bundle.location:
        observed.append(f"Location: {bundle.location}.")
    observed.append(f"Sources reporting this event: {', '.join(bundle.sources) or 'none recorded'}.")
    for item in bundle.evidence_items:
        tag = " [DEMO]" if item.get("is_demo") else ""
        observed.append(f"{item['kind'].title()} evidence from {item['source']}{tag}: {item['content']}")

    derived = [
        f"Verification status: {bundle.verification_status.upper()} (confidence {bundle.confidence:.0%})."
    ]
    for chain in bundle.impact_chains:
        derived.append(
            f"Impact chain implies {chain['direction'].upper()} pressure on {chain['asset_symbol']} "
            f"via {' -> '.join(chain['chain'])} (exposure {chain['exposure_score']:.0%})."
        )

    hypothesis: list[str] = []
    for signal in bundle.signals:
        hypothesis.append(
            f"[{signal['strategy']}] {signal['direction'].upper()} bias on {signal['asset_symbol']}, "
            f"confidence {signal['confidence']:.0%}, horizon {signal['expected_horizon']} — "
            f"pricing status: {signal['pricing_status'].replace('_', ' ')}."
        )

    uncertain = []
    if bundle.verification_status in ("unverified", "pending"):
        uncertain.append("Event is not yet independently verified by multiple sources.")
    if not bundle.evidence_items:
        uncertain.append("No corroborating evidence beyond the initial report is on file.")
    if bundle.historical_analogue_count == 0:
        uncertain.append("No historical analogues of this event type are on file to compare against.")

    risks = [
        "Event severity/magnitude estimates may be revised as more reports arrive.",
        "Impact chain weights are rule-based estimates, not measured elasticities.",
    ]

    invalidation = [
        "Independent sources retract or contradict the initial report.",
        "Market price action shows no reaction within the signal's expected horizon.",
    ]
    if bundle.impact_chains:
        invalidation.append(
            f"{bundle.impact_chains[0]['chain'][1] if len(bundle.impact_chains[0]['chain']) > 1 else 'The affected node'} "
            "resumes normal operation faster than assumed."
        )

    priced_statuses = {s["pricing_status"] for s in bundle.signals}
    if "priced" in priced_statuses:
        market_already_priced = "YES"
    elif "partially_priced" in priced_statuses:
        market_already_priced = "POSSIBLY"
    else:
        market_already_priced = "NO"

    if bundle.historical_analogue_count > 0:
        historical_analogues = f"{bundle.historical_analogue_count} prior {bundle.event_type.replace('_', ' ')} event(s) on file for comparison."
    else:
        historical_analogues = "INSUFFICIENT EVIDENCE"

    if not bundle.evidence_items and not bundle.impact_chains:
        return ResearchOutput(
            observed=observed,
            derived=["INSUFFICIENT EVIDENCE"],
            hypothesis=["INSUFFICIENT EVIDENCE"],
            uncertain=["Event has not yet been linked to any market exposure."],
            risks=risks,
            invalidation=invalidation,
            market_already_priced="NO",
            historical_analogues="INSUFFICIENT EVIDENCE",
            source="deterministic",
        )

    return ResearchOutput(
        observed=observed,
        derived=derived,
        hypothesis=hypothesis or ["INSUFFICIENT EVIDENCE"],
        uncertain=uncertain,
        risks=risks,
        invalidation=invalidation,
        market_already_priced=market_already_priced,
        historical_analogues=historical_analogues,
        source="deterministic",
    )
