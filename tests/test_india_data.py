"""Tests for the India-market data layer: fundamentals + option chain."""

from __future__ import annotations

from datetime import date

from ats.services.fundamentals.providers import SyntheticFundamentals
from ats.services.market_data.option_chain import (
    NSE_WEEKLY_EXPIRY_WEEKDAY,
    SyntheticOptionChain,
    _next_expiry,
)


# --- fundamentals provider -----------------------------------------------------
def test_synthetic_fundamentals_are_deterministic_and_plausible():
    p = SyntheticFundamentals()
    a = p.fetch("HDFCBANK.NS")
    b = p.fetch("HDFCBANK.NS")
    assert a == b  # deterministic
    assert 8.0 <= a.pe <= 60.0
    assert 0.8 <= a.pb <= 11.8
    assert 0.05 <= a.roe <= 0.35
    assert 0.0 <= a.debt_to_equity <= 2.5
    assert a.market_cap > 0


def test_synthetic_fundamentals_differ_across_symbols():
    p = SyntheticFundamentals()
    assert p.fetch("TCS.NS").pe != p.fetch("INFY.NS").pe


def test_non_equity_symbols_have_no_fundamentals():
    p = SyntheticFundamentals()
    assert p.fetch("^NSEI") is None
    assert p.fetch("SILVERBEES.NS") is None
    assert p.fetch("NIFTYBEES.NS") is None


def test_snapshot_as_dict_roundtrip():
    snap = SyntheticFundamentals().fetch("RELIANCE.NS")
    d = snap.as_dict()
    assert d["symbol"] == "RELIANCE.NS"
    assert set(d) == {
        "symbol", "as_of", "pe", "pb", "roe", "debt_to_equity",
        "profit_margin", "dividend_yield", "market_cap", "source",
    }


# --- option chain -----------------------------------------------------------------
def test_synthetic_chain_summary_is_sane():
    s = SyntheticOptionChain().fetch("NIFTY", spot=250.0)
    assert s is not None
    assert 0.10 <= s.atm_iv <= 0.28
    assert 0.7 <= s.pcr <= 1.3
    assert abs(s.atm_strike - 250.0) <= 250.0 * 0.02
    assert s.source == "synthetic"
    # Deterministic within a day.
    assert SyntheticOptionChain().fetch("NIFTY", spot=250.0) == s


def test_synthetic_chain_defaults_without_spot():
    s = SyntheticOptionChain().fetch("NIFTY")
    assert s is not None and s.spot == 100.0


def test_next_expiry_is_always_a_future_tuesday():
    for d in (date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 12), date(2026, 6, 14)):
        expiry = _next_expiry(d)
        assert expiry.weekday() == NSE_WEEKLY_EXPIRY_WEEKDAY
        assert expiry > d
