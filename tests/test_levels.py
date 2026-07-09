"""QA-1: pivot points + Fibonacci retracements — exact hand-computed values."""

from __future__ import annotations

import pandas as pd
import pytest

from quant.analysis.levels import (
    classic_pivots,
    fibonacci_retracements,
    nearest_level,
    session_anchor,
)


def test_classic_pivots_exact():
    # H=110 L=90 C=100 -> P=100, clean integer levels.
    p = classic_pivots(110, 90, 100)
    assert p.pivot == 100.0
    assert p.r1 == 110.0 and p.r2 == 120.0 and p.r3 == 130.0
    assert p.s1 == 90.0 and p.s2 == 80.0 and p.s3 == 70.0


def test_pivots_are_monotone_ordered():
    p = classic_pivots(110, 90, 100)
    lv = p.all_levels()
    assert lv == sorted(lv)  # s3 < s2 < s1 < pivot < r1 < r2 < r3
    assert set(p.as_dict()) == {"pivot", "r1", "r2", "r3", "s1", "s2", "s3"}


def test_fibonacci_down_from_high():
    fib = fibonacci_retracements(200, 100, "down")
    assert fib["0.236"] == pytest.approx(176.4)
    assert fib["0.382"] == pytest.approx(161.8)
    assert fib["0.5"] == pytest.approx(150.0)
    assert fib["0.618"] == pytest.approx(138.2)
    assert fib["0.786"] == pytest.approx(121.4)


def test_fibonacci_up_from_low():
    fib = fibonacci_retracements(200, 100, "up")
    assert fib["0.236"] == pytest.approx(123.6)
    assert fib["0.5"] == pytest.approx(150.0)
    assert fib["0.618"] == pytest.approx(161.8)


def test_fibonacci_tolerates_swapped_inputs():
    a = fibonacci_retracements(100, 200, "down")
    b = fibonacci_retracements(200, 100, "down")
    assert a == b


def test_fibonacci_bad_direction_raises():
    with pytest.raises(ValueError):
        fibonacci_retracements(200, 100, "sideways")


def test_nearest_level_above_is_positive():
    lvl, dist = nearest_level(101.0, [90, 100, 110, 120])
    assert lvl == 100.0
    assert dist == pytest.approx(1.0)  # price 1% above the level (support)


def test_nearest_level_below_is_negative():
    lvl, dist = nearest_level(99.0, [90, 100, 110, 120])
    assert lvl == 100.0
    assert dist == pytest.approx(-1.0)  # price 1% below the level (resistance)


def test_nearest_level_empty_raises():
    with pytest.raises(ValueError):
        nearest_level(100.0, [])


def _two_week_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=14, freq="D")  # Mon Jan 1 .. Sun Jan 14
    return pd.DataFrame(
        {
            "high": [10, 11, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26],
            "low": [5] * 7 + [8] * 7,
            "close": [9] * 7 + [19, 19, 19, 19, 19, 19, 25],
        },
        index=idx,
    )


def test_session_anchor_daily():
    h, l, c = session_anchor(_two_week_frame(), "D")
    assert (h, l, c) == (26.0, 8.0, 25.0)


def test_session_anchor_weekly():
    # Last complete week (Jan 8-14): high 26, low 8, close 25.
    h, l, c = session_anchor(_two_week_frame(), "W")
    assert (h, l, c) == (26.0, 8.0, 25.0)


def test_session_anchor_empty_raises():
    with pytest.raises(ValueError):
        session_anchor(pd.DataFrame(), "D")
