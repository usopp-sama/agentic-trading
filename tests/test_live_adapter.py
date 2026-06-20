"""Tests for the live NSE intraday adapter (no network — fetch is patched)."""

from __future__ import annotations

import pandas as pd

import quant.data.fetch as fetch
from ats.services.market_data.sources import (
    NseLiveSource,
    ResilientDataSource,
    SyntheticDataSource,
    _to_nse_yf,
)


def test_symbol_mapping():
    assert _to_nse_yf("RELIANCE") == "RELIANCE.NS"
    assert _to_nse_yf("^NSEI") == "^NSEI"          # index untouched
    assert _to_nse_yf("SILVERBEES.NS") == "SILVERBEES.NS"  # already suffixed


def test_intraday_shapes_candles(monkeypatch):
    idx = pd.date_range("2026-01-01 09:15", periods=3, freq="5min")
    df = pd.DataFrame({"open": [1, 2, 3], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5],
                       "close": [1.5, 2.5, 3.5], "volume": [100, 200, 300]}, index=idx)
    monkeypatch.setattr(fetch, "fetch_prices", lambda *a, **k: df)

    src = NseLiveSource()
    candles = src.intraday("RELIANCE", interval="5m", limit=10)
    assert len(candles) == 3
    assert set(candles[0]) == {"time", "open", "high", "low", "close", "volume"}
    assert candles[0]["open"] == 1.0 and candles[-1]["close"] == 3.5
    # cached on the second call (same object returned within refresh window)
    assert src.intraday("RELIANCE", interval="5m") == candles


def test_intraday_degrades_when_fetch_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(fetch, "fetch_prices", boom)
    src = NseLiveSource()
    assert src.intraday("INFY", interval="1m") == []


def test_resilient_passthrough_intraday(monkeypatch):
    idx = pd.date_range("2026-01-01 09:15", periods=2, freq="15min")
    df = pd.DataFrame({"open": [1, 2], "high": [2, 3], "low": [0.5, 1.5],
                       "close": [1.5, 2.5], "volume": [10, 20]}, index=idx)
    monkeypatch.setattr(fetch, "fetch_prices", lambda *a, **k: df)
    rds = ResilientDataSource(NseLiveSource(), SyntheticDataSource())
    assert len(rds.intraday("TCS", interval="15m")) == 2
    # a source with no intraday() yields []
    assert ResilientDataSource(SyntheticDataSource(), SyntheticDataSource()).intraday("TCS") == []
