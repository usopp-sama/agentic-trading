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
_TOKEN_KEY = "kite:access_token"   # runtime store (shared across processes via DB)


class KiteNotReady(RuntimeError):
    """kiteconnect missing or credentials/token not configured."""


# --- access token (runtime store) ------------------------------------------
# The daily token can arrive two ways: the web /kite/callback route (which
# writes it here, to the DB) or ATS_KITE_ACCESS_TOKEN in .env. The DB store
# wins so a fresh login through the dashboard takes effect immediately — and,
# because it is in the DB, the separate backtest process reads the same token.

def set_access_token(token: str) -> None:
    from ats.core import state

    state.set_kv(_TOKEN_KEY, {"token": token, "ts": time.time()})


def get_access_token() -> str:
    from ats.core import state

    kv = state.get_kv(_TOKEN_KEY) or {}
    return (kv.get("token") or "") or get_settings().kite_access_token


def login_url() -> str:
    """The Zerodha login URL for this app's api_key (no kiteconnect needed)."""
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={get_settings().kite_api_key}"


def exchange_request_token(request_token: str) -> str:  # pragma: no cover - network
    """Exchange a Kite ``request_token`` (from the redirect) for an access token."""
    s = get_settings()
    if not (s.kite_api_key and s.kite_api_secret):
        raise KiteNotReady("set ATS_KITE_API_KEY + ATS_KITE_API_SECRET first")
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:  # noqa: BLE001
        raise KiteNotReady(f"kiteconnect not installed ({exc}); pip install kiteconnect") from exc
    data = KiteConnect(api_key=s.kite_api_key).generate_session(
        request_token, api_secret=s.kite_api_secret
    )
    return data["access_token"]


def nse_symbol(symbol: str) -> str | None:
    """Map an internal symbol to a Kite NSE trading symbol, or None to skip."""
    if symbol.startswith("^"):
        return None                    # index — different Kite namespace
    return symbol[:-3] if symbol.endswith(".NS") else symbol


def build_kite():  # pragma: no cover - needs the kiteconnect dep + live creds
    """A ready ``KiteConnect`` with the access token set, or raise KiteNotReady."""
    s = get_settings()
    token = get_access_token()
    if not (s.kite_api_key and token):
        raise KiteNotReady("set ATS_KITE_API_KEY + a daily access token "
                           "(log in via /kite/login on the dashboard, or run "
                           "scripts/kite_login.py)")
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:  # noqa: BLE001
        raise KiteNotReady(f"kiteconnect not installed ({exc}); pip install kiteconnect") from exc
    kite = KiteConnect(api_key=s.kite_api_key)
    kite.set_access_token(token)
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
    """Map NSE trading symbol -> instrument_token (one call, cached per process).

    ``kite.instruments("NSE")`` downloads the full exchange instrument dump
    (a large CSV) — flaky wifi or a TLS-inspecting proxy can reset it
    mid-transfer, so retry a few times with backoff before giving up.
    """
    global _TOKENS
    try:
        return _TOKENS  # type: ignore[name-defined]
    except NameError:
        pass
    import time as _time

    last_exc: Exception | None = None
    rows = None
    for attempt in range(4):
        try:
            rows = kite.instruments("NSE")
            break
        except Exception as exc:  # noqa: BLE001 — retry transient network resets
            last_exc = exc
            log.warning("kite_instruments_retry",
                        extra={"attempt": attempt + 1, "error": str(exc)})
            _time.sleep(2.0 * (attempt + 1))
    if rows is None:
        raise KiteNotReady(
            f"kite.instruments('NSE') failed after 4 attempts: {last_exc}"
        )
    tokens: dict[str, int] = {}
    for row in rows:
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
