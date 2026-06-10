"""Pluggable market-data sources.

All sources expose ``poll(symbol) -> DataFrame`` returning OHLCV indexed by
date. The synthetic source is stateful (it appends a fresh bar each poll) so
the system shows live-like movement and the volume-spike detector has
something to fire on - all with zero network. yfinance and Kite are drop-in
swaps via ``ATS_DATA_SOURCE``.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np
import pandas as pd

from quant.data.fetch import synthetic_prices


class DataSource(Protocol):
    def poll(self, symbol: str) -> pd.DataFrame: ...


def _seed_for(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % (2**32)


class SyntheticDataSource:
    """Deterministic GBM history that grows by one bar per poll."""

    def __init__(self, history: int = 300) -> None:
        self._history = history
        self._frames: dict[str, pd.DataFrame] = {}
        self._rng: dict[str, np.random.Generator] = {}

    def poll(self, symbol: str) -> pd.DataFrame:
        if symbol not in self._frames:
            seed = _seed_for(symbol)
            start_price = 50.0 + (seed % 4000) / 10.0
            self._frames[symbol] = synthetic_prices(
                n=self._history, start_price=start_price, seed=seed
            )
            self._rng[symbol] = np.random.default_rng(seed + 1)
            return self._frames[symbol]
        self._frames[symbol] = self._append_bar(symbol, self._frames[symbol])
        return self._frames[symbol]

    def _append_bar(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        rng = self._rng[symbol]
        last_close = float(df["close"].iloc[-1])
        ret = rng.normal(0.0004, 0.013)
        close = max(0.5, last_close * (1.0 + ret))
        intraday = abs(rng.normal(0.0, 0.008)) * close
        # ~6% of bars get a volume spike, so the detector has signal.
        base_vol = rng.integers(1_000_000, 3_000_000)
        volume = base_vol * (rng.uniform(4.0, 9.0) if rng.random() < 0.06 else 1.0)
        next_idx = df.index[-1] + pd.tseries.offsets.BDay(1)
        bar = pd.DataFrame(
            {
                "open": [last_close],
                "high": [close + intraday],
                "low": [close - intraday],
                "close": [close],
                "volume": [float(volume)],
            },
            index=pd.DatetimeIndex([next_idx], name="date"),
        )
        return pd.concat([df, bar]).tail(self._history + 90)


class YFinanceDataSource:
    """Live history from yfinance (Indian symbols use the .NS suffix)."""

    # 2y of dailies: the 200-SMA filter and 12-1 momentum need ~275 bars.
    def __init__(self, period: str = "2y") -> None:
        self._period = period

    def poll(self, symbol: str) -> pd.DataFrame:
        from quant.data.fetch import fetch_prices

        return fetch_prices(symbol, period=self._period)


class KiteDataSource:
    """Zerodha Kite source. Deferred until real-money is enabled."""

    def poll(self, symbol: str) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError(
            "Kite data source is not enabled in v1. Set ATS_DATA_SOURCE=synthetic "
            "or yfinance. Kite is wired in when the real-money gate opens."
        )


def build_data_source() -> DataSource:
    from ats.core.config import get_settings

    source = get_settings().data_source
    if source == "yfinance":
        return YFinanceDataSource()
    if source == "kite":
        return KiteDataSource()
    return SyntheticDataSource()
