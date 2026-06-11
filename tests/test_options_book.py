"""Tests for the defined-risk options paper book and vol-premium rules."""

from __future__ import annotations

from datetime import date

import pytest

from ats.services.execution.options_book import OptionsPaperBook
from ats.services.vol_premium.service import (
    condor_strikes,
    exit_reason,
    price_condor_credit,
    should_enter,
    viable_credit,
)

EXPIRY = date(2026, 6, 16)


def _book(capital: float = 100_000.0) -> OptionsPaperBook:
    return OptionsPaperBook(capital=capital, fee_per_order=25.0)


def _open_call_spread(book: OptionsPaperBook, credit: float = 30.0):
    # Short 105 call, wing at 110: width 5 points... use index-scale numbers.
    return book.open_spread(
        "NIFTY", "CE", short_strike=24500, long_strike=24700,
        expiry=EXPIRY, lots=1, lot_size=75, entry_credit=credit,
    )


# --- book mechanics ---------------------------------------------------------------
def test_margin_reserves_max_loss():
    book = _book()
    s = _open_call_spread(book, credit=30.0)
    # width 200 - credit 30 = 170 per unit x 75 units.
    assert s.max_loss == pytest.approx(170 * 75)
    assert book.margin_reserved() == pytest.approx(170 * 75)


def test_loss_is_bounded_even_in_a_crash_through_strikes():
    book = _book()
    s = _open_call_spread(book, credit=30.0)
    # Spot rips 20% through BOTH strikes — worst case for a call spread.
    book.settle_expired(spot=30000.0, today=EXPIRY)
    # Settlement debit caps at the width; loss caps at reserved margin + fees.
    assert s.exit_debit == pytest.approx(200.0)
    assert s.realized() == pytest.approx(-(170 * 75) - 25.0)
    assert abs(s.realized()) <= s.max_loss + book.fee_per_order + 1e-9


def test_otm_expiry_keeps_full_credit():
    book = _book()
    s = _open_call_spread(book, credit=30.0)
    book.settle_expired(spot=24000.0, today=EXPIRY)  # both legs OTM
    assert s.exit_debit == 0.0
    assert s.realized() == pytest.approx(30.0 * 75 - 25.0)


def test_margin_check_blocks_oversized_positions():
    book = _book(capital=5_000.0)  # too small for a 170x75 max loss
    with pytest.raises(ValueError, match="margin"):
        _open_call_spread(book, credit=30.0)


def test_credit_spread_validation():
    book = _book()
    with pytest.raises(ValueError):  # PE wing must be BELOW the short strike
        book.open_spread("NIFTY", "PE", 24000, 24200, EXPIRY, 1, 75, 20.0)
    with pytest.raises(ValueError):  # credit >= width is free money; reject
        book.open_spread("NIFTY", "CE", 24500, 24550, EXPIRY, 1, 75, 60.0)
    with pytest.raises(ValueError):
        book.open_spread("NIFTY", "CE", 24500, 24700, EXPIRY, 1, 75, -5.0)


def test_mark_to_market_decays_toward_zero_otm():
    book = _book()
    s = _open_call_spread(book, credit=30.0)
    # Far OTM with little time left: the spread should cost less to close
    # than the credit received -> positive unrealized P&L.
    debit = s.value_to_close(spot=23500.0, iv=0.15, t_years=2 / 365, r=0.065)
    assert debit < 30.0
    assert book.unrealized_pnl(spot=23500.0, iv=0.15, t_years=2 / 365) > 0


# --- vol-premium decision rules ----------------------------------------------------
def test_should_enter_requires_everything_aligned():
    ok = dict(iv_premium=0.06, threshold=0.04, has_open=False,
              crisis=False, killed=False, mode="PAPER")
    assert should_enter(**ok)
    assert not should_enter(**{**ok, "iv_premium": 0.02})   # premium too thin
    assert not should_enter(**{**ok, "iv_premium": None})   # no data
    assert not should_enter(**{**ok, "has_open": True})     # one position at a time
    assert not should_enter(**{**ok, "crisis": True})       # never in crisis vol
    assert not should_enter(**{**ok, "killed": True})       # kill switch wins
    assert not should_enter(**{**ok, "mode": "OFF"})


def test_exit_reasons():
    assert exit_reason(entry_credit=30.0, current_debit=14.0,
                       profit_target=0.5, stop_mult=2.0) == "profit_target"
    assert exit_reason(30.0, 61.0, 0.5, 2.0) == "stop"
    assert exit_reason(30.0, 25.0, 0.5, 2.0) is None


def test_condor_strikes_round_to_grid_and_order_correctly():
    ks = condor_strikes(spot=24487.0, otm_pct=0.05, step=50.0, wing_steps=4)
    assert ks["short_call"] % 50 == 0 and ks["short_put"] % 50 == 0
    assert ks["long_call"] == ks["short_call"] + 200
    assert ks["long_put"] == ks["short_put"] - 200
    assert ks["short_put"] < 24487.0 < ks["short_call"]


def test_condor_strikes_stay_otm_on_a_coarse_grid():
    # At spot ~300 a 50-point grid would round 5% OTM back to ATM; the
    # short strikes must still land at least one step beyond spot.
    ks = condor_strikes(spot=300.0, otm_pct=0.05, step=50.0, wing_steps=4)
    assert ks["short_call"] >= 350.0
    assert ks["short_put"] <= 250.0
    assert ks["short_put"] < 300.0 < ks["short_call"]


def test_condor_credit_is_positive_and_defined_risk():
    ks = condor_strikes(spot=24500.0, otm_pct=0.05, step=50.0, wing_steps=4)
    credits = price_condor_credit(24500.0, ks, iv=0.18, t_years=7 / 365)
    assert credits["call"] > 0 and credits["put"] > 0
    # Defined risk: credit must be below the wing width on each side.
    assert credits["call"] < 200 and credits["put"] < 200


def test_viable_credit_rejects_noise_for_full_margin():
    assert viable_credit(credit=10.0, wing_width=200.0)        # 5% of width: fine
    assert not viable_credit(credit=0.5, wing_width=200.0)     # noise: skip
    assert not viable_credit(credit=1.0, wing_width=0.0)
