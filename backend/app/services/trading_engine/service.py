"""Trading service — the only place that turns a Signal into an order. It
always goes RiskEngine -> BrokerAdapter, never the reverse, and always
resolves the broker for the portfolio's own mode (research portfolios never
reach a broker at all).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.signal import Signal
from app.models.trading import Portfolio
from app.services.market_engine.factory import get_market_source
from app.services.signal_engine.strategy_base import confidence_scaled_notional
from app.services.trading_engine.broker_base import BrokerAdapter, OrderInfo, OrderRequest
from app.services.trading_engine.paper_broker import PaperBroker
from app.services.trading_engine.risk_engine import check_order, get_or_create_risk_config, portfolio_equity


@dataclass
class TradeDecision:
    approved: bool
    reason: str | None
    order: OrderInfo | None


def get_broker_for_portfolio(db: Session, portfolio: Portfolio) -> BrokerAdapter:
    if portfolio.mode == "live":
        from app.services.trading_engine.live_broker import LiveBroker

        return LiveBroker()
    if get_settings().broker_provider == "alpaca":
        from app.services.trading_engine.alpaca_broker import AlpacaBroker

        return AlpacaBroker(db, portfolio)
    market_source = get_market_source()
    return PaperBroker(db, portfolio, market_source)


def execute_signal(db: Session, portfolio: Portfolio, signal: Signal, override_notional: float | None = None) -> TradeDecision:
    if portfolio.mode == "research":
        return TradeDecision(False, "Portfolio is in RESEARCH mode — analysis only, no orders are ever placed.", None)

    market_source = get_market_source()
    price_lookup = market_source.get_price
    current_price = price_lookup(signal.asset.symbol)

    config = get_or_create_risk_config(db, portfolio)
    equity = portfolio_equity(db, portfolio, price_lookup)
    notional = override_notional or confidence_scaled_notional(signal.confidence, equity, config.max_position_size_pct)

    check = check_order(db, portfolio, signal.asset.symbol, "buy" if signal.direction == "bullish" else "sell", notional, current_price, price_lookup)
    if not check.approved:
        return TradeDecision(False, check.reason, None)

    try:
        broker = get_broker_for_portfolio(db, portfolio)
    except Exception as exc:  # noqa: BLE001 — LiveTradingNotConfiguredError or similar
        return TradeDecision(False, f"DO NOT PLACE ORDER: {exc}", None)

    side = "buy" if signal.direction == "bullish" else "sell"
    order = broker.place_order(
        OrderRequest(
            asset_symbol=signal.asset.symbol,
            side=side,
            qty=check.approved_qty,
            signal_id=signal.id,
            event_id=signal.event_id,
        )
    )
    return TradeDecision(order.status == "filled", None if order.status == "filled" else order.status, order)
