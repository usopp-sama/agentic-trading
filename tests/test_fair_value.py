"""QA-6: fair-value surface — exact wiring + refusal paths."""

from __future__ import annotations

from datetime import date

import pytest

from ats.services.fundamentals.fair_value import fair_value
from quant.analysis.valuation import discounted_cash_flow


def _stmts(fcf_series, shares=100.0, net_debt=0.0):
    """Newest-first statements with cfo/capex chosen so cfo-capex == fcf."""
    out = []
    year = 2024
    for fcf in fcf_series:  # newest first
        out.append({
            "as_of": date(year, 3, 31), "cfo": fcf + 50.0, "capex": 50.0,
            "net_debt": net_debt, "shares_outstanding": shares,
            "net_income": 1.0, "total_assets": 10.0,
        })
        year -= 1
    return out


def test_intrinsic_matches_dcf_engine_exactly():
    # Flat FCF=100 => base 100, CAGR 0 -> clamped to growth floor 0.02.
    stmts = _stmts([100.0, 100.0, 100.0])
    fv = fair_value("X", price=None, statements=stmts)
    expected = discounted_cash_flow(
        base_fcf=100.0, growth_rate=0.02, discount_rate=0.12,
        terminal_growth=0.04, years=5, net_debt=0.0, shares_outstanding=100.0,
    ).per_share_value
    assert fv["intrinsic"] == pytest.approx(round(expected, 2))
    assert fv["assumptions"]["base_fcf"] == 100.0
    assert fv["assumptions"]["growth"] == 0.02


def test_verdict_undervalued_at_20pct_boundary():
    fv = fair_value("X", statements=_stmts([100.0, 100.0, 100.0]))
    intrinsic = fv["intrinsic"]
    fv2 = fair_value("X", price=round(0.8 * intrinsic, 2),
                     statements=_stmts([100.0, 100.0, 100.0]))
    assert fv2["margin_of_safety_pct"] == pytest.approx(20.0, abs=0.2)
    assert fv2["verdict"] == "undervalued"


def test_verdict_overvalued_and_fair():
    stmts = _stmts([100.0, 100.0, 100.0])
    intrinsic = fair_value("X", statements=stmts)["intrinsic"]
    over = fair_value("X", price=round(1.5 * intrinsic, 2), statements=stmts)
    fair = fair_value("X", price=intrinsic, statements=stmts)
    assert over["verdict"] == "overvalued"   # ~-50% MoS
    assert fair["verdict"] == "fair"


def test_growth_clamps_high():
    # Steeply rising FCF -> CAGR would exceed cap, clamps to 0.15.
    fv = fair_value("X", statements=_stmts([300.0, 150.0, 50.0]))
    assert fv["assumptions"]["growth"] == 0.15


def test_sensitivity_grid_is_3x3_centered():
    fv = fair_value("X", statements=_stmts([100.0, 100.0, 100.0]))
    grid = fv["sensitivity"]["grid"]
    assert len(grid) == 3 and all(len(row) == 3 for row in grid)
    # centre cell = the headline intrinsic
    assert grid[1][1] == pytest.approx(fv["intrinsic"], abs=0.05)


def test_refuses_thin_history():
    assert fair_value("X", statements=[{"cfo": 100, "capex": 50, "shares_outstanding": 100}]) is None
    assert fair_value("X", statements=[]) is None


def test_refuses_negative_fcf():
    # cfo < capex every year -> base FCF negative -> refuse
    stmts = [
        {"as_of": date(2024, 3, 31), "cfo": 10, "capex": 50, "shares_outstanding": 100},
        {"as_of": date(2023, 3, 31), "cfo": 10, "capex": 50, "shares_outstanding": 100},
    ]
    assert fair_value("X", statements=stmts) is None


def test_refuses_without_shares():
    stmts = [
        {"as_of": date(2024, 3, 31), "cfo": 150, "capex": 50, "shares_outstanding": None},
        {"as_of": date(2023, 3, 31), "cfo": 140, "capex": 50, "shares_outstanding": None},
    ]
    assert fair_value("X", statements=stmts) is None
