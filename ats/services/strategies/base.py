"""Strategy base class and the signal contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ats.core.schemas import SignalModel, Stance


class Strategy(ABC):
    id: str
    # Style tag consumed by the regime tilt: "trend" | "momentum" |
    # "mean_reversion" | "stat_arb" | "other". Mismatched styles get their
    # conviction dampened (never boosted) by the current regime.
    style: str = "other"
    min_bars: int = 60

    @abstractmethod
    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        """Return a signal for ``symbol`` given its OHLCV history, or None."""

    def _signal(
        self, symbol: str, stance: Stance, conviction: float, **features
    ) -> SignalModel:
        return make_signal(self.id, symbol, stance, conviction, **features)


class UniverseStrategy(ABC):
    """A strategy that needs several symbols' histories at once.

    Pairs/stat-arb and cross-sectional ranking strategies cannot be
    expressed as a function of a single symbol's bars; they evaluate the
    whole universe and may emit signals for multiple symbols per pass.
    """

    id: str
    style: str = "other"
    min_bars: int = 60

    @abstractmethod
    def evaluate_universe(
        self, history: dict[str, pd.DataFrame]
    ) -> list[SignalModel]:
        """Return signals across the universe given per-symbol OHLCV."""

    def symbols(self) -> list[str]:
        """Symbols this strategy needs; empty means the whole watchlist."""
        return []

    def _signal(
        self, symbol: str, stance: Stance, conviction: float, **features
    ) -> SignalModel:
        return make_signal(self.id, symbol, stance, conviction, **features)


def make_signal(
    strategy_id: str, symbol: str, stance: Stance, conviction: float, **features
) -> SignalModel:
    return SignalModel(
        strategy=strategy_id,
        symbol=symbol,
        stance=stance,
        conviction=max(0.0, min(1.0, conviction)),
        features=features,
    )
