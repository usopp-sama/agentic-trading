"""QA-5: fundamental quality scores — exact, hand-checked fixtures."""

from __future__ import annotations

import pytest

from quant.analysis.quality import (
    altman_z,
    altman_zone,
    dividend_safety,
    payout_ratio,
    piotroski_f,
)

# A strong company: engineered so 8 of 9 Piotroski checks pass (gross margin
# deliberately shrinks, failing exactly one).
STRONG_PREV = dict(
    net_income=80, total_assets=1000, cfo=90, current_assets=400,
    current_liabilities=200, total_debt=300, gross_margin=0.30, revenue=1000,
    shares_outstanding=100,
)
STRONG_CUR = dict(
    net_income=120, total_assets=1050, cfo=150, current_assets=500,
    current_liabilities=200, total_debt=250, gross_margin=0.28, revenue=1200,
    shares_outstanding=100,
)

# A weak company: only 2 checks pass (CFO>0 and accruals CFO>NI).
WEAK_PREV = dict(
    net_income=100, total_assets=1000, cfo=50, current_assets=300,
    current_liabilities=200, total_debt=200, gross_margin=0.30, revenue=900,
    shares_outstanding=100,
)
WEAK_CUR = dict(
    net_income=-20, total_assets=1100, cfo=60, current_assets=250,
    current_liabilities=250, total_debt=350, gross_margin=0.25, revenue=800,
    shares_outstanding=120,
)


def test_piotroski_strong_scores_eight():
    f = piotroski_f(STRONG_CUR, STRONG_PREV)
    assert f.score == 8
    assert len(f.checks) == 9
    gm = next(c for c in f.checks if c["name"] == "gross_margin_increasing")
    assert gm["passed"] is False


def test_piotroski_weak_scores_two():
    f = piotroski_f(WEAK_CUR, WEAK_PREV)
    assert f.score == 2
    passed = {c["name"] for c in f.checks if c["passed"]}
    assert passed == {"cfo_positive", "accruals_cfo_gt_ni"}


def test_piotroski_missing_inputs_all_fail():
    f = piotroski_f({}, {})
    assert f.score == 0
    assert len(f.checks) == 9
    assert all(c["passed"] is False for c in f.checks)


def test_payout_ratio_normal():
    assert payout_ratio(30, 100) == pytest.approx(0.30)


def test_payout_ratio_abs_dividend():
    assert payout_ratio(-30, 100) == pytest.approx(0.30)  # cash-flow sign


def test_payout_ratio_zero_or_negative_ni_is_none():
    assert payout_ratio(30, 0) is None
    assert payout_ratio(30, -50) is None
    assert payout_ratio(None, 100) is None


def test_altman_z_hand_computed():
    cur = dict(
        current_assets=500, current_liabilities=200, total_assets=1000,
        retained_earnings=300, ebit=150, revenue=1200, total_liabilities=400,
    )
    z = altman_z(cur, market_cap=800)
    # 1.2*.3 + 1.4*.3 + 3.3*.15 + 0.6*2 + 1.0*1.2 = 3.675
    assert z == pytest.approx(3.675)
    assert altman_zone(z) == "safe"


def test_altman_zones():
    assert altman_zone(1.0) == "distress"
    assert altman_zone(2.5) == "grey"
    assert altman_zone(3.5) == "safe"
    assert altman_zone(None) is None


def test_altman_missing_input_is_none():
    cur = dict(current_assets=500, current_liabilities=200, total_assets=1000,
               ebit=150, revenue=1200, total_liabilities=400)  # no retained_earnings
    assert altman_z(cur, market_cap=800) is None


def test_dividend_safety_healthy():
    d = dividend_safety(yield_pct=0.05, payout=0.5, f_score=8, growth_years=6)
    assert d["safe"] is True
    assert all(d["checks"].values())


def test_dividend_safety_trap_is_rejected():
    # 12% yield but 95% payout, weak F-score, no growth streak -> unsafe.
    d = dividend_safety(yield_pct=0.12, payout=0.95, f_score=5, growth_years=2)
    assert d["safe"] is False
    assert d["checks"]["high_yield"] is True
    assert d["checks"]["safe_payout"] is False
    assert d["checks"]["healthy_fscore"] is False
