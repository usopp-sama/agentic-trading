"""QA-4: intraday VWAP + movers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.analysis.intraday import DayStat, daily_vwap_approx, movers, vwap


def test_vwap_hand_computed():
    df = pd.DataFrame({
        "high": [10, 12, 14],
        "low": [8, 10, 12],
        "close": [9, 11, 13],
        "volume": [100, 200, 300],
    })
    v = vwap(df)
    # TP = 9, 11, 13 ; cumPV/cumV
    assert v.iloc[0] == pytest.approx(9.0)
    assert v.iloc[1] == pytest.approx(3100 / 300)
    assert v.iloc[2] == pytest.approx(7000 / 600)


def test_vwap_zero_volume_is_nan_not_crash():
    df = pd.DataFrame({"high": [10], "low": [8], "close": [9], "volume": [0]})
    v = vwap(df)
    assert np.isnan(v.iloc[0])


def test_vwap_empty():
    df = pd.DataFrame(columns=["high", "low", "close", "volume"])
    assert vwap(df).empty


def test_daily_vwap_approx():
    df = pd.DataFrame({"high": [12], "low": [9], "close": [10.5], "volume": [1]})
    assert daily_vwap_approx(df) == pytest.approx((12 + 9 + 10.5) / 3)


def test_movers_ranking_and_volume_filter():
    stats = {
        "A": DayStat(5.0, 300, 100),   # big gain, 3x vol -> confirmed
        "B": DayStat(3.0, 50, 100),    # gain but thin vol -> not confirmed
        "C": DayStat(-4.0, 400, 100),  # big drop, 4x vol -> confirmed
        "D": DayStat(-1.0, 90, 100),   # small drop, thin vol
    }
    out = movers(stats, min_volume_x=1.5)
    assert [e["symbol"] for e in out["gainers"]] == ["A", "B"]
    assert [e["symbol"] for e in out["losers"]] == ["C", "D"]
    assert [e["symbol"] for e in out["volume_confirmed"]] == ["A", "C"]


def test_movers_empty():
    out = movers({})
    assert out == {"gainers": [], "losers": [], "volume_confirmed": []}


def test_movers_zero_avg_volume_not_confirmed():
    out = movers({"Z": DayStat(9.0, 500, 0)})
    assert out["gainers"][0]["symbol"] == "Z"
    assert out["volume_confirmed"] == []
