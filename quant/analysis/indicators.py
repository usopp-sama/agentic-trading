"""Technical indicators.

All functions operate on a pandas ``Series`` of prices (typically the
close) indexed by date, and return a ``Series`` (or ``DataFrame`` for
multi-line indicators) aligned to the same index. They are pure and
side-effect free, which makes them trivial to unit test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(prices: pd.Series, window: int = 20) -> pd.Series:
    """Simple moving average."""
    _validate_window(window)
    return prices.rolling(window=window, min_periods=window).mean()


def ema(prices: pd.Series, window: int = 20) -> pd.Series:
    """Exponential moving average."""
    _validate_window(window)
    return prices.ewm(span=window, adjust=False).mean()


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing.

    Returns values in ``[0, 100]``. Above 70 is conventionally
    "overbought", below 30 "oversold".
    """
    _validate_window(window)
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder's smoothing is an EMA with alpha = 1/window.
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # When average loss is zero, RSI is defined as 100.
    out = out.where(avg_loss != 0.0, 100.0)
    # When both are zero (flat price), RSI is conventionally 50.
    out = out.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return out


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Returns a DataFrame with columns ``macd``, ``signal`` and ``hist``.
    """
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be smaller than slow ({slow})")
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": hist}
    )


def bollinger_bands(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands.

    Returns a DataFrame with columns ``mid``, ``upper``, ``lower`` and
    ``pct_b`` (where price sits within the band, 0 = lower, 1 = upper).
    """
    _validate_window(window)
    if num_std <= 0:
        raise ValueError("num_std must be positive")
    mid = prices.rolling(window=window, min_periods=window).mean()
    std = prices.rolling(window=window, min_periods=window).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower).replace(0.0, np.nan)
    pct_b = (prices - lower) / width
    return pd.DataFrame(
        {"mid": mid, "upper": upper, "lower": lower, "pct_b": pct_b}
    )


def annualized_volatility(prices: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized volatility of log returns."""
    log_ret = np.log(prices / prices.shift(1)).dropna()
    if log_ret.empty:
        return float("nan")
    return float(log_ret.std(ddof=1) * np.sqrt(periods_per_year))


def _validate_window(window: int) -> None:
    if not isinstance(window, (int, np.integer)) or window < 1:
        raise ValueError(f"window must be a positive integer, got {window!r}")
