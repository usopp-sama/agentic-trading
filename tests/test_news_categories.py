"""P3: news categorization — classifier, API filter/counts, backfill."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from ats.core import db
from ats.core.models import Base, NewsItem
from ats.server.app import create_app
from ats.services.scraper.categorize import CATEGORIES, categorize


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


@pytest.mark.parametrize("title,expected", [
    ("SEBI bars promoter in fraud case, trading halt ordered", "breaking"),
    ("Infosys Q2 net profit rises 11%, beats guidance", "earnings"),
    ("Morgan Stanley upgrades TCS, raises target price", "analyst_ratings"),
    ("XYZ Ltd IPO subscribed 12x on day 2; strong GMP", "ipo"),
    ("India CPI inflation eases to 4.9% in June", "economic_indicators"),
    ("Government unveils union budget with new tariff", "economy"),
    ("Gold prices jump as crude oil rallies", "commodities"),
    ("Rupee slips vs dollar as forex reserves dip", "currencies"),
    ("Bitcoin rallies past resistance; ethereum follows", "crypto"),
    ("Nifty ends flat as banks drag the market", "stock_markets"),
])
def test_categorize_each_category(title, expected):
    assert categorize(title, "") == expected


def test_categorize_priority_breaking_wins():
    # earnings-ish words present, but a breaking keyword takes priority
    assert categorize("Fraud probe hits firm despite strong Q1 profit", "") == "breaking"


def test_categories_list_is_the_canonical_set():
    assert set(CATEGORIES) == {
        "breaking", "earnings", "analyst_ratings", "ipo", "economic_indicators",
        "economy", "commodities", "currencies", "crypto", "stock_markets",
    }


def _seed(memdb):
    with db.session_scope() as s:
        s.add(NewsItem(title="Infosys Q2 profit rises", body="", tickers=[],
                       category="earnings", raw_hash="h1"))
        s.add(NewsItem(title="Gold rallies", body="", tickers=[],
                       category="commodities", raw_hash="h2"))
        s.add(NewsItem(title="Nifty flat", body="", tickers=[],
                       category="stock_markets", raw_hash="h3"))


def test_api_filters_by_category_and_returns_counts(memdb):
    _seed(memdb)
    c = TestClient(create_app())
    body = c.get("/api/news?category=earnings").json()
    assert body["count"] == 1 and body["news"][0]["category"] == "earnings"
    assert body["counts"]["earnings"] == 1 and body["counts"]["commodities"] == 1
    # no filter -> all three
    assert c.get("/api/news").json()["total"] == 3


def test_backfill_is_idempotent(memdb):
    with db.session_scope() as s:
        s.add(NewsItem(title="Morgan Stanley downgrades stock, cuts target price",
                       body="", tickers=[], category="", raw_hash="hx"))
    from scripts.backfill_news_categories import main

    assert main() == 0
    with db.session_scope() as s:
        row = s.execute(select(NewsItem).where(NewsItem.raw_hash == "hx")).scalar_one()
        assert row.category == "analyst_ratings"
    # second run changes nothing
    assert main() == 0
