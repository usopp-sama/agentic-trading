import numpy as np
import pandas as pd
import pytest

from quant.analysis import indicators
from quant.data.fetch import synthetic_prices


@pytest.fixture
def close() -> pd.Series:
    return synthetic_prices(n=120, seed=7)["close"]


def test_sma_matches_manual_mean(close):
    result = indicators.sma(close, 5)
    expected = close.iloc[:5].mean()
    assert result.iloc[4] == pytest.approx(expected)
    assert result.iloc[:4].isna().all()


def test_ema_first_value_equals_price(close):
    result = indicators.ema(close, 10)
    assert result.iloc[0] == pytest.approx(close.iloc[0])


def test_rsi_bounds(close):
    result = indicators.rsi(close, 14).dropna()
    assert result.between(0, 100).all()


def test_rsi_all_gains_is_100():
    rising = pd.Series(np.arange(1, 50, dtype=float))
    result = indicators.rsi(rising, 14).dropna()
    assert (result > 99.0).all()


def test_rsi_flat_series_is_50():
    flat = pd.Series([100.0] * 40)
    result = indicators.rsi(flat, 14).dropna()
    assert result.eq(50.0).all()


def test_macd_hist_is_difference(close):
    m = indicators.macd(close)
    assert m["hist"].equals(m["macd"] - m["signal"])


def test_macd_rejects_bad_windows(close):
    with pytest.raises(ValueError):
        indicators.macd(close, fast=26, slow=12)


def test_bollinger_pct_b_range(close):
    bb = indicators.bollinger_bands(close, 20, 2.0).dropna()
    assert len(bb) > 0
    assert (bb["upper"] >= bb["mid"]).all()
    assert (bb["mid"] >= bb["lower"]).all()


def test_invalid_window_raises(close):
    with pytest.raises(ValueError):
        indicators.sma(close, 0)
    with pytest.raises(ValueError):
        indicators.ema(close, -3)


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    return synthetic_prices(n=120, seed=7)


def test_atr_constant_range_converges_to_range():
    n = 60
    close = pd.Series([100.0] * n)
    df = pd.DataFrame(
        {"high": close + 1.0, "low": close - 1.0, "close": close}
    )
    result = indicators.atr(df, 14).dropna()
    # No gaps and a constant 2.0 true range -> ATR is exactly 2.0.
    assert result.iloc[-1] == pytest.approx(2.0)


def test_atr_positive_and_warmup(ohlcv):
    result = indicators.atr(ohlcv, 14)
    assert result.iloc[:13].isna().all()
    assert (result.dropna() > 0).all()


def test_donchian_excludes_current_bar():
    rising = pd.Series(np.arange(1.0, 61.0))
    df = pd.DataFrame({"high": rising, "low": rising - 0.5, "close": rising})
    ch = indicators.donchian(df, 20).dropna()
    aligned = df.loc[ch.index]
    # In a strictly rising series every close is a breakout of the
    # PRIOR 20-bar high; with an unshifted channel this would be equality.
    assert (aligned["close"] > ch["upper"]).all()


def test_donchian_bands_ordered(ohlcv):
    ch = indicators.donchian(ohlcv, 20).dropna()
    assert (ch["upper"] >= ch["mid"]).all()
    assert (ch["mid"] >= ch["lower"]).all()
