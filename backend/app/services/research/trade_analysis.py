"""AI Trade Analysis — explains one specific Signal in the structured
LONG BIAS / CONFIDENCE / KEY EVIDENCE / RISKS / INVALIDATION / HORIZON /
HISTORICAL ANALOGUES / MARKET ALREADY PRICED format. The strategy already
made the trade decision from fixed rules; this module only explains it —
it never overrides or re-decides direction or sizing.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.services.research.evidence import build_evidence_bundle
from app.services.research.synthesizer import synthesize_research


@dataclass
class TradeAnalysis:
    signal_id: str
    asset_symbol: str
    bias: str  # "LONG BIAS" / "SHORT BIAS" / "NEUTRAL"
    confidence: float
    key_evidence: list[str]
    risks: list[str]
    invalidation: list[str]
    expected_horizon: str
    historical_analogues: str
    market_already_priced: str
    source: str


def analyze_signal(db: Session, signal: Signal) -> TradeAnalysis:
    bundle = build_evidence_bundle(db, signal.event) if signal.event else None
    if bundle is None:
        return TradeAnalysis(
            signal_id=signal.signal_id,
            asset_symbol=signal.asset.symbol,
            bias="LONG BIAS" if signal.direction == "bullish" else "SHORT BIAS",
            confidence=signal.confidence,
            key_evidence=[signal.reasoning] if signal.reasoning else ["INSUFFICIENT EVIDENCE"],
            risks=["No linked event — signal provenance is limited."],
            invalidation=["INSUFFICIENT EVIDENCE"],
            expected_horizon=signal.expected_horizon,
            historical_analogues="INSUFFICIENT EVIDENCE",
            market_already_priced="NO",
            source="deterministic",
        )

    research = synthesize_research(bundle)
    key_evidence = research.observed + research.derived
    bias = "LONG BIAS" if signal.direction == "bullish" else ("SHORT BIAS" if signal.direction == "bearish" else "NEUTRAL")

    return TradeAnalysis(
        signal_id=signal.signal_id,
        asset_symbol=signal.asset.symbol,
        bias=bias,
        confidence=signal.confidence,
        key_evidence=key_evidence,
        risks=research.risks,
        invalidation=research.invalidation,
        expected_horizon=signal.expected_horizon,
        historical_analogues=research.historical_analogues,
        market_already_priced=research.market_already_priced,
        source=research.source,
    )
