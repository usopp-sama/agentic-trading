"""Candlestick pattern detection — deterministic OHLC predicates.

Pure functions over an OHLC frame (``open``/``high``/``low``/``close``). Each
pattern is a small, independently importable predicate returning a *strength*
in ``(0, 1]`` (or ``None`` when it does not fire), so the tests can prove each
one on an engineered frame. ``detect`` runs them all against the most recent
bar(s) and returns the hits, most-recent-bar oriented.

Textbook-correct forms are used — e.g. engulfing compares *real bodies*
(open→close), not the full high→low range. Reversal patterns carry a signed
``direction`` (+1 bullish / −1 bearish / 0 indecision).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_EPS = 1e-9


@dataclass(frozen=True)
class PatternHit:
    name: str
    direction: int          # +1 bullish, -1 bearish, 0 indecision
    strength: float         # 0 < strength <= 1

    def as_dict(self) -> dict:
        return {"name": self.name, "direction": self.direction,
                "strength": round(self.strength, 3)}


# --- per-bar geometry helpers (all take plain floats) ----------------------

def _body(o: float, c: float) -> float:
    return abs(c - o)


def _rng(h: float, l: float) -> float:
    return max(h - l, 0.0)


def _upper_shadow(o: float, h: float, c: float) -> float:
    return h - max(o, c)


def _lower_shadow(o: float, l: float, c: float) -> float:
    return min(o, c) - l


def _is_bull(o: float, c: float) -> bool:
    return c > o


def _is_bear(o: float, c: float) -> bool:
    return c < o


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- single-bar patterns ---------------------------------------------------

def hammer(o: float, h: float, l: float, c: float) -> float | None:
    """Small body near the top with a long lower shadow (bullish reversal).

    Lower shadow ≥ 2× body, upper shadow ≤ body, non-trivial body.
    """
    body, rng = _body(o, c), _rng(h, l)
    if body <= _EPS or rng <= _EPS:
        return None
    lower, upper = _lower_shadow(o, l, c), _upper_shadow(o, h, c)
    if lower >= 2.0 * body and upper <= body:
        return _clamp01(lower / rng)
    return None


def shooting_star(o: float, h: float, l: float, c: float) -> float | None:
    """Small body near the bottom with a long upper shadow (bearish reversal)."""
    body, rng = _body(o, c), _rng(h, l)
    if body <= _EPS or rng <= _EPS:
        return None
    lower, upper = _lower_shadow(o, l, c), _upper_shadow(o, h, c)
    if upper >= 2.0 * body and lower <= body:
        return _clamp01(upper / rng)
    return None


def doji(o: float, h: float, l: float, c: float) -> float | None:
    """Open ≈ close: body ≤ 10% of the range (indecision)."""
    body, rng = _body(o, c), _rng(h, l)
    if rng <= _EPS:
        return None
    if body <= 0.1 * rng:
        return _clamp01(1.0 - body / rng)
    return None


def marubozu(o: float, h: float, l: float, c: float) -> float | None:
    """Body fills ≥ 90% of the range — negligible shadows (continuation)."""
    body, rng = _body(o, c), _rng(h, l)
    if rng <= _EPS or body <= _EPS:
        return None
    if body >= 0.9 * rng:
        return _clamp01(body / rng)
    return None


# --- two-bar patterns ------------------------------------------------------

def bullish_engulfing(prev: dict, cur: dict) -> float | None:
    """Prior bearish body strictly engulfed by a larger current bullish body."""
    if not _is_bear(prev["open"], prev["close"]):
        return None
    if not _is_bull(cur["open"], cur["close"]):
        return None
    # current real body strictly contains the prior real body
    if cur["open"] < prev["close"] and cur["close"] > prev["open"]:
        bp = _body(prev["open"], prev["close"])
        bc = _body(cur["open"], cur["close"])
        return _clamp01(bc / (bp + _EPS) - 1.0) or 0.5
    return None


def bearish_engulfing(prev: dict, cur: dict) -> float | None:
    """Prior bullish body strictly engulfed by a larger current bearish body."""
    if not _is_bull(prev["open"], prev["close"]):
        return None
    if not _is_bear(cur["open"], cur["close"]):
        return None
    if cur["open"] > prev["close"] and cur["close"] < prev["open"]:
        bp = _body(prev["open"], prev["close"])
        bc = _body(cur["open"], cur["close"])
        return _clamp01(bc / (bp + _EPS) - 1.0) or 0.5
    return None


# --- three-bar patterns ----------------------------------------------------

def _long_body(bar: dict) -> bool:
    return _body(bar["open"], bar["close"]) >= 0.5 * _rng(bar["high"], bar["low"])


def morning_star(b1: dict, b2: dict, b3: dict) -> float | None:
    """Bearish long → small-body star → bullish long closing past b1 midpoint."""
    body1 = _body(b1["open"], b1["close"])
    body2 = _body(b2["open"], b2["close"])
    if not (_is_bear(b1["open"], b1["close"]) and _long_body(b1)):
        return None
    if body2 > 0.5 * body1:                       # middle must be a small body
        return None
    if not (_is_bull(b3["open"], b3["close"]) and _long_body(b3)):
        return None
    mid1 = (b1["open"] + b1["close"]) / 2.0
    if b3["close"] > mid1:
        return _clamp01((b3["close"] - mid1) / (body1 + _EPS))
    return None


def evening_star(b1: dict, b2: dict, b3: dict) -> float | None:
    """Bullish long → small-body star → bearish long closing below b1 midpoint."""
    body1 = _body(b1["open"], b1["close"])
    body2 = _body(b2["open"], b2["close"])
    if not (_is_bull(b1["open"], b1["close"]) and _long_body(b1)):
        return None
    if body2 > 0.5 * body1:
        return None
    if not (_is_bear(b3["open"], b3["close"]) and _long_body(b3)):
        return None
    mid1 = (b1["open"] + b1["close"]) / 2.0
    if b3["close"] < mid1:
        return _clamp01((mid1 - b3["close"]) / (body1 + _EPS))
    return None


# --- driver ----------------------------------------------------------------

_SINGLE = [
    ("hammer", 1, hammer),
    ("shooting_star", -1, shooting_star),
    ("doji", 0, doji),
    ("marubozu", 0, marubozu),  # direction resolved from bar color below
]


def _row(df: pd.DataFrame, i: int) -> dict:
    r = df.iloc[i]
    return {"open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"])}


def detect(df: pd.DataFrame, lookback: int = 3) -> list[PatternHit]:
    """Detect candlestick patterns on the most recent bar(s).

    Returns every pattern that fires, most-significant grouping first
    (three-bar, then two-bar, then single-bar). ``lookback`` is accepted for
    API symmetry; detection always anchors on the final bar.
    """
    if df is None or df.empty:
        return []
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"detect needs an {col!r} column")

    hits: list[PatternHit] = []
    n = len(df)
    cur = _row(df, -1)

    # three-bar
    if n >= 3:
        b1, b2, b3 = _row(df, -3), _row(df, -2), _row(df, -1)
        s = morning_star(b1, b2, b3)
        if s is not None:
            hits.append(PatternHit("morning_star", 1, s))
        s = evening_star(b1, b2, b3)
        if s is not None:
            hits.append(PatternHit("evening_star", -1, s))

    # two-bar
    if n >= 2:
        prev = _row(df, -2)
        s = bullish_engulfing(prev, cur)
        if s is not None:
            hits.append(PatternHit("bullish_engulfing", 1, s))
        s = bearish_engulfing(prev, cur)
        if s is not None:
            hits.append(PatternHit("bearish_engulfing", -1, s))

    # single-bar
    for name, direction, fn in _SINGLE:
        s = fn(cur["open"], cur["high"], cur["low"], cur["close"])
        if s is not None:
            if name == "marubozu":
                direction = 1 if _is_bull(cur["open"], cur["close"]) else -1
            hits.append(PatternHit(name, direction, s))

    return hits
