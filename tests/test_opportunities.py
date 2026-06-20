"""Tests for the opportunity aggregator and the result-oriented REST endpoints.

Uses an isolated in-memory SQLite (StaticPool so every session shares one
connection) so it never touches the dev database.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import (
    Base,
    Decision,
    Fill,
    NewsItem,
    Ohlcv,
    Order,
    PnlDaily,
    SentimentScore,
    Signal,
    SmeOpinion,
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


def _seed_signals():
    with db.session_scope() as s:
        s.add(Signal(strategy="momentum", symbol="TCS", stance="buy", conviction=0.85, features={}))
        s.add(SmeOpinion(sme="finance", symbol="TCS", stance="buy", conviction=0.7,
                         rationale="Strong order book and margin expansion.", key_risks=["fx", "margin"]))
        s.add(Signal(strategy="meanrev", symbol="INFY", stance="sell", conviction=0.30, features={}))
        s.add(Signal(strategy="trend", symbol="NIFTY", stance="neutral", conviction=0.9, features={}))


def test_aggregator_ranks_and_scores(memdb):
    _seed_signals()
    from ats.services.opportunities import build_opportunities

    opps = build_opportunities(None, limit=10)
    syms = [o["symbol"] for o in opps]
    assert "TCS" in syms
    assert "NIFTY" not in syms  # neutral-only symbol is excluded
    tcs = next(o for o in opps if o["symbol"] == "TCS")
    assert tcs["side"] == "LONG"
    assert tcs["n_signals"] == 1 and tcs["n_opinions"] == 1
    assert 0.0 < tcs["score"] <= 1.0
    assert tcs["thesis"]
    assert "fx" in tcs["risks"]
    # agreement + high conviction beats the lone weak INFY signal
    assert syms.index("TCS") < syms.index("INFY")


def test_detail_includes_contributors(memdb):
    _seed_signals()
    from ats.services.opportunities import opportunity_detail

    d = opportunity_detail(None, "TCS")
    assert d is not None
    assert len(d["signals"]) == 1
    assert len(d["opinions"]) == 1
    assert opportunity_detail(None, "ZZZZ") is None


@pytest.fixture()
def client(memdb):
    from ats.server.results_api import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_endpoint_opportunities(client):
    _seed_signals()
    r = client.get("/api/opportunities")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert any(o["symbol"] == "TCS" for o in body["opportunities"])


def test_endpoint_validates_symbol(client):
    r = client.get("/api/opportunities/this is not valid!!")
    assert r.json().get("error") == "invalid symbol"
    r = client.get("/api/ohlcv", params={"symbol": "TCS", "interval": "bogus"})
    assert r.json().get("error") == "invalid interval"


def test_endpoint_ohlcv_and_annotations(client):
    with db.session_scope() as s:
        for i in range(3):
            s.add(Ohlcv(symbol="TCS", ts=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
                        interval="1d", open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1000))
        o = Order(symbol="TCS", side="BUY", qty=10, status="FILLED", account="paper")
        s.add(o)
        s.flush()
        s.add(Fill(order_id=o.id, qty=10, price=100.0, fees=1.0))
        s.add(Signal(strategy="momentum", symbol="TCS", stance="buy", conviction=0.8))
    rc = client.get("/api/ohlcv", params={"symbol": "TCS", "interval": "1d"})
    assert rc.status_code == 200 and rc.json()["count"] == 3
    candle = rc.json()["candles"][0]
    assert {"time", "open", "high", "low", "close"} <= set(candle)
    ra = client.get("/api/annotations", params={"symbol": "TCS"})
    kinds = {m["kind"] for m in ra.json()["markers"]}
    assert "fill" in kinds and "signal" in kinds


def test_endpoint_news_filters(client):
    with db.session_scope() as s:
        n = NewsItem(ts=datetime(2026, 1, 1, tzinfo=timezone.utc), source="x", title="TCS wins deal",
                     body="big body", tickers=["TCS"], raw_hash="h1")
        s.add(n)
        s.flush()
        s.add(SentimentScore(symbol="TCS", news_id=n.id, label="positive", score=0.6))
        s.add(NewsItem(ts=datetime(2026, 1, 2, tzinfo=timezone.utc), source="y", title="generic",
                       body="b", tickers=[], raw_hash="h2"))
    r = client.get("/api/news", params={"ticker": "TCS"})
    body = r.json()
    assert body["count"] == 1 and body["news"][0]["title"] == "TCS wins deal"
    rid = body["news"][0]["id"]
    reader = client.get(f"/api/news/{rid}").json()
    assert reader["body"] == "big body" and reader["sentiment"]["label"] == "positive"
    assert client.get("/api/news", params={"sentiment": "bogus"}).json().get("error")


def test_endpoint_equity_and_brief(client):
    with db.session_scope() as s:
        s.add(PnlDaily(account="paper", day=date(2026, 1, 1), equity=1_000_000, net=0, drawdown=0))
        s.add(PnlDaily(account="paper", day=date(2026, 1, 2), equity=1_010_000, net=10_000, drawdown=0))
        s.add(Signal(strategy="momentum", symbol="TCS", stance="buy", conviction=0.8))
    eq = client.get("/api/equity_curve").json()
    assert eq["count"] == 2 and eq["points"][-1]["equity"] == 1_010_000
    br = client.get("/api/brief").json()
    assert br["brief"]  # templated narrative when no real LLM
    assert br["real"] is False
