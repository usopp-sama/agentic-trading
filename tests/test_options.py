"""Tests for Black-Scholes pricing, Greeks, implied vol, and the CRR tree.

Reference values are the classic Hull worked example (Options, Futures,
and Other Derivatives): S=42, K=40, r=10%, sigma=20%, T=0.5y ->
call ~ 4.76, put ~ 0.81.
"""

from __future__ import annotations

import pytest

from quant.options import bs_greeks, bs_price, crr_price, implied_vol

HULL = dict(spot=42.0, strike=40.0, t=0.5, r=0.10, sigma=0.20)


# --- pricing -----------------------------------------------------------------
def test_hull_textbook_values():
    assert bs_price(**HULL, kind="call") == pytest.approx(4.7594, abs=1e-3)
    assert bs_price(**HULL, kind="put") == pytest.approx(0.8086, abs=1e-3)


def test_put_call_parity():
    import math

    for q in (0.0, 0.03):
        c = bs_price(**HULL, kind="call", q=q)
        p = bs_price(**HULL, kind="put", q=q)
        lhs = c - p
        rhs = HULL["spot"] * math.exp(-q * HULL["t"]) - HULL["strike"] * math.exp(
            -HULL["r"] * HULL["t"]
        )
        assert lhs == pytest.approx(rhs, abs=1e-10)


def test_expiry_and_zero_vol_degenerate_to_intrinsic():
    assert bs_price(110, 100, 0.0, 0.05, 0.2, "call") == 10.0
    assert bs_price(90, 100, 0.0, 0.05, 0.2, "call") == 0.0
    assert bs_price(90, 100, 0.0, 0.05, 0.2, "put") == 10.0
    # Zero vol: discounted forward intrinsic, never negative.
    assert bs_price(100, 100, 1.0, 0.05, 0.0, "put") == 0.0
    assert bs_price(100, 100, 1.0, 0.05, 0.0, "call") > 0.0


def test_input_validation():
    with pytest.raises(ValueError):
        bs_price(-1, 100, 1.0, 0.05, 0.2)
    with pytest.raises(ValueError):
        bs_price(100, 100, -0.1, 0.05, 0.2)
    with pytest.raises(ValueError):
        bs_price(100, 100, 1.0, 0.05, 0.2, kind="straddle")


# --- greeks -------------------------------------------------------------------
def test_greek_signs_and_ranges():
    g_call = bs_greeks(**HULL, kind="call")
    g_put = bs_greeks(**HULL, kind="put")
    assert 0.0 < g_call.delta < 1.0
    assert -1.0 < g_put.delta < 0.0
    assert g_call.gamma > 0 and g_call.gamma == pytest.approx(g_put.gamma, abs=1e-12)
    assert g_call.vega > 0 and g_call.vega == pytest.approx(g_put.vega, abs=1e-12)
    assert g_call.theta < 0  # long options decay
    assert g_call.rho > 0 > g_put.rho


def test_greeks_match_finite_differences():
    h = 1e-4
    g = bs_greeks(**HULL, kind="call")
    up = bs_price(HULL["spot"] + h, HULL["strike"], HULL["t"], HULL["r"], HULL["sigma"], "call")
    dn = bs_price(HULL["spot"] - h, HULL["strike"], HULL["t"], HULL["r"], HULL["sigma"], "call")
    base = bs_price(**HULL, kind="call")
    assert g.delta == pytest.approx((up - dn) / (2 * h), abs=1e-5)
    assert g.gamma == pytest.approx((up - 2 * base + dn) / (h * h), abs=1e-3)

    v_up = bs_price(HULL["spot"], HULL["strike"], HULL["t"], HULL["r"], HULL["sigma"] + h, "call")
    v_dn = bs_price(HULL["spot"], HULL["strike"], HULL["t"], HULL["r"], HULL["sigma"] - h, "call")
    assert g.vega == pytest.approx((v_up - v_dn) / (2 * h), abs=1e-4)

    t_dn = bs_price(HULL["spot"], HULL["strike"], HULL["t"] - h, HULL["r"], HULL["sigma"], "call")
    assert g.theta == pytest.approx((t_dn - base) / h, abs=1e-3)


def test_deep_itm_call_delta_near_one():
    g = bs_greeks(500.0, 100.0, 0.25, 0.05, 0.2, "call")
    assert g.delta == pytest.approx(1.0, abs=1e-6)


# --- implied vol ----------------------------------------------------------------
def test_implied_vol_round_trip():
    for sigma in (0.08, 0.20, 0.55, 1.2):
        for kind in ("call", "put"):
            price = bs_price(HULL["spot"], HULL["strike"], HULL["t"], HULL["r"], sigma, kind)
            iv = implied_vol(price, HULL["spot"], HULL["strike"], HULL["t"], HULL["r"], kind)
            assert iv == pytest.approx(sigma, abs=1e-5)


def test_implied_vol_rejects_unattainable_prices():
    with pytest.raises(ValueError):
        implied_vol(0.0001, **{k: v for k, v in HULL.items() if k != "sigma"}, kind="call")
    with pytest.raises(ValueError):
        implied_vol(1000.0, **{k: v for k, v in HULL.items() if k != "sigma"}, kind="call")


# --- binomial tree ----------------------------------------------------------------
def test_crr_converges_to_black_scholes():
    bs = bs_price(**HULL, kind="call")
    tree = crr_price(**HULL, kind="call", steps=600)
    assert tree == pytest.approx(bs, abs=5e-3)


def test_american_put_carries_early_exercise_premium():
    # Deep ITM American put on a high-rate underlying: the textbook case
    # where early exercise has real value.
    kwargs = dict(spot=60.0, strike=100.0, t=1.0, r=0.10, sigma=0.20, kind="put")
    european = crr_price(**kwargs, steps=400, american=False)
    american = crr_price(**kwargs, steps=400, american=True)
    assert american > european + 1e-3
    # American option never below intrinsic.
    assert american >= 40.0 - 1e-9


def test_american_call_no_dividends_equals_european():
    # Without dividends, early exercise of a call is never optimal.
    kwargs = dict(spot=42.0, strike=40.0, t=0.5, r=0.10, sigma=0.20, kind="call")
    european = crr_price(**kwargs, steps=300, american=False)
    american = crr_price(**kwargs, steps=300, american=True)
    assert american == pytest.approx(european, abs=1e-9)
