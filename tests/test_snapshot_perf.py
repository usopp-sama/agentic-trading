"""P0.4: batched sentiment lookup, news_id index, cached snapshot."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import Base, NewsItem, SentimentScore
from ats.services.dashboard.service import DashboardService
from ats.services.dashboard.snapshot import build_snapshot


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


class _FakeMD:
    def watchlist(self):
        return ["RELIANCE.NS"]
    def data_status(self):
        return {"mode": "synthetic"}


class _FakeOrch:
    def __init__(self):
        self._m = {"market_data": _FakeMD()}
    def get(self, name):
        return self._m.get(name)


def _seed_news(n=3):
    with db.session_scope() as s:
        for i in range(n):
            item = NewsItem(source="x", title=f"news {i}", url="", body="",
                            tickers=["RELIANCE.NS"], raw_hash=f"h{i}")
            s.add(item)
            s.flush()
            s.add(SentimentScore(symbol="RELIANCE.NS", news_id=item.id,
                                 label="positive", score=0.8))


def test_snapshot_attaches_sentiment_via_batched_query(memdb):
    _seed_news(3)
    snap = build_snapshot(_FakeOrch())
    wl = snap["watchlist_news"]
    assert wl and all(n["sentiment"]["label"] == "positive" for n in wl)
    assert wl[0]["sentiment"]["score"] == 0.8


def test_news_id_is_indexed():
    # the model declares the index (fresh DBs get it via create_all;
    # existing DBs get it via the explicit CREATE INDEX in init_db)
    assert SentimentScore.__table__.columns["news_id"].index is True


def test_dashboard_service_caches_snapshot(memdb):
    _seed_news(1)
    svc = DashboardService()
    svc._orch = _FakeOrch()
    assert svc._latest is None
    snap = svc.snapshot()               # lazy build + cache
    assert svc._latest is snap
    # a broadcast refreshes the cache off-loop
    asyncio.run(svc.broadcast_snapshot())
    assert svc._latest is not None and "portfolio" in svc._latest
