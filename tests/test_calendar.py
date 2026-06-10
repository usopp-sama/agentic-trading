"""Tests for the NSE trading calendar (IST hours + 2026 holidays)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from ats.services.market_data.calendar import (
    IST,
    has_holiday_data,
    is_market_open,
    is_polling_window,
    is_trading_day,
    to_ist,
)


def _ist(y, m, d, hh, mm) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=IST)


def test_weekends_are_not_trading_days():
    assert not is_trading_day(date(2026, 6, 13))  # Saturday
    assert not is_trading_day(date(2026, 6, 14))  # Sunday
    assert is_trading_day(date(2026, 6, 15))      # Monday


def test_2026_holidays_are_closed():
    assert has_holiday_data(2026)
    for holiday in (
        date(2026, 1, 26),   # Republic Day
        date(2026, 3, 3),    # Holi
        date(2026, 6, 26),   # Muharram
        date(2026, 10, 20),  # Dussehra
        date(2026, 12, 25),  # Christmas
    ):
        assert not is_trading_day(holiday)


def test_unknown_year_degrades_to_weekday_check():
    assert not has_holiday_data(2031)
    assert is_trading_day(date(2031, 12, 25))  # Thursday; no list -> open


def test_market_hours_boundaries_ist():
    monday = (2026, 6, 15)
    assert not is_market_open(_ist(*monday, 9, 14))
    assert is_market_open(_ist(*monday, 9, 15))     # open is inclusive
    assert is_market_open(_ist(*monday, 12, 0))
    assert not is_market_open(_ist(*monday, 15, 30))  # close is exclusive
    assert not is_market_open(_ist(*monday, 20, 0))


def test_market_open_handles_utc_input():
    # 2026-06-15 06:00 UTC == 11:30 IST -> open.
    assert is_market_open(datetime(2026, 6, 15, 6, 0, tzinfo=timezone.utc))
    # 2026-06-15 03:00 UTC == 08:30 IST -> pre-open.
    assert not is_market_open(datetime(2026, 6, 15, 3, 0, tzinfo=timezone.utc))


def test_market_closed_on_holiday_even_during_hours():
    assert not is_market_open(_ist(2026, 1, 26, 11, 0))  # Republic Day


def test_polling_window_includes_post_close_grace():
    monday = (2026, 6, 15)
    assert is_polling_window(_ist(*monday, 15, 45))       # within 45-min grace
    assert not is_polling_window(_ist(*monday, 16, 16))   # past grace
    assert not is_polling_window(_ist(2026, 6, 13, 12, 0))  # Saturday


def test_to_ist_assumes_utc_for_naive():
    ist = to_ist(datetime(2026, 6, 15, 6, 0))
    assert (ist.hour, ist.minute) == (11, 30)
