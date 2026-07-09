"""QA-2: candlestick patterns — each provable on an engineered frame."""

from __future__ import annotations

import pandas as pd

from quant.analysis.patterns import (
    bearish_engulfing,
    bullish_engulfing,
    detect,
)


def _frame(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows are (open, high, low, close)."""
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def _names(hits) -> set[str]:
    return {h.name for h in hits}


def _by_name(hits, name):
    return next(h for h in hits if h.name == name)


def test_bullish_engulfing():
    df = _frame([(105, 106, 99, 100), (99, 107, 98, 106)])
    hits = detect(df)
    assert "bullish_engulfing" in _names(hits)
    h = _by_name(hits, "bullish_engulfing")
    assert h.direction == 1 and 0.0 < h.strength <= 1.0


def test_bearish_engulfing():
    df = _frame([(100, 106, 99, 105), (106, 107, 98, 99)])
    hits = detect(df)
    assert "bearish_engulfing" in _names(hits)
    assert _by_name(hits, "bearish_engulfing").direction == -1


def test_bullish_engulfing_predicate_direct():
    prev = {"open": 105, "high": 106, "low": 99, "close": 100}
    cur = {"open": 99, "high": 107, "low": 98, "close": 106}
    assert bullish_engulfing(prev, cur) is not None
    assert bearish_engulfing(prev, cur) is None


def test_hammer():
    df = _frame([(100, 101.3, 90, 101)])
    hits = detect(df)
    assert "hammer" in _names(hits)
    assert _by_name(hits, "hammer").direction == 1


def test_shooting_star():
    df = _frame([(100, 110, 98.7, 99)])
    hits = detect(df)
    assert "shooting_star" in _names(hits)
    assert _by_name(hits, "shooting_star").direction == -1


def test_doji():
    df = _frame([(100, 102, 98, 100.05)])
    hits = detect(df)
    assert "doji" in _names(hits)
    assert _by_name(hits, "doji").direction == 0


def test_marubozu_bullish():
    df = _frame([(100, 110.1, 99.9, 110)])
    hits = detect(df)
    assert "marubozu" in _names(hits)
    assert _by_name(hits, "marubozu").direction == 1


def test_morning_star():
    df = _frame([
        (110, 110.5, 99.5, 100),   # bearish long
        (99, 99.2, 98.6, 98.8),    # small star
        (99, 107.5, 98.5, 107),    # bullish long, closes past b1 midpoint (105)
    ])
    hits = detect(df)
    assert "morning_star" in _names(hits)
    assert _by_name(hits, "morning_star").direction == 1


def test_evening_star():
    df = _frame([
        (100, 110.5, 99.5, 110),   # bullish long
        (111, 111.5, 110.8, 111.2),  # small star
        (110, 110.5, 102.5, 103),  # bearish long, closes below b1 midpoint (105)
    ])
    hits = detect(df)
    assert "evening_star" in _names(hits)
    assert _by_name(hits, "evening_star").direction == -1


def test_flat_frame_fires_nothing():
    df = _frame([(100, 101, 99, 100.4)] * 3)
    assert detect(df) == []


def test_empty_frame():
    assert detect(pd.DataFrame(columns=["open", "high", "low", "close"])) == []


def test_strengths_bounded():
    df = _frame([(100, 101.3, 90, 101)])
    for h in detect(df):
        assert 0.0 < h.strength <= 1.0
        assert set(h.as_dict()) == {"name", "direction", "strength"}
