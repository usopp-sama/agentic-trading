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


# --- Zerodha Kite live source (L2) ------------------------------------------
# Our internal intervals -> Kite historical interval names.
_KITE_INTERVAL = {"1m": "minute", "3m": "3minute", "5m": "5minute",
                  "15m": "15minute", "30m": "30minute", "60m": "60minute",
                  "1h": "60minute", "1d": "day", "1w": "day"}
# How far back to request each intraday interval (bounds the payload and stays
# under Kite's per-interval history caps).
_KITE_LOOKBACK_DAYS = {"minute": 5, "3minute": 10, "5minute": 15, "15minute": 30,
                       "30minute": 45, "60minute": 90, "day": 400}
_KITE_QUOTE_CHUNK = 500  # kite.quote() accepts up to 500 instruments per call


def _kite_quote_key(symbol: str) -> str | None:
    """Internal symbol -> Kite quote key (``RELIANCE.NS`` -> ``NSE:RELIANCE``);
    indices (``^NSEI``) return None (Kite exposes them under a different namespace)."""
    from ats.services.market_data.kite_history import nse_symbol

    ns = nse_symbol(symbol)
    return f"NSE:{ns}" if ns else None


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _ltps_from_quote(resp: dict) -> dict[str, float]:
    """Kite ``quote()`` payload ``{'NSE:SYM': {'last_price': x, ...}}`` -> ``{'NSE:SYM': x}``."""
    out: dict[str, float] = {}
    for key, val in (resp or {}).items():
        try:
            lp = val.get("last_price") if isinstance(val, dict) else None
            if lp is not None:
                out[key] = float(lp)
        except Exception:  # noqa: BLE001
            continue
    return out


def _candles_from_records(records: list[dict]) -> list[dict]:
    """Kite ``historical_data`` records -> chart candles (epoch-keyed)."""
    out: list[dict] = []
    for r in records or []:
        try:
            t = pd.Timestamp(r["date"])
            epoch = int((t.tz_localize("UTC") if t.tzinfo is None else t).timestamp())
            out.append({"time": epoch, "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]),
                        "volume": float(r.get("volume", 0.0) or 0.0)})
        except Exception:  # noqa: BLE001 - skip a malformed record, keep the rest
            continue
    return out


def _overlay_ltp(df: pd.DataFrame, ltp: float) -> pd.DataFrame:
    """Return ``df`` with its last (forming) bar's close set to the live LTP and
    high/low widened to include it — so a cheap batched quote keeps the daily
    frame ticking without re-downloading history every poll. Pure."""
    if df is None or df.empty or ltp is None:
        return df
    out = df.copy()
    for col in ("close", "high", "low"):  # tolerate int frames (real feeds are float)
        if col in out and out[col].dtype.kind != "f":
            out[col] = out[col].astype(float)
    i = out.index[-1]
    out.at[i, "close"] = float(ltp)
    out.at[i, "high"] = max(float(out.at[i, "high"]), float(ltp))
    out.at[i, "low"] = min(float(out.at[i, "low"]), float(ltp))
    return out


