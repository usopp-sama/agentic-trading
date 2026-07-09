"""QA-3: technical summary composite — labels correct across regimes."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis.summary import summary_label, technical_summary


def _frame(close: np.ndarray, volume: np.ndarray | None = None) -> pd.DataFrame:
    """OHLCV frame from a close path; bullish/bearish body follows the step."""
    n = len(close)
    prev = np.concatenate([[close[0]], close[:-1]])
    open_ = prev
    high = np.maximum(open_, close) * 1.002
    low = np.minimum(open_, close) * 0.998
    if volume is None:
        volume = np.full(n, 1_000_000.0)
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def test_strong_uptrend_is_strong_buy():
    n = 260
    close = 100.0 * (1.004 ** np.arange(n))
    vol = 1_000_000.0 * (1.0 + 0.001 * np.arange(n))  # slowly rising
    ts = technical_summary("UP", _frame(close, vol))
    assert ts.label == "strong_buy"
    assert ts.bulls >= 6
    assert ts.score == ts.bulls - ts.bears


def test_crash_is_strong_sell():
    n = 260
    close = 200.0 * (0.996 ** np.arange(n))
    vol = 1_000_000.0 * (1.0 + 0.001 * np.arange(n))
    ts = technical_summary("DN", _frame(close, vol))
    assert ts.label == "strong_sell"
    assert ts.bears >= 6


def test_flat_is_neutral():
    n = 260
    close = np.full(n, 100.0)
    df = _frame(close)
    # perfectly flat: no bodies/ranges
    df["open"] = 100.0
    df["high"] = 100.0
    df["low"] = 100.0
    ts = technical_summary("FLAT", df)
    assert ts.label == "neutral"
    assert ts.score == 0


def test_always_twelve_components_even_on_short_history():
    close = 100.0 + np.arange(10, dtype=float)  # only 10 bars
    ts = technical_summary("SHORT", _frame(close))
    assert len(ts.components) == 12
    # SMA-200 unavailable -> value None, vote 0
    sma200 = next(c for c in ts.components if c["name"] == "price_vs_sma200")
    assert sma200["value"] is None and sma200["vote"] == 0


def test_components_have_shape():
    close = 100.0 * (1.004 ** np.arange(260))
    ts = technical_summary("X", _frame(close))
    for c in ts.components:
        assert set(c) == {"name", "vote", "value"}
        assert c["vote"] in (-1, 0, 1)


def test_label_thresholds():
    assert summary_label(6) == "strong_buy"
    assert summary_label(5) == "buy"
    assert summary_label(3) == "buy"
    assert summary_label(2) == "neutral"
    assert summary_label(-2) == "neutral"
    assert summary_label(-3) == "sell"
    assert summary_label(-5) == "sell"
    assert summary_label(-6) == "strong_sell"


def test_score_equals_bulls_minus_bears():
    close = 100.0 * (1.002 ** np.arange(120))
    ts = technical_summary("Y", _frame(close))
    assert ts.score == ts.bulls - ts.bears
    assert ts.bulls + ts.bears + ts.neutral == 12
