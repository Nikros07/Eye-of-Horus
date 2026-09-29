"""BrokerAdapter interface. Every execution venue — the paper simulator now,
a real broker later — implements this same shape. Strategies and the
trading service never call a broker SDK directly, so swapping brokers is a
config change, never a rewrite, and no broker credentials ever need to
reach the frontend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AccountInfo:
    cash: float
    equity: float
    buying_power: float
    mode: str  # paper / live


@dataclass
class PositionInfo:
    asset_symbol: str
    side: str
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float


@dataclass
class OrderInfo:
    order_id: str
    asset_symbol: str
    side: str  # buy / sell
    qty: float
    order_type: str
    status: str
    filled_price: float | None
    submitted_at: datetime


@dataclass
class OrderRequest:
    asset_symbol: str
    side: str
    qty: float
    order_type: str = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    signal_id: int | None = None
    event_id: int | None = None


class BrokerAdapter(ABC):
    name: str
    mode: str

    @abstractmethod
    def get_account(self) -> AccountInfo: ...

    @abstractmethod
    def get_positions(self) -> list[PositionInfo]: ...

    @abstractmethod
    def get_orders(self) -> list[OrderInfo]: ...

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderInfo: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def close_position(self, asset_symbol: str) -> OrderInfo | None: ...

    @abstractmethod
    def get_market_data(self, asset_symbol: str) -> dict: ...
