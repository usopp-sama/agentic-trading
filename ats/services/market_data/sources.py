"""Pluggable market-data sources.

All sources expose ``poll(symbol) -> DataFrame`` returning OHLCV indexed by
date. The synthetic source is stateful (it appends a fresh bar each poll) so
the system shows live-like movement and the volume-spike detector has
something to fire on - all with zero network. yfinance and Kite are drop-in
swaps via ``ATS_DATA_SOURCE``.
"""

from __future__ import annotations

import hashlib
import time
from typing import Protocol

import numpy as np
import pandas as pd

from quant.data.fetch import synthetic_prices
from ats.core.logging import get_logger

log = get_logger("ats.market_data")


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


# yfinance interval/period mapping for intraday (free, no API key, covers NSE
# via the .NS suffix). The pluggable seam below lets Zerodha Kite replace this
# later without touching the pages or the /api/ohlcv endpoint.
_YF_INTERVAL = {"1m": "1m", "3m": "5m", "5m": "5m", "15m": "15m", "30m": "30m",
                "60m": "60m", "1h": "60m", "1d": "1d", "1w": "1wk"}
_YF_PERIOD = {"1m": "5d", "5m": "1mo", "15m": "2mo", "30m": "2mo",
              "60m": "6mo", "1h": "6mo", "1d": "2y", "1w": "5y"}


def _to_nse_yf(symbol: str) -> str:
    """Bare NSE symbol -> yfinance ticker (RELIANCE -> RELIANCE.NS); leave
    indices (^NSEI) and already-suffixed symbols untouched."""
    if "." in symbol or symbol.startswith("^"):
        return symbol
    return symbol + ".NS"


class NseLiveSource:
    """Live NSE quotes + intraday candles, no API key, via yfinance (an
    open-source data source covering NSE through the ``.NS`` suffix).

    ``poll`` returns daily backfill (for the strategy/backtest layer);
    ``intraday`` returns recent 1m/5m/15m/… candles shaped for the charts.
    Cached + rate-limit aware. Pluggable: a Kite-backed source can implement the
    same ``poll`` + ``intraday`` + ``quote`` interface and drop straight in.
    """

    def __init__(self, refresh_s: int = 60) -> None:
        self._daily = YFinanceDataSource(period="2y")
        self._refresh_s = refresh_s
        self._intraday_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}

    def poll(self, symbol: str) -> pd.DataFrame:
        return self._daily.poll(_to_nse_yf(symbol))

    def quote(self, symbol: str) -> float | None:
        try:
            df = self.poll(symbol)
            return float(df["close"].iloc[-1]) if df is not None and not df.empty else None
        except Exception:  # noqa: BLE001
            return None

    def intraday(self, symbol: str, interval: str = "5m", limit: int = 300) -> list[dict]:
        iv = _YF_INTERVAL.get(interval, "5m")
        key = (symbol, iv)
        now = time.time()
        cached = self._intraday_cache.get(key)
        if cached and (now - cached[0]) < self._refresh_s:
            return cached[1][-limit:]
        try:
            from quant.data.fetch import fetch_prices

            df = fetch_prices(_to_nse_yf(symbol), period=_YF_PERIOD.get(interval, "1mo"), interval=iv)
        except Exception as exc:  # noqa: BLE001 - live feeds fail; degrade
            log.warning("intraday_fetch_failed", extra={"symbol": symbol, "error": str(exc)})
            return cached[1][-limit:] if cached else []
        candles: list[dict] = []
        for ts, row in df.iterrows():
            t = pd.Timestamp(ts)
            epoch = int((t.tz_localize("UTC") if t.tzinfo is None else t).timestamp())
            candles.append({"time": epoch, "open": float(row["open"]), "high": float(row["high"]),
                            "low": float(row["low"]), "close": float(row["close"]),
                            "volume": float(row.get("volume", 0.0))})
        self._intraday_cache[key] = (now, candles)
        return candles[-limit:]


class ResilientDataSource:
    """Caches a live source per symbol and falls back gracefully.

    Live feeds (yfinance) are rate-limited and occasionally fail, and we don't
    want to refetch six months of history every 60s poll. So we cache each
    symbol's frame and only refresh after ``refresh_s``. If a live fetch fails
    we serve the last good cache, and if we've never had real data for a symbol
    we fall back to synthetic so the system still boots offline. ``is_live``
    reports whether the latest data for a symbol came from the live feed.
    """

    def __init__(self, primary: DataSource, fallback: DataSource, refresh_s: int = 300) -> None:
        self._primary = primary
        self._fallback = fallback
        self._refresh_s = refresh_s
        self._cache: dict[str, pd.DataFrame] = {}
        self._fetched_at: dict[str, float] = {}
        self._live: dict[str, bool] = {}

    def poll(self, symbol: str) -> pd.DataFrame:
        now = time.time()
        fresh = (now - self._fetched_at.get(symbol, 0.0)) < self._refresh_s
        if symbol in self._cache and fresh:
            return self._cache[symbol]
        try:
            df = self._primary.poll(symbol)
            if df is None or df.empty:
                raise ValueError("empty frame from live source")
            self._cache[symbol] = df
            self._fetched_at[symbol] = now
            self._live[symbol] = True
            return df
        except Exception as exc:  # noqa: BLE001 - live feeds fail; degrade, don't crash
            if symbol in self._cache:
                return self._cache[symbol]
            log.warning("live_fetch_fallback_synthetic", extra={"symbol": symbol, "error": str(exc)})
            df = self._fallback.poll(symbol)
            self._cache[symbol] = df
            self._fetched_at[symbol] = now
            self._live[symbol] = False
            return df

    def prefetch(self, symbols: list[str]) -> None:
        """Warm the cache for many symbols in one batched download."""
        try:
            from quant.data.fetch import fetch_prices_batch

            frames = fetch_prices_batch(symbols, period="6mo")
        except Exception as exc:  # noqa: BLE001
            log.warning("batch_prefetch_failed", extra={"error": str(exc)})
            return
        now = time.time()
        for sym, df in frames.items():
            if df is not None and not df.empty:
                self._cache[sym] = df
                self._fetched_at[sym] = now
                self._live[sym] = True
        log.info("batch_prefetch", extra={"requested": len(symbols), "live": len(frames)})

    def is_live(self, symbol: str) -> bool:
        return self._live.get(symbol, False)

    # Pass intraday/quote through to the primary source when it supports them
    # (e.g. NseLiveSource); degrade quietly otherwise.
    def intraday(self, symbol: str, interval: str = "5m", limit: int = 300) -> list[dict]:
        fn = getattr(self._primary, "intraday", None)
        if fn is None:
            return []
        try:
            return fn(symbol, interval=interval, limit=limit)
        except Exception as exc:  # noqa: BLE001
            log.warning("intraday_passthrough_failed", extra={"symbol": symbol, "error": str(exc)})
            return []

    def quote(self, symbol: str) -> float | None:
        fn = getattr(self._primary, "quote", None)
        return fn(symbol) if fn else None


def build_data_source() -> DataSource:
    from ats.core.config import get_settings

    settings = get_settings()
    source = settings.data_source
    if source == "nse_live":
        # Live quotes + intraday candles (free, no key) with synthetic fallback.
        return ResilientDataSource(NseLiveSource(), SyntheticDataSource(),
                                   refresh_s=max(60, settings.intraday_refresh_s))
    if source == "yfinance":
        refresh = max(120, settings.market_scan_interval_s)
        return ResilientDataSource(YFinanceDataSource(), SyntheticDataSource(), refresh_s=refresh)
    if source == "kite":
        return KiteDataSource()
    return SyntheticDataSource()
