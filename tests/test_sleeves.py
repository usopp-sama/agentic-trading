"""Tests for sleeve virtual P&L attribution and decay detection."""

from __future__ import annotations

from datetime import date, timedelta

from ats.services.strategies.sleeves import SleeveTracker

D0 = date(2026, 1, 5)


def _day(n: int) -> date:
    return D0 + timedelta(days=n)


def test_return_accrues_to_yesterdays_holdings_only():
    t = SleeveTracker()
    # Day 0: bar arrives, THEN the strategy goes long (signal at the close).
    t.mark_bar("A", 100.0, _day(0))
    t.update_holding("s1", "A", +1)
    # Day 1: +10% bar. Finalizing day 0 must show zero P&L (no look-ahead);
    # the +10% accrues to day 1, where the holding was live.
    fin0 = t.mark_bar("A", 110.0, _day(1))
    assert [f.ret for f in fin0 if f.strategy == "s1"] == [0.0]
    fin1 = t.mark_bar("A", 110.0, _day(2))
    (f,) = [f for f in fin1 if f.strategy == "s1"]
    assert f.ret == pytest_approx(0.10)
    assert f.equity == pytest_approx(1.10)


def test_equal_weight_across_holdings():
    t = SleeveTracker()
    t.mark_bar("A", 100.0, _day(0))
    t.mark_bar("B", 100.0, _day(0))
    t.update_holding("s1", "A", +1)
    t.update_holding("s1", "B", +1)
    t.mark_bar("A", 110.0, _day(1))  # +10%
    t.mark_bar("B", 100.0, _day(1))  # flat
    fin = t.mark_bar("A", 110.0, _day(2))
    (f,) = [f for f in fin if f.strategy == "s1"]
    assert f.ret == pytest_approx(0.05)  # (10% + 0%) / 2


def test_exited_holding_stops_accruing():
    t = SleeveTracker()
    t.mark_bar("A", 100.0, _day(0))
    t.update_holding("s1", "A", +1)
    t.mark_bar("A", 110.0, _day(1))
    t.update_holding("s1", "A", 0)  # exit at day 1 close
    t.mark_bar("A", 220.0, _day(2))  # huge move AFTER exit
    fin = t.mark_bar("A", 220.0, _day(3))
    (f,) = [f for f in fin if f.strategy == "s1"]
    assert f.ret == 0.0
    book_equity = [s for s in t.stats() if s["strategy"] == "s1"][0]["equity"]
    assert book_equity == pytest_approx(1.10)  # only day 1's gain


def test_decay_flag_fires_on_persistent_losses():
    t = SleeveTracker(decay_sharpe=0.0, decay_min_days=30)
    t.mark_bar("A", 1000.0, _day(0))
    t.update_holding("s1", "A", +1)
    price, flagged = 1000.0, False
    for n in range(1, 40):
        price *= 0.995  # steady bleed -> deeply negative Sharpe
        for f in t.mark_bar("A", price, _day(n)):
            flagged = flagged or (f.strategy == "s1" and f.decayed)
    assert flagged
    assert t.rolling_sharpe("s1") < 0


def test_healthy_sleeve_is_not_flagged():
    t = SleeveTracker(decay_sharpe=0.0, decay_min_days=30)
    t.mark_bar("A", 1000.0, _day(0))
    t.update_holding("s1", "A", +1)
    price = 1000.0
    for n in range(1, 40):
        price *= 1.003
        for f in t.mark_bar("A", price, _day(n)):
            assert not (f.strategy == "s1" and f.decayed)
    assert t.rolling_sharpe("s1") > 0
    assert t.max_drawdown("s1") == 0.0


def test_stats_shape():
    t = SleeveTracker()
    t.mark_bar("A", 100.0, _day(0))
    t.update_holding("s1", "A", +1)
    t.mark_bar("A", 101.0, _day(1))
    (s,) = t.stats()
    assert s["strategy"] == "s1"
    assert s["holdings"] == ["A"]
    assert set(s) == {"strategy", "equity", "days", "holdings", "sharpe", "max_drawdown"}


def pytest_approx(x: float):
    import pytest

    return pytest.approx(x, rel=1e-9, abs=1e-12)
