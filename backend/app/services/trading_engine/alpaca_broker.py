"""AlpacaBroker — a BrokerAdapter backed by Alpaca's real paper-trading API.

Unlike PaperBroker (which simulates fills in-process against our own
ledger), this submits real orders against Alpaca's own paper-trading
account: free to sign up, no real money ever involved, but real order
matching, real market data, and a real brokerage ledger you can also see
in Alpaca's own dashboard.

Hardcoded to Alpaca's PAPER base URL (paper-api.alpaca.markets) — never
configurable from here, so a misconfigured or copy-pasted live API key
simply fails authentication against this endpoint rather than ever
reaching Alpaca's live trading API (paper and live keys are tied to
separate Alpaca accounts, so a live key cannot "accidentally" trade
paper or vice versa). This is deliberately a *second paper venue*, not a
path to real-money trading: that line is drawn at Portfolio.mode, and
"live" mode still only ever resolves to LiveBroker (see live_broker.py),
completely untouched by this file.

After every order, local Portfolio.cash and Position rows are resynced
from Alpaca's own authoritative account/positions snapshot, so
RiskEngine's pre-trade checks (which read local state and are otherwise
unmodified by this integration) never drift from what Alpaca actually
holds.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.market import Asset
from app.models.trading import Portfolio, Position, Trade
from app.services.trading_engine.broker_base import (
    AccountInfo,
    BrokerAdapter,
    OrderInfo,
    OrderRequest,
    PositionInfo,
)

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
DATA_BASE_URL = "https://data.alpaca.markets"
# Market orders on Alpaca's paper venue usually settle within a second or
# two during market hours; a short bounded poll gets the real fill price
# for the common case without ever blocking a request indefinitely.
ORDER_POLL_ATTEMPTS = 5
ORDER_POLL_DELAY_SECONDS = 0.6
TERMINAL_ORDER_STATUSES = {"filled", "canceled", "expired", "rejected", "done_for_day"}


class AlpacaNotConfiguredError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class AlpacaBroker(BrokerAdapter):
    name = "ALPACA_PAPER"
    mode = "paper"

    def __init__(self, db: Session, portfolio: Portfolio) -> None:
        settings = get_settings()
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise AlpacaNotConfiguredError(
                "BROKER_PROVIDER=alpaca but ALPACA_API_KEY/ALPACA_SECRET_KEY are not set."
            )
        self.db = db
        self.portfolio = portfolio
        self._client = httpx.Client(
            base_url=PAPER_BASE_URL,
            headers={
                "APCA-API-KEY-ID": settings.alpaca_api_key,
                "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            },
            timeout=10.0,
        )

    def get_account(self) -> AccountInfo:
        r = self._client.get("/v2/account")
        r.raise_for_status()
        data = r.json()
        return AccountInfo(
            cash=float(data["cash"]),
            equity=float(data["portfolio_value"]),
            buying_power=float(data["buying_power"]),
            mode="paper",
        )

    def get_positions(self) -> list[PositionInfo]:
        r = self._client.get("/v2/positions")
        r.raise_for_status()
        out: list[PositionInfo] = []
        for p in r.json():
            qty = float(p["qty"])
            out.append(
                PositionInfo(
                    asset_symbol=p["symbol"],
                    side="long" if qty >= 0 else "short",
                    qty=abs(qty),
                    avg_entry_price=float(p["avg_entry_price"]),
                    current_price=float(p["current_price"]),
                    unrealized_pnl=round(float(p["unrealized_pl"]), 2),
                )
            )
        return out

    def get_orders(self) -> list[OrderInfo]:
        r = self._client.get("/v2/orders", params={"status": "all", "limit": 50})
        r.raise_for_status()
        return [self._to_order_info(o) for o in r.json()]

    def place_order(self, request: OrderRequest) -> OrderInfo:
        if request.qty <= 0:
            return self._rejected(request, "Order quantity must be positive.")

        order_type = request.order_type if request.order_type in ("market", "limit", "stop") else "market"
        body = {
            "symbol": request.asset_symbol,
            "qty": str(request.qty),
            "side": request.side,
            "type": order_type,
            "time_in_force": "day",
        }
        if request.limit_price:
            body["limit_price"] = str(request.limit_price)
        if request.stop_price:
            body["stop_price"] = str(request.stop_price)

        try:
            r = self._client.post("/v2/orders", json=body)
        except httpx.HTTPError as exc:
            return self._rejected(request, f"Alpaca request failed: {exc}")

        if r.status_code >= 400:
            return self._rejected(request, f"Alpaca rejected the order: {self._error_message(r)}")

        order = self._poll_until_terminal(r.json()["id"])
        info = self._to_order_info(order)
        self._record_local_trade(request, info)
        self._sync_local_ledger()
        return info

    def cancel_order(self, order_id: str) -> bool:
        r = self._client.delete(f"/v2/orders/{order_id}")
        return r.status_code in (200, 204)

    def close_position(self, asset_symbol: str) -> OrderInfo | None:
        r = self._client.delete(f"/v2/positions/{asset_symbol}")
        if r.status_code >= 400:
            return None
        order = self._poll_until_terminal(r.json()["id"])
        info = self._to_order_info(order)
        self._sync_local_ledger()
        return info

    def get_market_data(self, asset_symbol: str) -> dict:
        try:
            r = httpx.get(
                f"{DATA_BASE_URL}/v2/stocks/{asset_symbol}/trades/latest",
                headers=self._client.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            trade = r.json()["trade"]
            return {
                "symbol": asset_symbol,
                "price": float(trade["p"]),
                "ts": trade["t"],
                "is_demo": False,
                "source": "alpaca",
            }
        except Exception as exc:  # noqa: BLE001 — market data here is best-effort, never blocks trading
            return {"symbol": asset_symbol, "price": None, "error": str(exc), "is_demo": False, "source": "alpaca"}

    # -- internals --

    def _poll_until_terminal(self, order_id: str) -> dict:
        order: dict = {}
        for _ in range(ORDER_POLL_ATTEMPTS):
            r = self._client.get(f"/v2/orders/{order_id}")
            if r.status_code >= 400:
                break
            order = r.json()
            if order.get("status") in TERMINAL_ORDER_STATUSES:
                break
            time.sleep(ORDER_POLL_DELAY_SECONDS)
        return order

    def _to_order_info(self, order: dict) -> OrderInfo:
        filled_price = order.get("filled_avg_price")
        qty = order.get("qty") or order.get("filled_qty") or 0
        return OrderInfo(
            order_id=str(order.get("id", "")),
            asset_symbol=order.get("symbol", ""),
            side=order.get("side", ""),
            qty=float(qty),
            order_type=order.get("type", "market"),
            status=order.get("status", "unknown"),
            filled_price=float(filled_price) if filled_price else None,
            submitted_at=_parse_ts(order.get("submitted_at")) or _now(),
        )

    def _error_message(self, response: httpx.Response) -> str:
        try:
            return response.json().get("message", response.text)
        except Exception:  # noqa: BLE001
            return response.text

    def _record_local_trade(self, request: OrderRequest, info: OrderInfo) -> None:
        if info.status != "filled" or info.filled_price is None:
            return
        asset = self.db.query(Asset).filter(Asset.symbol == request.asset_symbol).one_or_none()
        if asset is None:
            return
        self.db.add(
            Trade(
                portfolio=self.portfolio,
                asset_id=asset.id,
                side=request.side,
                qty=info.qty,
                price=info.filled_price,
                fees=0.0,
                slippage=0.0,
                order_type=info.order_type,
                status="filled",
                signal_id=request.signal_id,
                event_id=request.event_id,
                mode="paper",
                created_at=_now(),
            )
        )

    def _sync_local_ledger(self) -> None:
        """Pulls Alpaca's own account/positions snapshot and overwrites the
        local Portfolio.cash + Position rows to match, so RiskEngine's
        pre-trade checks never drift from what Alpaca actually holds.
        """
        account = self.get_account()
        self.portfolio.cash = account.cash

        live_positions = {p.asset_symbol: p for p in self.get_positions()}
        existing_rows = {
            pos.asset.symbol: pos
            for pos in self.db.query(Position)
            .filter(Position.portfolio_id == self.portfolio.id, Position.closed_at.is_(None))
            .all()
        }

        for symbol, info in live_positions.items():
            asset = self.db.query(Asset).filter(Asset.symbol == symbol).one_or_none()
            if asset is None:
                # Alpaca holds a position in a symbol our local catalog
                # doesn't know about — nothing local to mirror it onto.
                continue
            row = existing_rows.get(symbol)
            if row is None:
                row = Position(
                    portfolio=self.portfolio,
                    asset_id=asset.id,
                    side=info.side,
                    qty=info.qty,
                    avg_entry_price=info.avg_entry_price,
                    opened_at=_now(),
                )
                self.db.add(row)
            else:
                row.side = info.side
                row.qty = info.qty
                row.avg_entry_price = info.avg_entry_price

        for symbol, row in existing_rows.items():
            if symbol not in live_positions:
                row.closed_at = _now()

        self.db.flush()

    def _rejected(self, request: OrderRequest, reason: str) -> OrderInfo:
        return OrderInfo(
            order_id="REJECTED",
            asset_symbol=request.asset_symbol,
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=f"rejected: {reason}",
            filled_price=None,
            submitted_at=_now(),
        )
