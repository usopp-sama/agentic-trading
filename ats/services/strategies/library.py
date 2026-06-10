"""Concrete strategies built on the ``quant`` analytics toolkit."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import indicators
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import Strategy


class SmaCrossover(Strategy):
    id = "sma_crossover"
    min_bars = 60

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        self.fast, self.slow = fast, slow

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.slow + 1:
            return None
        close = df["close"]
        fast = indicators.sma(close, self.fast).iloc[-1]
        slow = indicators.sma(close, self.slow).iloc[-1]
        if np.isnan(fast) or np.isnan(slow) or slow == 0:
            return None
        gap = float((fast - slow) / slow)
        if gap > 0:
            return self._signal(symbol, Stance.BUY, min(1.0, gap * 20), gap=round(gap, 4))
        if gap < 0:
            return self._signal(symbol, Stance.SELL, min(1.0, -gap * 20), gap=round(gap, 4))
        return self._signal(symbol, Stance.NEUTRAL, 0.0, gap=0.0)


class BollingerMeanReversion(Strategy):
    id = "mean_reversion"
    min_bars = 40

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        self.window, self.num_std = window, num_std

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.window + 2:
            return None
        bb = indicators.bollinger_bands(df["close"], self.window, self.num_std)
        pct_b = float(bb["pct_b"].iloc[-1])
        if np.isnan(pct_b):
            return None
        # Below the lower band -> oversold -> buy; above upper -> overbought -> sell.
        if pct_b < 0.0:
            return self._signal(symbol, Stance.BUY, min(1.0, -pct_b), pct_b=round(pct_b, 3))
        if pct_b > 1.0:
            return self._signal(symbol, Stance.SELL, min(1.0, pct_b - 1.0), pct_b=round(pct_b, 3))
        return self._signal(symbol, Stance.NEUTRAL, 0.0, pct_b=round(pct_b, 3))


class VolumeBreakout(Strategy):
    id = "volume_breakout"
    min_bars = 30

    def __init__(self, lookback: int = 20, vol_z: float = 2.0) -> None:
        self.lookback, self.vol_z = lookback, vol_z

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.lookback + 2:
            return None
        close = df["close"]
        vol = df["volume"]
        recent_high = close.iloc[-(self.lookback + 1):-1].max()
        vol_hist = vol.iloc[-(self.lookback + 1):-1]
        mean, std = float(vol_hist.mean()), float(vol_hist.std(ddof=0))
        if std <= 0:
            return None
        z = (float(vol.iloc[-1]) - mean) / std
        breakout = float(close.iloc[-1]) > float(recent_high)
        if z >= self.vol_z and breakout:
            return self._signal(
                symbol, Stance.BUY, min(1.0, z / 5.0), vol_z=round(z, 2), breakout=True
            )
        return self._signal(symbol, Stance.NEUTRAL, 0.0, vol_z=round(z, 2), breakout=breakout)


def default_strategies() -> list[Strategy]:
    return [SmaCrossover(), BollingerMeanReversion(), VolumeBreakout()]
