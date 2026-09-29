"""Production MarketSource backed by Yahoo Finance via the `yfinance`
package. Free tier, no API key, but does need outbound network access that
this sandboxed dev environment does not have — hence DemoMarketSource
covers local development and tests. Swapping providers later (a paid
vendor, IEX, etc.) means adding one more adapter behind MarketSource, not
touching callers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.market_engine.base import Bar, MarketSource, Quote


class YFinanceMarketSource(MarketSource):
    name = "YFINANCE"
    is_demo = False

    def get_history(self, symbol: str, start: datetime, end: datetime, interval: str = "1d") -> list[Bar]:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval)
        bars: list[Bar] = []
        for ts, row in df.iterrows():
            bars.append(
                Bar(
                    ts=ts.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
        return bars

    def get_quote(self, symbol: str) -> Quote:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        price = float(fast["lastPrice"])
        prev_close = float(fast.get("previousClose", price))
        change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
        return Quote(symbol=symbol, price=price, change_pct=round(change_pct, 3), ts=datetime.now(timezone.utc), is_demo=False)
