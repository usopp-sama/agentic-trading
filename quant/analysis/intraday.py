"""Intraday analytics: VWAP and top movers.

Pure functions. ``vwap`` needs an intraday OHLCV frame; ``daily_vwap_approx``
degrades to a single daily bar when no intraday cache exists. ``movers`` ranks
gainers/losers and applies the "is this move real?" volume filter — a move only
counts as *volume-confirmed* when the day's volume clears a multiple of its
20-day average, which drops the zero-volume penny-stock spikes.
"""

from __future__ import annotations

from typing import Mapping, NamedTuple

import numpy as np
import pandas as pd


class DayStat(NamedTuple):
    pct_change: float        # day % change vs previous close
    volume: float            # today's volume
    avg_volume_20d: float    # trailing 20-session average volume


def _typical_price(df: pd.DataFrame) -> pd.Series:
    return (df["high"] + df["low"] + df["close"]) / 3.0


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume-Weighted Average Price: ``cum(TP·V) / cum(V)``, TP=(H+L+C)/3.

    Returns a Series aligned to ``df``. Where cumulative volume is zero the
    value is NaN (undefined), never a divide-by-zero crash.
    """
    for col in ("high", "low", "close", "volume"):
        if col not in df.columns:
            raise ValueError(f"vwap needs a {col!r} column")
    if df.empty:
        return pd.Series(dtype=float)
    tp = _typical_price(df)
    cum_pv = (tp * df["volume"]).cumsum()
    cum_v = df["volume"].cumsum().replace(0.0, np.nan)
    return cum_pv / cum_v


def daily_vwap_approx(df: pd.DataFrame) -> float:
    """Single-day VWAP approximation from the last daily bar: its typical price
    (H+L+C)/3. Used when no intraday bars are cached."""
    if df is None or df.empty:
        return float("nan")
    row = df.iloc[-1]
    return float((row["high"] + row["low"] + row["close"]) / 3.0)


def _entry(symbol: str, st: DayStat) -> dict:
    vx = None
    if st.avg_volume_20d and st.avg_volume_20d > 0:
        vx = round(st.volume / st.avg_volume_20d, 2)
    return {
        "symbol": symbol,
        "pct_change": round(float(st.pct_change), 4),
        "volume": float(st.volume),
        "volume_x": vx,
    }


def movers(latest: Mapping[str, DayStat], min_volume_x: float = 1.5) -> dict:
    """Rank the day's movers and flag which moves are volume-confirmed.

    Returns ``{"gainers", "losers", "volume_confirmed"}``:
    - **gainers**: positive % change, high → low
    - **losers**: negative % change, low → high (most negative first)
    - **volume_confirmed**: moves where ``volume ≥ min_volume_x ×
      avg_volume_20d`` (the junk filter), ranked by absolute % change
    """
    entries = {sym: _entry(sym, st) for sym, st in latest.items()}
    gainers = sorted(
        (e for e in entries.values() if e["pct_change"] > 0),
        key=lambda e: e["pct_change"], reverse=True,
    )
    losers = sorted(
        (e for e in entries.values() if e["pct_change"] < 0),
        key=lambda e: e["pct_change"],
    )
    confirmed = sorted(
        (e for e in entries.values()
         if e["volume_x"] is not None and e["volume_x"] >= min_volume_x
         and e["pct_change"] != 0),
        key=lambda e: abs(e["pct_change"]), reverse=True,
    )
    return {"gainers": gainers, "losers": losers, "volume_confirmed": confirmed}
