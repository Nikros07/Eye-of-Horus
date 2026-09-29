"""Strategy interface shared by live signal generation and the backtester.

A strategy is a pure function of a StrategyContext -> list[SignalCandidate].
Because it never reaches into the database or the clock itself, the exact
same strategy code runs unmodified in real time (full history available) and
inside the backtester (history sliced to `as_of` by the TemporalGuard) —
that equivalence is what makes the backtest results honest.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.event import Event, EvidenceItem, ImpactLink
    from app.services.market_engine.base import Bar


@dataclass
class SignalCandidate:
    asset_symbol: str
    direction: str  # bullish / bearish / neutral
    confidence: float  # 0-1
    expected_horizon: str  # e.g. "6-24h"
    reasoning: str
    evidence: list[str]
    strategy: str
    strategy_version: str


@dataclass
class StrategyContext:
    as_of: datetime
    event: "Event | None" = None
    impact_links: list["ImpactLink"] = field(default_factory=list)
    evidence_items: list["EvidenceItem"] = field(default_factory=list)
    price_history: dict[str, list["Bar"]] = field(default_factory=dict)  # symbol -> bars with ts <= as_of
    historical_analogue_count: int = 0


class StrategyBase(ABC):
    name: str = "unnamed"
    version: str = "1.0.0"
    description: str = ""
    required_features: list[str] = []
    timeframe: str = "1h"

    @abstractmethod
    def generate(self, ctx: StrategyContext) -> list[SignalCandidate]:
        raise NotImplementedError

    def position_size(self, confidence: float, equity: float, max_position_pct: float) -> float:
        """Default sizing: scale allocation proportionally with confidence.
        Strategies already gate candidate generation on their own minimum
        confidence, so sizing must not apply a second, differently
        calibrated floor on top of that."""
        return equity * max_position_pct * max(confidence, 0.0)
