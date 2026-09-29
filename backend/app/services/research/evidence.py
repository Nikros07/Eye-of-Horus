"""Builds the structured evidence bundle the research layer is allowed to
reason over. This is the enforcement boundary against hallucination: the
synthesizer (deterministic or LLM-backed) never receives raw free text to
riff on, only this typed bundle, and is instructed to output
INSUFFICIENT EVIDENCE for anything not present in it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.signal import Signal


@dataclass
class EvidenceBundle:
    event_id: str
    event_type: str
    title: str
    location: str | None
    severity: str
    verification_status: str
    confidence: float
    sources: list[str]
    evidence_items: list[dict]
    impact_chains: list[dict]
    historical_analogue_count: int
    signals: list[dict] = field(default_factory=list)
    market_reaction: dict | None = None


def build_evidence_bundle(db: Session, event: Event) -> EvidenceBundle:
    analogue_count = db.query(Event).filter(Event.event_type == event.event_type, Event.id != event.id).count()

    signals = (
        db.query(Signal)
        .filter(Signal.event_id == event.id)
        .order_by(Signal.confidence.desc())
        .all()
    )

    return EvidenceBundle(
        event_id=event.event_id,
        event_type=event.event_type,
        title=event.title,
        location=event.location_name,
        severity=event.severity,
        verification_status=event.verification_status,
        confidence=event.confidence,
        sources=event.sources,
        evidence_items=[
            {"kind": e.kind, "source": e.source, "strength": e.strength, "content": e.content, "is_demo": e.is_demo}
            for e in event.evidence
        ],
        impact_chains=[
            {
                "asset_symbol": link.asset_symbol,
                "chain": [n["node"] for n in link.chain],
                "exposure_score": link.exposure_score,
                "direction": link.direction,
                "rationale": link.rationale,
            }
            for link in event.impact_links
        ],
        historical_analogue_count=analogue_count,
        signals=[
            {
                "strategy": s.strategy,
                "asset_symbol": s.asset.symbol,
                "direction": s.direction,
                "confidence": s.confidence,
                "expected_horizon": s.expected_horizon,
                "pricing_status": s.pricing_status,
            }
            for s in signals
        ],
    )


def bundle_to_dict(bundle: EvidenceBundle) -> dict:
    return asdict(bundle)
