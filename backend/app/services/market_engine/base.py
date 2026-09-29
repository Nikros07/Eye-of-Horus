"""MarketSource interface. Every price provider (demo generator, yfinance,
a future paid vendor) implements this same shape so the rest of the system
never couples to one vendor. `market_data_provider` in Settings selects the
active implementation via `get_market_source()`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Quote:
    symbol: str
    price: float
    change_pct: float
    ts: datetime
    is_demo: bool = False


class MarketSource(ABC):
    name: str
    is_demo: bool = False

    @abstractmethod
    def get_history(self, symbol: str, start: datetime, end: datetime, interval: str = "1d") -> list[Bar]:
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_price(self, symbol: str) -> float:
        return self.get_quote(symbol).price

    def get_volume(self, symbol: str) -> float:
        history = self.get_history(symbol, start=_days_ago(2), end=_now())
        return history[-1].volume if history else 0.0


def _now() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    from datetime import timedelta

    return _now() - timedelta(days=n)
