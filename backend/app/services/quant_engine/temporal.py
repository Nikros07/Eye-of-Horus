"""Temporal integrity enforcement.

This is the single most important correctness guarantee in the whole
platform: a backtest is only meaningful if, at every simulated point in
time, the strategy sees exactly the data that would really have been known
then — never anything whose `availability_time` is in its future.
`TemporalGuard.check` is called at every point the backtester hands data to
a strategy; violating it raises immediately rather than silently producing
an inflated result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class LookAheadBiasError(Exception):
    """Raised when a strategy or the backtester tries to use data that would
    not yet have been available at the simulated point in time."""


@dataclass
class TemporalGuard:
    as_of: datetime
    violations: list[str] = field(default_factory=list)

    def check(self, availability_time: datetime | None, label: str = "data") -> None:
        if availability_time is None:
            return
        if availability_time > self.as_of:
            msg = f"LOOK-AHEAD BIAS DETECTED: {label} availability_time={availability_time.isoformat()} > as_of={self.as_of.isoformat()}"
            self.violations.append(msg)
            raise LookAheadBiasError(msg)

    def filter_available(self, items: list, availability_getter) -> list:
        """Return only items whose availability_time <= as_of, without raising —
        used for bulk filtering (e.g. evidence lists) where callers intend to
        drop future data rather than treat its presence as a hard bug."""
        return [item for item in items if availability_getter(item) is None or availability_getter(item) <= self.as_of]
