"""Shared ORM -> dict serializers. Kept as plain functions rather than a
second Pydantic schema layer on top of the SQLAlchemy models — for an API
this size the duplication would outweigh the benefit; FastAPI serializes
plain dicts to JSON directly.
"""
from __future__ import annotations

from app.models.event import Event, EvidenceItem, ImpactLink
from app.models.market import Asset
from app.models.signal import Signal
from app.models.trading import Position, Trade
from app.services.market_engine.factory import get_market_source


def serialize_evidence(item: EvidenceItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "source": item.source,
        "source_url": item.source_url,
        "content": item.content,
        "strength": item.strength,
        "retrieved_at": item.retrieved_at.isoformat(),
        "availability_time": item.availability_time.isoformat(),
        "is_demo": item.is_demo,
    }


def serialize_impact_link(link: ImpactLink) -> dict:
    return {
        "id": link.id,
        "asset_symbol": link.asset_symbol,
        "chain": link.chain,
        "exposure_score": link.exposure_score,
        "direction": link.direction,
        "rationale": link.rationale,
    }


def serialize_event(event: Event, include_details: bool = False) -> dict:
    data = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "title": event.title,
        "timestamp": event.timestamp.isoformat(),
        "first_seen": event.first_seen.isoformat(),
        "last_updated": event.last_updated.isoformat(),
        "lat": event.lat,
        "lon": event.lon,
        "location_name": event.location_name,
        "magnitude": event.magnitude,
        "severity": event.severity,
        "sources": event.sources,
        "verification_status": event.verification_status,
        "confidence": event.confidence,
        "affected_assets": event.affected_assets,
        "affected_commodities": event.affected_commodities,
        "affected_supply_chains": event.affected_supply_chains,
        "market_exposure": event.market_exposure,
        "is_demo": event.is_demo,
        "data_version": event.data_version,
        "availability_time": event.availability_time.isoformat(),
    }
    if include_details:
        data["evidence"] = [serialize_evidence(e) for e in event.evidence]
        data["impact_links"] = [serialize_impact_link(link) for link in event.impact_links]
    return data


def serialize_signal(signal: Signal) -> dict:
    return {
        "signal_id": signal.signal_id,
        "event_id": signal.event.event_id if signal.event else None,
        "asset_symbol": signal.asset.symbol,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "expected_horizon": signal.expected_horizon,
        "reasoning": signal.reasoning,
        "evidence": signal.evidence,
        "strategy": signal.strategy,
        "strategy_version": signal.strategy_version,
        "pricing_status": signal.pricing_status,
        "signal_time": signal.signal_time.isoformat(),
    }


def serialize_asset_with_quote(asset: Asset) -> dict:
    market_source = get_market_source()
    try:
        quote = market_source.get_quote(asset.symbol)
        quote_data = {"price": quote.price, "change_pct": quote.change_pct, "is_demo": quote.is_demo, "ts": quote.ts.isoformat()}
    except Exception:  # noqa: BLE001
        quote_data = {"price": None, "change_pct": None, "is_demo": market_source.is_demo, "ts": None}

    return {
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_class": asset.asset_class,
        "currency": asset.currency,
        **quote_data,
    }


def serialize_position(position: Position, current_price: float | None) -> dict:
    price = current_price if current_price is not None else position.avg_entry_price
    sign = 1 if position.side == "long" else -1
    unrealized = (price - position.avg_entry_price) * position.qty * sign
    return {
        "id": position.id,
        "asset_symbol": position.asset.symbol,
        "side": position.side,
        "qty": position.qty,
        "avg_entry_price": position.avg_entry_price,
        "current_price": price,
        "unrealized_pnl": round(unrealized, 2),
        "stop_price": position.stop_price,
        "target_price": position.target_price,
        "opened_at": position.opened_at.isoformat(),
        "event_id": position.event_id,
        "signal_id": position.signal_id,
    }


def serialize_trade(trade: Trade) -> dict:
    return {
        "id": trade.id,
        "asset_symbol": trade.asset.symbol,
        "side": trade.side,
        "qty": trade.qty,
        "price": trade.price,
        "fees": trade.fees,
        "slippage": trade.slippage,
        "status": trade.status,
        "realized_pnl": trade.realized_pnl,
        "mode": trade.mode,
        "created_at": trade.created_at.isoformat(),
        "signal_id": trade.signal_id,
        "event_id": trade.event_id,
    }
