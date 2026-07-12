"""Tests for the Kite live market-data source (L2).

No network and no ``kiteconnect`` dependency: the Kite handle is injected via
``kite_factory``. Covers the pure shaping helpers, the batched-quote path, the
LTP overlay, and graceful fallback when the daily token is missing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ats.services.market_data import kite_history
from ats.services.market_data.sources import (
    KiteLiveSource,
    _candles_from_records,
    _chunks,
    _kite_quote_key,
    _ltps_from_quote,
    _overlay_ltp,
)


# --- pure helpers -----------------------------------------------------------
def test_kite_quote_key_maps_and_skips_indices():
    assert _kite_quote_key("RELIANCE.NS") == "NSE:RELIANCE"
    assert _kite_quote_key("INFY") == "NSE:INFY"
    assert _kite_quote_key("^NSEI") is None  # index — different Kite namespace


def test_ltps_from_quote_extracts_last_price():
    resp = {"NSE:RELIANCE": {"last_price": 2450.5}, "NSE:INFY": {"last_price": 1500},
            "NSE:BAD": {"no_price": 1}, "NSE:NONE": None}
    assert _ltps_from_quote(resp) == {"NSE:RELIANCE": 2450.5, "NSE:INFY": 1500.0}
    assert _ltps_from_quote({}) == {}


def test_chunks_splits_at_boundary():
    assert list(_chunks(list(range(5)), 2)) == [[0, 1], [2, 3], [4]]
    assert list(_chunks([], 500)) == []


def test_candles_from_records_shapes_and_skips_malformed():
    recs = [
        {"date": pd.Timestamp("2026-01-01 09:15", tz="Asia/Kolkata"),
         "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        {"date": "not-a-date"},  # malformed — dropped
        {"date": pd.Timestamp("2026-01-01 09:20"),
         "open": 2, "high": 3, "low": 1.5, "close": 2.5, "volume": 200},
    ]
    candles = _candles_from_records(recs)
    assert len(candles) == 2
    assert set(candles[0]) == {"time", "open", "high", "low", "close", "volume"}
    assert candles[0]["close"] == 1.5 and candles[-1]["close"] == 2.5
    assert candles[0]["time"] < candles[1]["time"]


def test_overlay_ltp_updates_last_bar_only():
    idx = pd.date_range("2026-01-01", periods=2, freq="D")
    df = pd.DataFrame({"open": [10, 20], "high": [12, 22], "low": [9, 19],
                       "close": [11, 21], "volume": [100, 200]}, index=idx)
    out = _overlay_ltp(df, 25.0)
    assert out["close"].iloc[-1] == 25.0
    assert out["high"].iloc[-1] == 25.0   # widened above prior high (22)
    assert out["low"].iloc[-1] == 19.0    # unchanged (25 > 19)
    assert out["close"].iloc[0] == 11     # earlier bar untouched
    # LTP inside the bar range leaves high/low alone.
    out2 = _overlay_ltp(df, 20.5)
    assert out2["high"].iloc[-1] == 22 and out2["low"].iloc[-1] == 19


# --- fake Kite handle (no network) ------------------------------------------
class _FakeKite:
    def __init__(self, ltps: dict[str, float]) -> None:
        self._ltps = ltps
        self.quote_calls: list[list[str]] = []

    def instruments(self, exchange: str) -> list[dict]:
        return [
            {"segment": "NSE", "instrument_type": "EQ",
             "tradingsymbol": "RELIANCE", "instrument_token": 111},
            {"segment": "NSE", "instrument_type": "EQ",
             "tradingsymbol": "INFY", "instrument_token": 222},
        ]

    def historical_data(self, token, start, end, interval):
        if interval == "day":
            idx = ["2026-01-01", "2026-01-02", "2026-01-03"]
            return [{"date": d, "open": 100, "high": 101, "low": 99,
                     "close": 100, "volume": 1000} for d in idx]
        return [{"date": pd.Timestamp("2026-01-03 09:15", tz="Asia/Kolkata"),
                 "open": 100, "high": 102, "low": 98, "close": 101, "volume": 500}]

    def quote(self, keys):
        self.quote_calls.append(list(keys))
        return {k: {"last_price": self._ltps[k]} for k in keys if k in self._ltps}


@pytest.fixture(autouse=True)
def _reset_token_cache():
    # kite_history caches the instrument dump in a module global; clear it so
    # each test's fake handle resolves its own tokens.
    kite_history.__dict__.pop("_TOKENS", None)
    yield
    kite_history.__dict__.pop("_TOKENS", None)


def test_poll_overlays_live_ltp_from_batched_quote():
    fake = _FakeKite({"NSE:RELIANCE": 105.0, "NSE:INFY": 1500.0})
    src = KiteLiveSource(kite_factory=lambda: fake)
    # Prime the universe so the batch covers both names in one quote() call.
    src._universe.update({"RELIANCE.NS", "INFY.NS"})
    df = src.poll("RELIANCE.NS")
    assert df["close"].iloc[-1] == 105.0        # last bar overlaid with LTP
    assert df["high"].iloc[-1] == 105.0         # widened above the 101 bar high
    assert src.kite_ready() is True
    # One batched call for the whole known universe (2 symbols), not per-symbol.
    assert len(fake.quote_calls) == 1
    assert set(fake.quote_calls[0]) == {"NSE:RELIANCE", "NSE:INFY"}


def test_quote_returns_ltp_and_intraday_shapes_candles():
    fake = _FakeKite({"NSE:RELIANCE": 105.0})
    src = KiteLiveSource(kite_factory=lambda: fake)
    assert src.quote("RELIANCE.NS") == 105.0
    candles = src.intraday("RELIANCE.NS", interval="5m", limit=10)
    assert len(candles) == 1 and candles[0]["close"] == 101.0


class _StubFallback:
    """nse_live stand-in with distinctive outputs so we can prove delegation."""

    def poll(self, symbol):
        return pd.DataFrame({"open": [1], "high": [1], "low": [1], "close": [42.0],
                             "volume": [1]}, index=pd.DatetimeIndex(["2026-01-01"], name="date"))

    def quote(self, symbol):
        return 42.0

    def intraday(self, symbol, interval="5m", limit=300):
        return [{"time": 1, "open": 1, "high": 1, "low": 1, "close": 42.0, "volume": 1}]


def test_falls_back_when_token_missing():
    from ats.services.market_data.kite_history import KiteNotReady

    def _no_token():
        raise KiteNotReady("no daily token")

    src = KiteLiveSource(fallback=_StubFallback(), kite_factory=_no_token)
    assert src.kite_ready() is False
    assert src.poll("RELIANCE.NS")["close"].iloc[-1] == 42.0   # fallback frame
    assert src.quote("RELIANCE.NS") == 42.0
    assert src.intraday("RELIANCE.NS")[0]["close"] == 42.0
