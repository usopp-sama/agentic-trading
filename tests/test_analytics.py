"""QA-7: AnalyticsService (snapshots, movers, screener) + API."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import AnalyticsSnapshot, Base
from ats.services.analytics.service import AnalyticsService


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


def _ohlcv(close: np.ndarray) -> pd.DataFrame:
    prev = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({
        "open": prev,
        "high": np.maximum(prev, close) * 1.002,
        "low": np.minimum(prev, close) * 0.998,
        "close": close,
        "volume": np.full(len(close), 1_000_000.0),
    })


class _FakeMD:
    def __init__(self, frames):
        self._f = frames
    def watchlist(self):
        return list(self._f)
    def get_history(self, sym, limit=400):
        return self._f[sym]


class _FakeFund:
    def get(self, sym):
        return {"pe": 12.0, "pb": 2.0, "roe": 0.2, "dividend_yield": 0.05}


class _FakeOrch:
    def __init__(self, md):
        self._m = {"market_data": md, "fundamentals": _FakeFund()}
    def get(self, n):
        return self._m.get(n)


def _service(frames):
    md = _FakeMD(frames)
    svc = AnalyticsService()
    svc._md = md
    svc._orch = _FakeOrch(md)
    return svc


UPTREND = 100.0 * (1.01 ** np.arange(210))
FLAT = np.full(210, 100.0)


def test_close_pass_persists_snapshots(memdb):
    svc = _service({"UP.NS": _ohlcv(UPTREND), "FLAT.NS": _ohlcv(FLAT)})
    n = svc.run_close_pass()
    assert n == 2
    snap = svc.get("UP.NS")
    assert snap is not None
    assert snap["summary"]["label"] in ("buy", "strong_buy")
    assert "levels" in snap and "pivots" in snap["levels"]
    assert snap["metrics"]["pe"] == 12.0  # from fundamentals


def test_close_pass_idempotent_per_day(memdb):
    svc = _service({"UP.NS": _ohlcv(UPTREND)})
    svc.run_close_pass()
    svc.run_close_pass()
    with db.session_scope() as s:
        count = s.execute(select(func.count()).select_from(AnalyticsSnapshot)).scalar()
    assert count == 1


def test_movers(memdb):
    up = FLAT.copy(); up[-1] = 106.0   # +6% last bar
    dn = FLAT.copy(); dn[-1] = 96.0    # -4% last bar
    svc = _service({"UP.NS": _ohlcv(up), "DN.NS": _ohlcv(dn)})
    out = svc.run_poll_pass()
    assert out["gainers"][0]["symbol"] == "UP.NS"
    assert out["losers"][0]["symbol"] == "DN.NS"


def test_screener_momentum_preset(memdb):
    svc = _service({"UP.NS": _ohlcv(UPTREND), "FLAT.NS": _ohlcv(FLAT)})
    svc.run_close_pass()
    syms = {r["symbol"] for r in svc.screener("momentum")}
    assert "UP.NS" in syms          # strong tech score, near 52w high
    assert "FLAT.NS" not in syms    # flat -> tech score 0
    assert len(svc.screener()) == 2  # no preset -> whole table


def test_api_endpoints(memdb):
    from starlette.testclient import TestClient

    from ats.server.app import create_app

    svc = _service({"UP.NS": _ohlcv(UPTREND)})
    svc.run_close_pass()

    class _O:
        def get(self, n):
            return svc if n == "analytics" else None

    app = create_app()
    app.state.orchestrator = _O()
    c = TestClient(app)
    assert c.get("/api/analytics").json()["rows"]
    assert c.get("/api/analytics/UP.NS").json()["symbol"] == "UP.NS"
    assert "gainers" in c.get("/api/movers").json()
    sc = c.get("/api/screener?preset=momentum").json()
    assert "rows" in sc and "presets" in sc
