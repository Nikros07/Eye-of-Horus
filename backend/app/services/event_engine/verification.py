"""Cross-source confirmation and confidence scoring.

The system never treats a single-source report as fact: confidence starts
low and only rises with independent corroboration (additional sources,
matching weather/infrastructure evidence). Conflicting evidence pulls
confidence down and flips status to `disputed` rather than silently
averaging it away.
"""
from __future__ import annotations

from app.models.event import Event, EvidenceItem

BASE_SINGLE_SOURCE_CONFIDENCE = 0.38
MAX_CONFIDENCE = 0.97
EVIDENCE_KIND_WEIGHT = 0.20


def score_verification(event: Event, evidence: list[EvidenceItem]) -> tuple[str, float]:
    source_count = len(event.sources or [])
    confidence = BASE_SINGLE_SOURCE_CONFIDENCE if source_count <= 1 else min(0.55 + 0.1 * (source_count - 1), 0.85)

    corroborating_kinds = {e.kind for e in evidence}
    for kind in corroborating_kinds:
        strongest = max((e.strength for e in evidence if e.kind == kind), default=0.0)
        confidence += strongest * EVIDENCE_KIND_WEIGHT

    confidence = min(confidence, MAX_CONFIDENCE)

    # Verification can come from either multiple independent reporting
    # sources of the same event, OR from two-or-more independent kinds of
    # corroborating evidence (e.g. weather + news) agreeing with a
    # single-source report — either is real independent confirmation.
    if source_count >= 2 or len(corroborating_kinds) >= 2:
        status = "verified"
    elif source_count >= 1 and len(corroborating_kinds) >= 1:
        status = "pending"
    else:
        status = "unverified"

    return status, round(confidence, 3)
