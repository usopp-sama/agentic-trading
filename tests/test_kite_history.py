"""Kite historical data — pure parts (symbol map, record→frame, guard)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from ats.core.config import get_settings
from ats.services.market_data.kite_history import (
    KiteNotReady,
    _records_to_df,
    build_kite,
    nse_symbol,
)


def test_nse_symbol_mapping():
    assert nse_symbol("RELIANCE.NS") == "RELIANCE"
    assert nse_symbol("NIFTYBEES.NS") == "NIFTYBEES"
    assert nse_symbol("TCS") == "TCS"
    assert nse_symbol("^NSEI") is None            # index — skipped


def test_records_to_df_shape_and_index():
    recs = [
        {"date": datetime(2024, 1, 1), "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
        {"date": datetime(2024, 1, 2), "open": 103, "high": 107, "low": 102, "close": 106, "volume": 1200},
    ]
    df = _records_to_df(recs)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2 and df["close"].iloc[-1] == 106.0
    assert isinstance(df.index, pd.DatetimeIndex)


def test_records_to_df_tz_aware_is_normalized():
    recs = [{"date": "2024-03-01T09:15:00+05:30", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 5}]
    df = _records_to_df(recs)
    assert df.index.tz is None and len(df) == 1


def test_records_to_df_empty():
    df = _records_to_df([])
    assert df.empty and "close" in df.columns


def test_build_kite_raises_without_creds(monkeypatch):
    monkeypatch.setattr(get_settings(), "kite_api_key", "")
    monkeypatch.setattr(get_settings(), "kite_access_token", "")
    with pytest.raises(KiteNotReady):
        build_kite()
