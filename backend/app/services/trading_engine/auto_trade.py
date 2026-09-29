"""Automatic execution of fresh signals — the scheduled counterpart to a
manual "Execute Signal" click in the Trading Terminal. Every decision still
goes through the same RiskEngine -> BrokerAdapter path
(trading_engine.service.execute_signal); this module only decides *which*
signals to hand it and makes sure the same signal is never auto-traded
twice for a given portfolio.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.trading import AutoTradeAttempt, Portfolio
from app.services.trading_engine.service import execute_signal

logger = logging.getLogger("eye_of_horus")

# Only consider signals from the last N hours — an auto-trader acting on a
# stale, hours-old signal would be trading on outdated evidence.
FRESHNESS_WINDOW_HOURS = 6
# A generous safety cap, not a meaningful throttle: ranking candidates by
# confidence alone can bunch many same-direction signals (e.g. a macro event
# moving several correlated commodities bearish at once) at the very top,
# starving out actionable long entries further down the list. Excluding
# already-attempted signals at the query level (below) means each cycle only
# ever pays this cost for genuinely new signals, so the cap can stay high.
MAX_SIGNALS_PER_CYCLE = 200


@dataclass
class AutoTradeOutcome:
    portfolio_id: int
    signal_id: str
    approved: bool
    reason: str | None


def run_auto_trade_for_portfolio(db: Session, portfolio: Portfolio) -> list[AutoTradeOutcome]:
    if not portfolio.auto_trade_enabled or portfolio.mode == "research":
        return []

    since = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_WINDOW_HOURS)
    already_considered = (
        db.query(AutoTradeAttempt.signal_id)
        .filter(AutoTradeAttempt.portfolio_id == portfolio.id)
        .scalar_subquery()
    )
    signals = (
        db.query(Signal)
        .filter(
            Signal.signal_time >= since,
            Signal.confidence >= portfolio.auto_trade_min_confidence,
            Signal.id.notin_(already_considered),
        )
        .order_by(Signal.confidence.desc())
        .limit(MAX_SIGNALS_PER_CYCLE)
        .all()
    )

    outcomes: list[AutoTradeOutcome] = []
    for signal in signals:
        decision = execute_signal(db, portfolio, signal)
        db.add(
            AutoTradeAttempt(
                portfolio_id=portfolio.id,
                signal_id=signal.id,
                approved=decision.approved,
                reason=decision.reason,
            )
        )
        outcomes.append(
            AutoTradeOutcome(
                portfolio_id=portfolio.id,
                signal_id=signal.signal_id,
                approved=decision.approved,
                reason=decision.reason,
            )
        )
        if decision.approved:
            logger.info(
                "Auto-trade: portfolio=%s signal=%s asset=%s filled",
                portfolio.id,
                signal.signal_id,
                signal.asset.symbol,
            )

    return outcomes


def run_auto_trade_cycle(db: Session) -> list[AutoTradeOutcome]:
    portfolios = db.query(Portfolio).filter(Portfolio.auto_trade_enabled.is_(True)).all()
    all_outcomes: list[AutoTradeOutcome] = []
    for portfolio in portfolios:
        all_outcomes.extend(run_auto_trade_for_portfolio(db, portfolio))
    return all_outcomes