class KiteLiveSource:
    """Authenticated Zerodha Kite live feed with a free-data safety net.

    - ``poll(symbol)`` returns daily OHLCV (Kite ``historical_data``), the history
      cached with a long TTL and its last bar overlaid with the live LTP so each
      poll reflects intraday movement *without* re-downloading history.
    - ``quote(symbol)`` returns LTP from a **batched** cache: one ``kite.quote()``
      call (chunked to ≤500 symbols) refreshes the whole known watchlist per
      window, honouring Kite's 3 req/s quote budget.
    - ``intraday(...)`` returns recent minute candles for the Charts page.

    Every path degrades to the injected ``fallback`` (nse_live) when the daily
    token is missing/expired or a Kite call fails — so there's never a dead feed
    at 9:15 just because you hadn't clicked Login yet. Network calls are best-
    effort; the pure shaping helpers above are unit-tested.
    """

    def __init__(self, fallback: DataSource | None = None, *, years: int = 2,
                 daily_refresh_s: int = 4 * 3600, quote_refresh_s: int = 55,
                 intraday_refresh_s: int = 60, kite_factory=None) -> None:
        self._fallback = fallback if fallback is not None else NseLiveSource()
        self._years = years
        self._daily_refresh_s = daily_refresh_s
        self._quote_refresh_s = quote_refresh_s
        self._intraday_refresh_s = intraday_refresh_s
        self._kite_factory = kite_factory  # test seam; defaults to build_kite
        self._kite = None
        self._kite_warned = False
        self._tokens: dict[str, int] = {}
        self._universe: set[str] = set()
        self._daily_cache: dict[str, tuple[float, pd.DataFrame]] = {}
        self._intraday_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}
        self._ltp: dict[str, float] = {}
        self._ltp_ts: float = 0.0

    # --- kite handle -------------------------------------------------------
    def _kite_or_none(self):  # pragma: no cover - needs creds + kiteconnect dep
        if self._kite is not None:
            return self._kite
        factory = self._kite_factory
        if factory is None:
            from ats.services.market_data.kite_history import build_kite
            factory = build_kite
        try:
            self._kite = factory()  # raises KiteNotReady if token/dep missing
            return self._kite
        except Exception as exc:  # noqa: BLE001 - degrade to the free feed
            if not self._kite_warned:
                log.warning("kite_unavailable_using_fallback", extra={"error": str(exc)})
                self._kite_warned = True
            return None

    def kite_ready(self) -> bool:
        return self._kite_or_none() is not None

    def _tokens_map(self) -> dict[str, int]:  # pragma: no cover - network
        kite = self._kite_or_none()
        if kite is None:
            return {}
        if not self._tokens:
            try:
                from ats.services.market_data.kite_history import _instrument_tokens
                self._tokens = _instrument_tokens(kite)
            except Exception as exc:  # noqa: BLE001
                log.warning("kite_tokens_failed", extra={"error": str(exc)})
                self._tokens = {}
        return self._tokens

    # --- daily poll --------------------------------------------------------
    def poll(self, symbol: str) -> pd.DataFrame:  # pragma: no cover - network
        self._universe.add(symbol)
        kite = self._kite_or_none()
        if kite is None:
            return self._fallback.poll(symbol)
        df = self._daily_frame(symbol, kite)
        if df is None or df.empty:
            return self._fallback.poll(symbol)
        ltp = self._live_ltp(symbol, kite)
        return _overlay_ltp(df, ltp) if ltp is not None else df

    def _daily_frame(self, symbol: str, kite) -> pd.DataFrame | None:  # pragma: no cover
        from datetime import date, timedelta

        from ats.services.market_data.kite_history import _records_to_df, nse_symbol

        now = time.time()
        cached = self._daily_cache.get(symbol)
        if cached and (now - cached[0]) < self._daily_refresh_s:
            return cached[1]
        ns = nse_symbol(symbol)
        tok = self._tokens_map().get(ns) if ns else None
        if not tok:
            return None
        end = date.today()
        start = end - timedelta(days=int(365.25 * self._years))
        try:
            df = _records_to_df(kite.historical_data(tok, start, end, "day"))
        except Exception as exc:  # noqa: BLE001
            log.warning("kite_poll_failed", extra={"symbol": symbol, "error": str(exc)})
            return cached[1] if cached else None
        if df is not None and not df.empty:
            self._daily_cache[symbol] = (now, df)
        return df

    # --- batched live quotes ----------------------------------------------
    def quote(self, symbol: str) -> float | None:  # pragma: no cover - network
        self._universe.add(symbol)
        kite = self._kite_or_none()
        if kite is None:
            fn = getattr(self._fallback, "quote", None)
            return fn(symbol) if fn else None
        ltp = self._live_ltp(symbol, kite)
        if ltp is not None:
            return ltp
        fn = getattr(self._fallback, "quote", None)
        return fn(symbol) if fn else None

    def _live_ltp(self, symbol: str, kite) -> float | None:  # pragma: no cover
        now = time.time()
        if (now - self._ltp_ts) >= self._quote_refresh_s or symbol not in self._ltp:
            self._refresh_quotes(kite)
        return self._ltp.get(symbol)

    def _refresh_quotes(self, kite) -> None:  # pragma: no cover
        keymap = {k: s for s in self._universe if (k := _kite_quote_key(s))}
        keys = list(keymap)
        if not keys:
            return
        fresh: dict[str, float] = {}
        ok = False
        for chunk in _chunks(keys, _KITE_QUOTE_CHUNK):
            try:
                resp = kite.quote(chunk)
            except Exception as exc:  # noqa: BLE001
                log.warning("kite_quote_failed", extra={"error": str(exc), "n": len(chunk)})
                continue
            ok = True
            for qk, lp in _ltps_from_quote(resp).items():
                if (sym := keymap.get(qk)) is not None:
                    fresh[sym] = lp
        if ok:
            self._ltp.update(fresh)
            self._ltp_ts = time.time()

    # --- intraday candles --------------------------------------------------
    def intraday(self, symbol: str, interval: str = "5m", limit: int = 300) -> list[dict]:  # pragma: no cover
        kite = self._kite_or_none()
        if kite is None:
            return self._fallback_intraday(symbol, interval, limit)
        iv = _KITE_INTERVAL.get(interval, "5minute")
        key = (symbol, iv)
        now = time.time()
        cached = self._intraday_cache.get(key)
        if cached and (now - cached[0]) < self._intraday_refresh_s:
            return cached[1][-limit:]
        candles = self._intraday_kite(symbol, iv, kite)
        if candles is None:
            return self._fallback_intraday(symbol, interval, limit)
        self._intraday_cache[key] = (now, candles)
        return candles[-limit:]

    def _intraday_kite(self, symbol: str, iv: str, kite) -> list[dict] | None:  # pragma: no cover
        from datetime import date, timedelta

        from ats.services.market_data.kite_history import nse_symbol

        ns = nse_symbol(symbol)
        tok = self._tokens_map().get(ns) if ns else None
        if not tok:
            return None
        end = date.today()
        start = end - timedelta(days=_KITE_LOOKBACK_DAYS.get(iv, 15))
        try:
            return _candles_from_records(kite.historical_data(tok, start, end, iv))
        except Exception as exc:  # noqa: BLE001
            log.warning("kite_intraday_failed", extra={"symbol": symbol, "error": str(exc)})
            return None

    def _fallback_intraday(self, symbol: str, interval: str, limit: int) -> list[dict]:  # pragma: no cover
        fn = getattr(self._fallback, "intraday", None)
        return fn(symbol, interval=interval, limit=limit) if fn else []


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
        # Kite live → nse_live (yfinance) → synthetic: never a dead feed. The
        # inner ResilientDataSource caches per-symbol frames and tracks is_live
        # (True unless a symbol fell all the way through to synthetic); the Kite
        # source itself falls back to nse_live when the daily token is missing.
        refresh = max(60, settings.market_scan_interval_s)
        kite_live = KiteLiveSource(
            fallback=NseLiveSource(),
            quote_refresh_s=max(30, settings.intraday_refresh_s),
            intraday_refresh_s=max(30, settings.intraday_refresh_s),
        )
        return ResilientDataSource(kite_live, SyntheticDataSource(), refresh_s=refresh)
    return SyntheticDataSource()
