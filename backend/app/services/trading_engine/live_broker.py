"""LiveBroker — deliberately an interface-only safety stub in this build.

No real broker credentials exist anywhere in this repository, and none
should ever be accepted from the frontend. This class exists so the
BrokerAdapter contract has a live-mode implementation to point at once a
real broker (Alpaca, Interactive Brokers, etc.) is integrated — every
method refuses to act unless LIVE_TRADING_ENABLED=true AND a concrete
broker connection has been wired in, which it deliberately has not been.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.services.trading_engine.broker_base import (
    AccountInfo,
    BrokerAdapter,
    OrderInfo,
    OrderRequest,
    PositionInfo,
)


class LiveTradingNotConfiguredError(RuntimeError):
    pass


class LiveBroker(BrokerAdapter):
    name = "LIVE_BROKER_STUB"
    mode = "live"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.live_trading_enabled:
            raise LiveTradingNotConfiguredError(
                "Live trading is disabled (LIVE_TRADING_ENABLED=false). This is the default and safe state."
            )
        # A real deployment would establish a broker connection here and
        # verify it before allowing any of the methods below to proceed.
        raise LiveTradingNotConfiguredError(
            "LIVE_TRADING_ENABLED=true but no real broker connection is configured in this build. "
            "Refusing to place live orders. Implement a concrete broker SDK integration before enabling this path."
        )

    def get_account(self) -> AccountInfo:
        raise LiveTradingNotConfiguredError("Live broker not configured.")

    def get_positions(self) -> list[PositionInfo]:
        raise LiveTradingNotConfiguredError("Live broker not configured.")

    def get_orders(self) -> list[OrderInfo]:
        raise LiveTradingNotConfiguredError("Live broker not configured.")

    def place_order(self, request: OrderRequest) -> OrderInfo:
        raise LiveTradingNotConfiguredError("Live broker not configured. DO NOT PLACE ORDER.")

    def cancel_order(self, order_id: str) -> bool:
        raise LiveTradingNotConfiguredError("Live broker not configured.")

    def close_position(self, asset_symbol: str) -> OrderInfo | None:
        raise LiveTradingNotConfiguredError("Live broker not configured.")

    def get_market_data(self, asset_symbol: str) -> dict:
        raise LiveTradingNotConfiguredError("Live broker not configured.")
