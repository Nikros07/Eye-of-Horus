from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.market_engine.base import MarketSource
from app.services.market_engine.demo_adapter import DemoMarketSource


@lru_cache
def get_market_source() -> MarketSource:
    settings = get_settings()
    if settings.market_data_provider == "yfinance":
        from app.services.market_engine.yfinance_adapter import YFinanceMarketSource

        return YFinanceMarketSource()
    return DemoMarketSource()
