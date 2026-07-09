"""P0.5: warm-from-store + background backfill; deferred analytics boot pass."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import Base, Ohlcv
from ats.services.analytics.service import AnalyticsService
from ats.services.market_data.service import MarketDataService


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


def test_warm_from_store_caches_fresh_and_flags_stale(memdb):
    now = datetime.now()
    with db.session_scope() as s:
        s.add(Ohlcv(symbol="FRESH.NS", ts=now, interval="1d",
                    open=1, high=1, low=1, close=10, volume=1))
        s.add(Ohlcv(symbol="STALE.NS", ts=now - timedelta(days=10), interval="1d",
                    open=1, high=1, low=1, close=20, volume=1))

    svc = MarketDataService.__new__(MarketDataService)
    svc._symbols = ["FRESH.NS", "STALE.NS", "MISSING.NS"]
    svc._history = {}
    svc._last_price = {}

    stale = svc._warm_from_store()
    # fresh symbol is cached from the DB (dashboard has data immediately)
    assert "FRESH.NS" in svc._history and svc._last_price["FRESH.NS"] == 10.0
    # stale + missing need a network backfill; fresh does not
    assert set(stale) == {"STALE.NS", "MISSING.NS"}
    assert "FRESH.NS" not in stale


def test_analytics_boot_pass_is_deferred(memdb):
    svc = AnalyticsService()

    class _Sched:
        def add_job(self, *a, **k):
            return None

    class _Orch:
        def get(self, n):
            return None

    class _Ctx:
        scheduler = _Sched()
        orchestrator = _Orch()

    async def run():
        await svc.start(_Ctx())
        # start() returns without having blocked on the close pass
        assert svc._boot_task is not None
        await svc._boot_task            # let the background pass finish
        assert svc._boot_task.done()

    asyncio.run(run())
