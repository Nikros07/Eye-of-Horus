"""Builds ImpactLink rows (the visual EVENT -> ... -> MARKET chain) and the
event's market_exposure summary from the rule table, scaled by the event's
own confidence and severity so a low-confidence report never shows up with
the same exposure weight as a verified one.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.event import Event, ImpactLink
from app.services.impact_engine.rules import rules_for

_SEVERITY_WEIGHT = {"low": 0.5, "medium": 0.75, "high": 1.0, "critical": 1.15}


def compute_exposure(base_exposure: float, event: Event) -> float:
    severity_weight = _SEVERITY_WEIGHT.get(event.severity, 0.75)
    score = base_exposure * (0.4 + 0.6 * event.confidence) * severity_weight
    return round(min(score, 1.0), 3)


def build_impact_links(db: Session, event: Event) -> list[ImpactLink]:
    db.query(ImpactLink).filter(ImpactLink.event_id == event.id).delete()

    links: list[ImpactLink] = []
    commodities: set[str] = set()
    assets: set[str] = set()
    exposure_summary: dict[str, float] = {}

    for rule in rules_for(event.event_type):
        exposure = compute_exposure(rule.base_exposure, event)
        chain_nodes = [{"node": node, "type": _infer_node_type(node, i, len(rule.chain))} for i, node in enumerate(rule.chain)]
        link = ImpactLink(
            event_id=event.id,
            asset_symbol=rule.asset_symbol,
            chain=chain_nodes,
            exposure_score=exposure,
            direction=rule.direction,
            rationale=rule.rationale,
        )
        db.add(link)
        links.append(link)
        assets.add(rule.asset_symbol)
        commodities.add(rule.chain[-1])
        exposure_summary[rule.asset_symbol] = exposure

    event.affected_assets = sorted(assets)
    event.affected_commodities = sorted(commodities)
    event.affected_supply_chains = sorted({node["node"] for link in links for node in link.chain if node["type"] == "supply_chain"})
    event.market_exposure = exposure_summary

    db.flush()
    return links


def _infer_node_type(node: str, index: int, length: int) -> str:
    if index == 0:
        return "event"
    if index == length - 1:
        return "market"
    if node in {"PORT", "REFINERY", "PIPELINE", "MINE", "OFFSHORE_PLATFORM", "GRID", "AIRPORT", "FACILITY", "FARMLAND", "FOREST_OPERATIONS"}:
        return "infrastructure"
    return "supply_chain"
