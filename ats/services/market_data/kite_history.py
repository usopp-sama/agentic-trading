"""Zerodha Kite historical data (read-only).

Pulls clean, authenticated NSE historical candles for backtesting — separate
from the (real-money-gated) order adapter, because reading history needs only a
valid ``api_key`` + ``access_token``, not the trading gate. Requires the
``kiteconnect`` package and a daily access token (see ``scripts/kite_login.py``).

Our universe uses yfinance-style symbols (``RELIANCE.NS``); Kite uses the NSE
trading symbol (``RELIANCE``). Index symbols (``^NSEI``) are skipped here (Kite
exposes indices under different names/exchanges — not needed for the equity
backtest). Everything degrades gracefully: a symbol that fails contributes no
frame, exactly like the yfinance path.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd

from ats.core.config import get_settings
from ats.core.logging import get_logger

log = get_logger("ats.kite_history")

_KITE_RATE_S = 0.34   # Kite historical API allows ~3 requests/second


class KiteNotReady(RuntimeError):
    """kiteconnect missing or credentials/token not configured."""


def nse_symbol(symbol: str) -> str | None:
    """Map an internal symbol to a Kite NSE trading symbol, or None to skip."""
    if symbol.startswith("^"):
        return None                    # index — different Kite namespace
    return symbol[:-3] if symbol.endswith(".NS") else symbol


def build_kite():  # pragma: no cover - needs the kiteconnect dep + live creds
    """A ready ``KiteConnect`` with the access token set, or raise KiteNotReady."""
    s = get_settings()
    if not (s.kite_api_key and s.kite_access_token):
        raise KiteNotReady("set ATS_KITE_API_KEY + ATS_KITE_ACCESS_TOKEN "
                           "(run scripts/kite_login.py for the token)")
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:  # noqa: BLE001
        raise KiteNotReady(f"kiteconnect not installed ({exc}); pip install kiteconnect") from exc
    kite = KiteConnect(api_key=s.kite_api_key)
    kite.set_access_token(s.kite_access_token)
    return kite


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    """Convert Kite ``historical_data`` records to our OHLCV frame (pure)."""
    if not records:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(records)
    dts = pd.to_datetime(df["date"])
    if getattr(dts.dt, "tz", None) is not None:   # Kite returns tz-aware IST
        dts = dts.dt.tz_localize(None)
    idx = pd.DatetimeIndex(dts, name="date")
    # .to_numpy() so the columns don't index-align against the new DatetimeIndex.
    return pd.DataFrame(
        {c: df[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close", "volume")},
        index=idx,
    )


def _instrument_tokens(kite) -> dict[str, int]:  # pragma: no cover - network
    """Map NSE trading symbol -> instrument_token (one call, cached per process)."""
    global _TOKENS
    try:
        return _TOKENS  # type: ignore[name-defined]
    except NameError:
        pass
    tokens: dict[str, int] = {}
    for row in kite.instruments("NSE"):
        if row.get("segment") == "NSE" and row.get("instrument_type") == "EQ":
            tokens[row["tradingsymbol"]] = row["instrument_token"]
    globals()["_TOKENS"] = tokens
    return tokens


def fetch_prices_batch_kite(symbols: list[str], years: int = 1,
                            interval: str = "day") -> dict[str, pd.DataFrame]:  # pragma: no cover - network
    """``{symbol: OHLCV df}`` for the backtest panel — same shape as the
    yfinance path. Best-effort per symbol, rate-limited for Kite's API."""
    kite = build_kite()
    tokens = _instrument_tokens(kite)
    end, start = date.today(), date.today() - timedelta(days=int(365.25 * years))
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        ns = nse_symbol(sym)
        if ns is None or ns not in tokens:
            continue
        try:
            recs = kite.historical_data(tokens[ns], start, end, interval)
            df = _records_to_df(recs)
            if not df.empty:
                out[sym] = df
        except Exception as exc:  # noqa: BLE001
            log.warning("kite_history_failed", extra={"symbol": sym, "error": str(exc)})
        time.sleep(_KITE_RATE_S)
    log.info("kite_history_loaded", extra={"symbols": len(out), "years": years})
    return out
