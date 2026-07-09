"""QA-8: loop integration — confluence sleeve, calendar surprise, LLM-free research."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import Base, ResearchNote
from ats.core.schemas import Stance
from ats.services.risk.event_calendar import EventCalendar, surprise_pct
from ats.services.strategies.library import TechConfluence, default_strategies


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


def _ohlcv(close: np.ndarray) -> pd.DataFrame:
    prev = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "open": prev, "high": np.maximum(prev, close) * 1.002,
        "low": np.minimum(prev, close) * 0.998, "close": close,
        "volume": np.full(len(close), 1e6),
    })


# --- tech_confluence sleeve -------------------------------------------------

def test_tech_confluence_buys_uptrend_on_support():
    close = np.linspace(90.0, 105.0, 250)   # smooth uptrend: price sits on prior pivot
    sig = TechConfluence().evaluate("X", _ohlcv(close))
    assert sig is not None and sig.stance == Stance.BUY
    assert "tech_score" in sig.features and sig.features["tech_score"] >= 6


def test_tech_confluence_exits_on_rollover():
    close = np.linspace(105.0, 80.0, 250)   # downtrend -> summary rolls over
    sig = TechConfluence().evaluate("X", _ohlcv(close))
    assert sig is not None and sig.stance == Stance.SELL


def test_tech_confluence_registered_as_shadow():
    from ats.services.reference import STRATEGIES
    row = next((r for r in STRATEGIES if r[0] == "tech_confluence"), None)
    assert row is not None and row[3] == "shadow"
    assert any(s.id == "tech_confluence" for s in default_strategies())


# --- calendar surprise ------------------------------------------------------

def test_surprise_pct_math():
    assert surprise_pct(1.0, 1.5) == pytest.approx(-33.3333, abs=1e-3)  # miss
    assert surprise_pct(1.5, 1.0) == pytest.approx(50.0)                # beat
    assert surprise_pct(1.0, 0) is None
    assert surprise_pct(None, 1.0) is None


def test_calendar_carries_estimate_actual_and_surprise(tmp_path):
    cal_file = tmp_path / "cal.yaml"
    cal_file.write_text(
        "global:\n"
        "  - {date: 2026-08-06, kind: cpi, estimate: 5.0, actual: 5.5}\n",
        encoding="utf-8",
    )
    cal = EventCalendar(path=cal_file)
    from datetime import date
    ev = cal.global_events(date(2026, 8, 6))[0]
    assert ev["estimate"] == 5.0 and ev["actual"] == 5.5
    assert ev["surprise_pct"] == pytest.approx(10.0)


# --- deterministic (LLM-free) fundamentals pass -----------------------------

class _FakeAnalytics:
    def table(self):
        return [
            {"symbol": "WEAK.NS", "f_score": 1, "verdict": "overvalued", "mos_pct": -35},
            {"symbol": "GOOD.NS", "f_score": 8, "verdict": "undervalued", "mos_pct": 30},
        ]
    def presets(self):
        return ["value", "quality"]
    def screener(self, preset):
        return [{"symbol": "GOOD.NS"}] if preset in ("value", "quality") else []


class _FakeOrch:
    def get(self, name):
        return _FakeAnalytics() if name == "analytics" else None


def test_deterministic_fundamentals_writes_note_no_llm(memdb):
    from ats.services.research.factory import ResearchFactoryService
    svc = ResearchFactoryService()
    svc._orch = _FakeOrch()
    out = svc._deterministic_fundamentals("fundamentals_analyst")
    assert out["ok"] and out["llm"] is False and out["flags"] >= 2
    with db.session_scope() as s:
        note = s.execute(select(ResearchNote)
                         .order_by(ResearchNote.id.desc())).scalars().first()
    assert note is not None and note.meta.get("llm") is False
    assert "WEAK.NS" in note.content and "value" in note.meta["screener_hits"]
