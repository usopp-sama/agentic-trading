"""Strategy base class and the signal contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ats.core.schemas import SignalModel, Stance


class Strategy(ABC):
    id: str
    min_bars: int = 60

    @abstractmethod
    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        """Return a signal for ``symbol`` given its OHLCV history, or None."""

    def _signal(
        self, symbol: str, stance: Stance, conviction: float, **features
    ) -> SignalModel:
        return SignalModel(
            strategy=self.id,
            symbol=symbol,
            stance=stance,
            conviction=max(0.0, min(1.0, conviction)),
            features=features,
        )
