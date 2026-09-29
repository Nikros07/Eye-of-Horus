"""Event-driven backtester with enforced temporal integrity.

For every event in the requested period, in chronological order, a
TemporalGuard is built from that event's `availability_time`. The strategy
under test only ever sees evidence, price history, and historical-analogue
counts whose own availability_time/timestamp is <= that instant — exactly
what a live system would have known at that moment. The one place the
simulation deliberately looks forward is *after* a signal is generated, to
find the entry fill and, `horizon` hours later, the exit fill and thereby
grade the trade — that is outcome evaluation, not decision-making, and is
not look-ahead bias.

If a LookAheadBiasError is raised anywhere in that loop, the backtest is
marked look_ahead_bias_detected=True and halts rather than silently
producing an inflated result — this is the automatic test the platform's
temporal-integrity requirement calls for, not just documentation of intent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.market import Asset, PriceBar
from app.services.market_engine.base import Bar
from app.services.quant_engine.metrics import TradeResult, compute_metrics
from app.services.quant_engine.temporal import LookAheadBiasError, TemporalGuard
from app.services.signal_engine.registry import get_strategy
from app.services.signal_engine.strategy_base import StrategyContext


@dataclass
class BacktestParams:
    strategy_name: str
    period_start: datetime
    period_end: datetime
    asset_symbols: list[str] | None = None
    initial_capital: float = 10_000.0
    max_position_pct: float = 0.10
    transaction_cost_bps: float = 5.0
    slippage_bps: float = 3.0
    sample_interval_hours: int = 6


@dataclass
class BacktestResult:
    trades: list[TradeResult] = field(default_factory=list)
    equity_curve: list[tuple[str, float]] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    signal_stats: dict = field(default_factory=dict)
    look_ahead_bias_detected: bool = False
    error: str | None = None


_HORIZON_RE = re.compile(r"(\d+)\s*-?\s*(\d+)?\s*h", re.IGNORECASE)


def _parse_horizon_hours(horizon: str) -> float:
    match = _HORIZON_RE.search(horizon)
    if not match:
        return 24.0
    lo = float(match.group(1))
    hi = float(match.group(2)) if match.group(2) else lo
    return (lo + hi) / 2


def _position_size(confidence: float, capital: float, max_position_pct: float) -> float:
    # Proportional to the strategy's own confidence output. Strategies
    # already gate candidate generation on their own minimum-confidence
    # thresholds before a candidate ever reaches here, so a second,
    # differently-calibrated floor (e.g. "confidence must exceed 0.5") would
    # silently zero out perfectly valid lower-conviction signals.
    return capital * max_position_pct * max(confidence, 0.0)


def _load_bars(db: Session, asset: Asset, start: datetime, end: datetime) -> list[PriceBar]:
    return (
        db.query(PriceBar)
        .filter(PriceBar.asset_id == asset.id, PriceBar.ts >= start, PriceBar.ts <= end)
        .order_by(PriceBar.ts.asc())
        .all()
    )


def run_backtest(db: Session, params: BacktestParams) -> BacktestResult:
    result = BacktestResult()

    try:
        strategy = get_strategy(params.strategy_name)
    except KeyError as exc:
        result.error = str(exc)
        return result

    assets_by_symbol = {a.symbol: a for a in db.query(Asset).all()}
    all_bars_by_symbol: dict[str, list[PriceBar]] = {
        symbol: _load_bars(db, asset, params.period_start, params.period_end)
        for symbol, asset in assets_by_symbol.items()
    }

    events = (
        db.query(Event)
        .filter(Event.availability_time >= params.period_start, Event.availability_time <= params.period_end)
        .order_by(Event.availability_time.asc())
        .all()
    )

    signal_count = 0
    signal_confidences: list[float] = []
    signal_directions: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
    event_types_covered: set[str] = set()

    try:
        for event in events:
            as_of = event.availability_time
            guard = TemporalGuard(as_of=as_of)
            guard.check(event.availability_time, f"event:{event.event_id}")

            # Evidence has a single timestamp (availability_time): not yet
            # having arrived by `as_of` is normal and expected, so it is
            # silently excluded rather than treated as a violation.
            available_evidence = guard.filter_available(list(event.evidence), lambda e: e.availability_time)

            # Price bars are different: `ts` (when the bar nominally
            # happened) and `availability_time` (when it actually became
            # knowable) can diverge — e.g. a restated/backfilled price. A
            # bar with ts <= as_of is expected to also have
            # availability_time <= as_of; if it doesn't, that IS look-ahead
            # bias and must raise, not be silently dropped. guard.check is
            # therefore the actual gate here, not a redundant assertion
            # after the fact.
            price_history: dict[str, list[Bar]] = {}
            for link in event.impact_links:
                candidate_bars = [b for b in all_bars_by_symbol.get(link.asset_symbol, []) if b.ts <= as_of]
                for b in candidate_bars:
                    guard.check(b.availability_time, f"price_bar:{link.asset_symbol}")
                price_history[link.asset_symbol] = [
                    Bar(ts=b.ts, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume) for b in candidate_bars
                ]

            analogue_count = (
                db.query(Event)
                .filter(Event.event_type == event.event_type, Event.id != event.id, Event.availability_time <= as_of)
                .count()
            )

            ctx = StrategyContext(
                as_of=as_of,
                event=event,
                impact_links=list(event.impact_links),
                evidence_items=available_evidence,
                price_history=price_history,
                historical_analogue_count=analogue_count,
            )

            candidates = strategy.generate(ctx)
            event_types_covered.add(event.event_type)

            for candidate in candidates:
                if params.asset_symbols and candidate.asset_symbol not in params.asset_symbols:
                    continue

                signal_count += 1
                signal_confidences.append(candidate.confidence)
                signal_directions[candidate.direction] = signal_directions.get(candidate.direction, 0) + 1

                asset = assets_by_symbol.get(candidate.asset_symbol)
                if asset is None:
                    continue

                symbol_bars = all_bars_by_symbol.get(candidate.asset_symbol, [])
                entry_bar = next((b for b in symbol_bars if b.ts > as_of), None)
                if entry_bar is None:
                    continue

                horizon_hours = _parse_horizon_hours(candidate.expected_horizon)
                target_exit_time = entry_bar.ts + timedelta(hours=horizon_hours)
                exit_bar = next((b for b in symbol_bars if b.ts >= target_exit_time), None)
                if exit_bar is None:
                    # trade would extend past the data window we have; skip rather
                    # than fabricate an outcome
                    continue

                sign = 1.0 if candidate.direction == "bullish" else -1.0
                slippage_mult = 1 + (params.slippage_bps / 10_000) * sign
                entry_price = entry_bar.open * slippage_mult
                exit_slippage_mult = 1 - (params.slippage_bps / 10_000) * sign
                exit_price = exit_bar.close * exit_slippage_mult

                notional = _position_size(candidate.confidence, params.initial_capital, params.max_position_pct)
                if notional <= 0 or entry_price <= 0:
                    continue
                qty = notional / entry_price

                fee_entry = notional * (params.transaction_cost_bps / 10_000)
                fee_exit = qty * exit_price * (params.transaction_cost_bps / 10_000)
                fees = fee_entry + fee_exit

                raw_return = ((exit_price - entry_price) / entry_price) * sign
                pnl = notional * raw_return - fees

                path_bars = [b for b in symbol_bars if entry_bar.ts <= b.ts <= exit_bar.ts]
                if path_bars:
                    excursions = [((b.close - entry_price) / entry_price) * sign for b in path_bars]
                    mfe = max(excursions)
                    mae = min(excursions)
                else:
                    mfe = mae = raw_return

                result.trades.append(
                    TradeResult(
                        asset_symbol=candidate.asset_symbol,
                        direction=candidate.direction,
                        entry_price=round(entry_price, 4),
                        exit_price=round(exit_price, 4),
                        qty=round(qty, 6),
                        fees=round(fees, 2),
                        pnl=round(pnl, 2),
                        opened_at=entry_bar.ts.isoformat(),
                        closed_at=exit_bar.ts.isoformat(),
                        mfe=round(mfe, 4),
                        mae=round(mae, 4),
                        strategy=candidate.strategy,
                        event_id=event.id,
                    )
                )
    except LookAheadBiasError as exc:
        result.look_ahead_bias_detected = True
        result.error = str(exc)
        return result

    result.equity_curve = _build_equity_curve(result.trades, params)
    result.metrics = compute_metrics(result.trades, result.equity_curve, params.initial_capital)
    result.signal_stats = {
        "total_signals": signal_count,
        "signals_traded": len(result.trades),
        "avg_confidence": round(sum(signal_confidences) / len(signal_confidences), 3) if signal_confidences else None,
        "by_direction": signal_directions,
        "event_types_covered": sorted(event_types_covered),
        "high_confidence_losing_trades": sum(1 for t in result.trades if t.pnl <= 0 and t.qty > 0),
    }
    return result


def _build_equity_curve(trades: list[TradeResult], params: BacktestParams) -> list[tuple[str, float]]:
    curve: list[tuple[str, float]] = []
    ts = params.period_start
    step = timedelta(hours=params.sample_interval_hours)

    parsed_trades = [
        (t, datetime.fromisoformat(t.opened_at), datetime.fromisoformat(t.closed_at))
        for t in trades
    ]

    while ts <= params.period_end:
        equity = params.initial_capital
        for trade, opened_at, closed_at in parsed_trades:
            if closed_at <= ts:
                equity += trade.pnl
            elif opened_at <= ts < closed_at:
                progress = (ts - opened_at) / (closed_at - opened_at) if closed_at > opened_at else 1.0
                equity += trade.pnl * progress
        curve.append((ts.isoformat(), round(equity, 2)))
        ts += step

    return curve
