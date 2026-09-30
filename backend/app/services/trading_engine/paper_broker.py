"""PaperBroker — a BrokerAdapter that behaves like a real broker without
risking real capital. Simulates spread, slippage, and fees on every fill,
and persists a real ledger (Portfolio/Position/Trade rows) so paper
performance is auditable exactly like live performance would be.

MVP scope: long-only. Selling without an existing long position is rejected
rather than opening a synthetic short — short-side cash/margin accounting is
real complexity with no payoff until the product actually needs shorting,
so it is deliberately deferred rather than half-implemented.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.market import Asset
from app.models.trading import Portfolio, Position, Trade
from app.services.market_engine.base import MarketSource
from app.services.trading_engine.broker_base import (
    AccountInfo,
    BrokerAdapter,
    OrderInfo,
    OrderRequest,
    PositionInfo,
)
from app.services.trading_engine.risk_engine import portfolio_equity

SPREAD_BPS = 5.0
SLIPPAGE_BPS = 3.0
FEE_BPS = 2.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PaperBroker(BrokerAdapter):
    name = "PAPER_BROKER"
    mode = "paper"

    def __init__(self, db: Session, portfolio: Portfolio, market_source: MarketSource) -> None:
        self.db = db
        self.portfolio = portfolio
        self.market_source = market_source

    def _price_lookup(self, symbol: str) -> float | None:
        try:
            return self.market_source.get_quote(symbol).price
        except Exception:  # noqa: BLE001
            return None

    def get_account(self) -> AccountInfo:
        equity = portfolio_equity(self.db, self.portfolio, self._price_lookup)
        return AccountInfo(cash=self.portfolio.cash, equity=equity, buying_power=self.portfolio.cash, mode="paper")

    def get_positions(self) -> list[PositionInfo]:
        out = []
        for pos in self.portfolio.positions:
            if pos.closed_at is not None:
                continue
            current = self._price_lookup(pos.asset.symbol) or pos.avg_entry_price
            unrealized = (current - pos.avg_entry_price) * pos.qty * (1 if pos.side == "long" else -1)
            out.append(
                PositionInfo(
                    asset_symbol=pos.asset.symbol,
                    side=pos.side,
                    qty=pos.qty,
                    avg_entry_price=pos.avg_entry_price,
                    current_price=current,
                    unrealized_pnl=round(unrealized, 2),
                )
            )
        return out

    def get_orders(self) -> list[OrderInfo]:
        return [
            OrderInfo(
                order_id=str(t.id),
                asset_symbol=t.asset.symbol,
                side=t.side,
                qty=t.qty,
                order_type=t.order_type,
                status=t.status,
                filled_price=t.price,
                submitted_at=t.created_at,
            )
            for t in sorted(self.portfolio.trades, key=lambda x: x.created_at, reverse=True)
        ]

    def place_order(self, request: OrderRequest) -> OrderInfo:
        asset = self.db.query(Asset).filter(Asset.symbol == request.asset_symbol).one_or_none()
        if asset is None:
            return self._rejected(request, "Unknown asset symbol.")

        quote = self.market_source.get_quote(request.asset_symbol)
        mid = quote.price
        if mid <= 0:
            return self._rejected(request, "No valid market price available.")

        sign = 1 if request.side == "buy" else -1
        fill_price = mid * (1 + ((SPREAD_BPS + SLIPPAGE_BPS) / 10_000) * sign)
        fees = request.qty * fill_price * (FEE_BPS / 10_000)

        # Queried directly rather than scanned from self.portfolio.positions:
        # that relationship collection is cached in memory once loaded, so a
        # position opened earlier in this same session (e.g. an already-flushed
        # but uncommitted buy from a prior signal in the same auto-trade cycle)
        # would not show up in it, and a second buy of the same asset would
        # silently open a duplicate Position instead of adding to the existing
        # one — reproduced in test_two_buys_of_the_same_asset_in_one_session_merge_into_one_position.
        existing = (
            self.db.query(Position)
            .filter(Position.portfolio_id == self.portfolio.id, Position.asset_id == asset.id, Position.closed_at.is_(None))
            .one_or_none()
        )

        if request.side == "buy":
            cost = request.qty * fill_price + fees
            if cost > self.portfolio.cash:
                return self._rejected(request, "Insufficient paper cash for this order.")
            self.portfolio.cash -= cost
            if existing is None:
                existing = Position(
                    portfolio_id=self.portfolio.id,
                    asset_id=asset.id,
                    side="long",
                    qty=request.qty,
                    avg_entry_price=fill_price,
                    signal_id=request.signal_id,
                    event_id=request.event_id,
                    opened_at=_now(),
                )
                self.db.add(existing)
            else:
                total_qty = existing.qty + request.qty
                existing.avg_entry_price = ((existing.avg_entry_price * existing.qty) + (fill_price * request.qty)) / total_qty
                existing.qty = total_qty
            realized_pnl = None
        else:  # sell
            if existing is None or existing.side != "long" or existing.qty < request.qty:
                return self._rejected(request, "No sufficient long position to sell (short-selling not supported in MVP).")
            proceeds = request.qty * fill_price - fees
            self.portfolio.cash += proceeds
            realized_pnl = (fill_price - existing.avg_entry_price) * request.qty - fees
            existing.qty -= request.qty
            if existing.qty <= 1e-9:
                existing.closed_at = _now()

        trade = Trade(
            portfolio_id=self.portfolio.id,
            asset_id=asset.id,
            side=request.side,
            qty=request.qty,
            price=round(fill_price, 4),
            fees=round(fees, 2),
            slippage=SLIPPAGE_BPS,
            order_type=request.order_type,
            status="filled",
            signal_id=request.signal_id,
            event_id=request.event_id,
            realized_pnl=round(realized_pnl, 2) if realized_pnl is not None else None,
            mode="paper",
            created_at=_now(),
        )
        self.db.add(trade)
        self.db.flush()

        return OrderInfo(
            order_id=str(trade.id),
            asset_symbol=request.asset_symbol,
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status="filled",
            filled_price=trade.price,
            submitted_at=trade.created_at,
        )

    def cancel_order(self, order_id: str) -> bool:
        # Every paper order fills immediately (no resting order book in MVP)
        return False

    def close_position(self, asset_symbol: str) -> OrderInfo | None:
        asset = self.db.query(Asset).filter(Asset.symbol == asset_symbol).one_or_none()
        if asset is None:
            return None
        # Same direct-query reasoning as place_order() above.
        position = (
            self.db.query(Position)
            .filter(Position.portfolio_id == self.portfolio.id, Position.asset_id == asset.id, Position.closed_at.is_(None))
            .one_or_none()
        )
        if position is None:
            return None
        return self.place_order(OrderRequest(asset_symbol=asset_symbol, side="sell", qty=position.qty))

    def get_market_data(self, asset_symbol: str) -> dict:
        quote = self.market_source.get_quote(asset_symbol)
        return {
            "symbol": asset_symbol,
            "price": quote.price,
            "change_pct": quote.change_pct,
            "estimated_spread_bps": SPREAD_BPS,
            "ts": quote.ts.isoformat(),
            "is_demo": quote.is_demo,
        }

    def _rejected(self, request: OrderRequest, reason: str) -> OrderInfo:
        return OrderInfo(
            order_id=f"REJECTED-{uuid.uuid4().hex[:8]}",
            asset_symbol=request.asset_symbol,
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=f"rejected: {reason}",
            filled_price=None,
            submitted_at=_now(),
        )
