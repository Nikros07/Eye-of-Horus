from __future__ import annotations

from app.services.signal_engine.strategies.baseline import BaselineStrategy
from app.services.signal_engine.strategies.event_momentum import EventMomentumStrategy
from app.services.signal_engine.strategies.mean_reversion import MeanReversionStrategy
from app.services.signal_engine.strategies.multi_signal import MultiSignalStrategy
from app.services.signal_engine.strategies.supply_chain_disruption import SupplyChainDisruptionStrategy
from app.services.signal_engine.strategy_base import StrategyBase

STRATEGY_REGISTRY: dict[str, type[StrategyBase]] = {
    EventMomentumStrategy.name: EventMomentumStrategy,
    MeanReversionStrategy.name: MeanReversionStrategy,
    SupplyChainDisruptionStrategy.name: SupplyChainDisruptionStrategy,
    MultiSignalStrategy.name: MultiSignalStrategy,
    BaselineStrategy.name: BaselineStrategy,
}

# Strategies that require an event to fire (all but the baseline).
EVENT_DRIVEN_STRATEGIES = [n for n in STRATEGY_REGISTRY if n != BaselineStrategy.name]


def get_strategy(name: str) -> StrategyBase:
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown strategy: {name}")
    return cls()


def all_strategies() -> list[StrategyBase]:
    return [cls() for cls in STRATEGY_REGISTRY.values()]
