"""Market data fetching.

Thin wrapper around :mod:`yfinance` that returns a clean, predictable
OHLCV schema. Also provides a deterministic synthetic-data generator so
the rest of the toolkit (indicators, backtests, tests) can run fully
offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_prices(
    ticker: str,
    start: str | None = None,
    end: str | None = None,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV price history for a single ticker.

    Returns a DataFrame indexed by date with lowercase columns
    ``open, high, low, close, volume``. Raises ``RuntimeError`` with a
    helpful message if the download fails or returns nothing.
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "yfinance is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    kwargs: dict = {"interval": interval, "auto_adjust": True, "progress": False}
    if start:
        kwargs["start"] = start
        if end:
            kwargs["end"] = end
    else:
        kwargs["period"] = period

    try:
        raw = yf.download(ticker, **kwargs)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise RuntimeError(f"Failed to download {ticker!r}: {exc}") from exc

    if raw is None or raw.empty:
        raise RuntimeError(
            f"No data returned for {ticker!r}. Check the symbol "
            "(Indian tickers need a suffix, e.g. 'SILVERBEES.NS')."
        )

    return _normalize(raw)


def fetch_prices_batch(
    tickers: list[str], period: str = "6mo", interval: str = "1d"
) -> dict[str, pd.DataFrame]:
    """Download many tickers in one threaded request; return {ticker: OHLCV}.

    Far faster and gentler on the API than looping ``fetch_prices`` per symbol.
    Tickers that return nothing are simply omitted from the result.
    """
    if not tickers:
        return {}
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("yfinance is not installed.") from exc

    raw = yf.download(
        tickers, period=period, interval=interval,
        auto_adjust=True, progress=False, group_by="ticker", threads=True,
    )
    out: dict[str, pd.DataFrame] = {}
    multi = isinstance(raw.columns, pd.MultiIndex)
    for t in tickers:
        try:
            sub = raw[t] if (multi and t in raw.columns.get_level_values(0)) else raw
            df = _normalize(sub)
            if not df.empty:
                out[t] = df
        except Exception:  # noqa: BLE001 - skip symbols that failed
            continue
    return out


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance output to the canonical OHLCV schema."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # Single-ticker download still returns a MultiIndex; take level 0.
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    keep = [c for c in OHLCV_COLUMNS if c in df.columns]
    df = df[keep]
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.dropna(how="all")


def synthetic_prices(
    n: int = 252,
    start_price: float = 100.0,
    annual_drift: float = 0.08,
    annual_vol: float = 0.20,
    seed: int | None = 42,
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """Generate a deterministic geometric-Brownian-motion price series.

    Useful for offline demos and unit tests. Produces a full OHLCV frame.
    """
    rng = np.random.default_rng(seed)
    dt = 1.0 / 252.0
    shocks = rng.normal(
        loc=(annual_drift - 0.5 * annual_vol**2) * dt,
        scale=annual_vol * np.sqrt(dt),
        size=n,
    )
    close = start_price * np.exp(np.cumsum(shocks))

    intraday = np.abs(rng.normal(0.0, annual_vol * np.sqrt(dt), size=n)) * close
    high = close + intraday
    low = close - intraday
    open_ = np.concatenate([[start_price], close[:-1]])
    volume = rng.integers(1_000_000, 5_000_000, size=n)

    idx = pd.bdate_range(start=start, periods=n, name="date")
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )
