"""Price levels: classic pivot points and Fibonacci retracements.

Pure functions over plain floats / a daily OHLC frame — no I/O, no settings.
These feed the Charts overlays, the technical-summary confluence check
(``quant.analysis.summary``), and level-aware strategies. Nothing here fetches
data; a service hands in the prior session's high/low/close.

References: the classic (floor-trader) pivot formulas and the standard
Fibonacci retracement ratios. Both are deterministic arithmetic — the tests
pin every value against a hand computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

# The canonical Fibonacci retracement ratios (0 and 1 are the endpoints of the
# move and intentionally excluded — they are the swing high/low themselves).
FIB_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)


@dataclass(frozen=True)
class PivotLevels:
    """Classic pivot point with three resistances and three supports."""

    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float

    def as_dict(self) -> dict[str, float]:
        return {
            "pivot": self.pivot,
            "r1": self.r1, "r2": self.r2, "r3": self.r3,
            "s1": self.s1, "s2": self.s2, "s3": self.s3,
        }

    def all_levels(self) -> list[float]:
        """Every level as a flat list (for ``nearest_level`` scans)."""
        return [self.s3, self.s2, self.s1, self.pivot, self.r1, self.r2, self.r3]


def classic_pivots(high: float, low: float, close: float) -> PivotLevels:
    """Floor-trader ("classic") pivot points from a prior session's H/L/C.

    ::

        P  = (H + L + C) / 3
        R1 = 2P - L        S1 = 2P - H
        R2 = P + (H - L)   S2 = P - (H - L)
        R3 = H + 2(P - L)  S3 = L - 2(H - P)
    """
    h, l, c = float(high), float(low), float(close)
    p = (h + l + c) / 3.0
    rng = h - l
    return PivotLevels(
        pivot=p,
        r1=2.0 * p - l,
        r2=p + rng,
        r3=h + 2.0 * (p - l),
        s1=2.0 * p - h,
        s2=p - rng,
        s3=l - 2.0 * (h - p),
    )


def fibonacci_retracements(
    high: float, low: float, direction: str = "down"
) -> dict[str, float]:
    """Fibonacci retracement levels for a swing between ``high`` and ``low``.

    ``direction="down"`` retraces *down from the high* (a pullback after a
    rally): ``level = high - (high - low) * ratio``. ``direction="up"``
    retraces *up from the low* (a bounce after a decline):
    ``level = low + (high - low) * ratio``. Keys are the ratio strings
    ``"0.236" … "0.786"``.
    """
    h, l = float(high), float(low)
    if h < l:
        h, l = l, h  # tolerate swapped inputs; a range is a range
    rng = h - l
    d = direction.lower().strip()
    if d not in ("down", "up"):
        raise ValueError(f"direction must be 'down' or 'up', got {direction!r}")
    out: dict[str, float] = {}
    for ratio in FIB_RATIOS:
        key = f"{ratio:g}"
        out[key] = (h - rng * ratio) if d == "down" else (l + rng * ratio)
    return out


def nearest_level(price: float, levels: Iterable[float]) -> tuple[float, float]:
    """Return ``(nearest_level, signed_distance_pct)`` for ``price``.

    ``signed_distance_pct = (price - level) / level * 100`` — **positive means
    price is above the level** (level acting as support), negative means price
    is below (level acting as resistance). "Nearest" is by absolute price gap.
    Raises ``ValueError`` on an empty level set.
    """
    p = float(price)
    candidates = [float(x) for x in levels if x is not None]
    if not candidates:
        raise ValueError("nearest_level requires at least one level")
    nearest = min(candidates, key=lambda lv: abs(p - lv))
    signed_pct = (p - nearest) / nearest * 100.0 if nearest != 0.0 else 0.0
    return nearest, signed_pct


def session_anchor(df: pd.DataFrame, period: str = "D") -> tuple[float, float, float]:
    """The most recent completed period's ``(high, low, close)`` from a daily
    OHLC frame — the input for the *next* period's pivots.

    ``period="D"`` returns the last daily row. ``"W"``/``"M"`` resample the
    daily frame to weekly/monthly and return the last aggregated period. The
    frame must have a ``DatetimeIndex`` for weekly/monthly aggregation and
    ``high``/``low``/``close`` columns.
    """
    if df is None or df.empty:
        raise ValueError("session_anchor requires a non-empty frame")
    for col in ("high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"session_anchor needs a {col!r} column")
    p = period.upper().strip()
    if p == "D":
        row = df.iloc[-1]
        return float(row["high"]), float(row["low"]), float(row["close"])
    rule = {"W": "W", "M": "ME"}.get(p)
    if rule is None:
        raise ValueError(f"period must be 'D', 'W' or 'M', got {period!r}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("weekly/monthly anchor needs a DatetimeIndex")
    agg = df.resample(rule).agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last")
    ).dropna()
    if agg.empty:
        raise ValueError("no complete period to anchor on")
    row = agg.iloc[-1]
    return float(row["high"]), float(row["low"]), float(row["close"])
