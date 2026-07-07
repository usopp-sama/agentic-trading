"""Event-risk veto gate: calendar, F&O expiry, severity flag, manual veto."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import Base
from ats.services.risk.event_calendar import (
    EventCalendar,
    EventRiskService,
    last_thursday,
)


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


@pytest.fixture()
def svc(memdb, tmp_path):
    cal_file = tmp_path / "events.yaml"
    cal_file.write_text(
        """
global:
  - {date: 2026-08-06, kind: rbi_mpc, note: MPC decision}
symbols:
  RELIANCE.NS:
    - {date: 2026-07-20, kind: earnings}
""",
        encoding="utf-8",
    )
    return EventRiskService(calendar=EventCalendar(cal_file))


def _non_expiry(day: date) -> date:
    """Nudge off the F&O expiry so tests only see the veto under test."""
    while day == last_thursday(day.year, day.month):
        day += timedelta(days=1)
    return day


# --- computed F&O expiry -----------------------------------------------------
def test_last_thursday_is_a_thursday_in_month():
    for y, m in [(2026, 7), (2026, 12), (2027, 2)]:
        d = last_thursday(y, m)
        assert d.weekday() == 3
        assert d.month == m
        assert (d + timedelta(days=7)).month != m  # truly the last one


def test_fo_expiry_vetoes_everything(svc):
    d = last_thursday(2026, 7)
    assert "fo_expiry" in svc.active_vetoes("TCS.NS", on=d)


# --- calendar ------------------------------------------------------------------
def test_global_event_vetoes_every_symbol(svc):
    d = date(2026, 8, 6)
    assert "rbi_mpc" in svc.active_vetoes("TCS.NS", on=d)
    assert "rbi_mpc" in svc.active_vetoes("RELIANCE.NS", on=d)


def test_earnings_window_is_plus_minus_one_day(svc):
    for d in (date(2026, 7, 19), date(2026, 7, 20), date(2026, 7, 21)):
        assert "earnings_window" in svc.active_vetoes("RELIANCE.NS", on=d), d
    clear_day = _non_expiry(date(2026, 7, 27))
    assert svc.active_vetoes("RELIANCE.NS", on=clear_day) == []
    # only the named symbol is vetoed
    assert "earnings_window" not in svc.active_vetoes("TCS.NS", on=date(2026, 7, 20))


def test_missing_calendar_file_is_not_fatal(memdb, tmp_path):
    svc = EventRiskService(calendar=EventCalendar(tmp_path / "nope.yaml"))
    assert svc.active_vetoes("TCS.NS", on=_non_expiry(date(2026, 7, 6))) == []


# --- severity flag ----------------------------------------------------------------
def test_negative_burst_sets_one_session_severity_veto(svc):
    for _ in range(3):
        svc.observe_sentiment({"tickers": ["TCS.NS"], "score": -0.8})
    assert "severity" in svc.active_vetoes("TCS.NS", on=date.today())
    # other names unaffected
    assert "severity" not in svc.active_vetoes("INFY.NS", on=date.today())
    # not active on any other day (one session only)
    assert "severity" not in svc.active_vetoes(
        "TCS.NS", on=date.today() + timedelta(days=1))


def test_mild_or_sparse_negativity_does_not_trip(svc):
    svc.observe_sentiment({"tickers": ["INFY.NS"], "score": -0.9})
    assert "severity" not in svc.active_vetoes("INFY.NS", on=date.today())
    for _ in range(5):
        svc.observe_sentiment({"tickers": ["WIPRO.NS"], "score": -0.2})
    assert "severity" not in svc.active_vetoes("WIPRO.NS", on=date.today())


# --- manual veto ------------------------------------------------------------------
def test_manual_symbol_veto_set_and_clear(svc):
    on = _non_expiry(date(2026, 7, 6))
    svc.set_manual_veto("TCS.NS", True, reason="something smells off")
    assert "manual" in svc.active_vetoes("TCS.NS", on=on)
    assert "manual" not in svc.active_vetoes("INFY.NS", on=on)
    svc.set_manual_veto("TCS.NS", False)
    assert svc.active_vetoes("TCS.NS", on=on) == []


def test_manual_global_veto(svc):
    on = _non_expiry(date(2026, 7, 6))
    svc.set_manual_veto(None, True)
    assert "manual_global" in svc.active_vetoes("ANYTHING.NS", on=on)
    svc.set_manual_veto(None, False)
    assert svc.active_vetoes("ANYTHING.NS", on=on) == []
