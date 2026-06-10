import numpy as np
import pandas as pd
import pytest

from quant.analysis import valuation


def test_dcf_basic_positive_value():
    r = valuation.discounted_cash_flow(
        base_fcf=100.0,
        growth_rate=0.05,
        discount_rate=0.10,
        terminal_growth=0.02,
        years=5,
        shares_outstanding=10.0,
    )
    assert r.enterprise_value > 0
    assert r.pv_terminal > r.pv_explicit  # terminal usually dominates
    assert r.per_share_value == pytest.approx(r.equity_value / 10.0)


def test_dcf_requires_discount_above_terminal():
    with pytest.raises(ValueError):
        valuation.discounted_cash_flow(
            base_fcf=100.0,
            growth_rate=0.05,
            discount_rate=0.02,
            terminal_growth=0.02,
        )


def test_dcf_known_value():
    # Single year, no growth, no terminal-dominance surprises.
    r = valuation.discounted_cash_flow(
        base_fcf=100.0,
        growth_rate=0.0,
        discount_rate=0.10,
        terminal_growth=0.0,
        years=1,
    )
    # Year-1 FCF = 100, discounted = 100/1.1 = 90.909...
    assert r.pv_explicit == pytest.approx(90.9090909, rel=1e-6)
    # Terminal: 100/(0.10) = 1000, discounted = 1000/1.1 = 909.09...
    assert r.pv_terminal == pytest.approx(909.090909, rel=1e-6)


def test_ddm():
    v = valuation.dividend_discount_model(2.0, 0.08, 0.03)
    assert v == pytest.approx(40.0)


def test_ddm_invalid():
    with pytest.raises(ValueError):
        valuation.dividend_discount_model(2.0, 0.03, 0.08)


def test_margin_of_safety_sign():
    assert valuation.margin_of_safety(100.0, 70.0) == pytest.approx(0.30)
    assert valuation.margin_of_safety(100.0, 120.0) == pytest.approx(-0.20)


def test_fair_futures_contango():
    # Positive net carry -> futures above spot.
    f = valuation.fair_futures_price(
        spot=100.0,
        risk_free_rate=0.05,
        storage_cost=0.02,
        convenience_yield=0.0,
        time_to_expiry_years=1.0,
    )
    assert f > 100.0


def test_nav_premium_discount():
    price = pd.Series([101.0, 99.0, 100.0])
    nav = pd.Series([100.0, 100.0, 100.0])
    table = valuation.nav_premium_discount(price, nav)
    assert table["premium_pct"].iloc[0] == pytest.approx(1.0)
    assert table["premium_pct"].iloc[1] == pytest.approx(-1.0)
