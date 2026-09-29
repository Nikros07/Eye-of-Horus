from __future__ import annotations

from datetime import timedelta

from app.services.market_engine.base import Bar


def return_over_window(bars: list[Bar], hours: int) -> float | None:
    """Percent return over the last `hours` of the given bar series."""
    if len(bars) < 2:
        return None
    cutoff = bars[-1].ts - timedelta(hours=hours)
    window = [b for b in bars if b.ts >= cutoff]
    if len(window) < 2 or window[0].open == 0:
        return None
    return (window[-1].close - window[0].open) / window[0].open


def realized_volatility(bars: list[Bar], hours: int = 24) -> float | None:
    if len(bars) < 3:
        return None
    cutoff = bars[-1].ts - timedelta(hours=hours)
    window = [b for b in bars if b.ts >= cutoff]
    if len(window) < 3:
        return None
    rets = [
        (window[i].close - window[i - 1].close) / window[i - 1].close
        for i in range(1, len(window))
        if window[i - 1].close
    ]
    if not rets:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return var**0.5
