"""P-news: the three keyed news collectors — pure parse tests (no network)."""

from __future__ import annotations

from ats.services.scraper.collectors import (
    CurrentsCollector,
    NewsApiCollector,
    NewsDataCollector,
)


def test_newsapi_parse():
    data = {"articles": [{
        "source": {"name": "ET"}, "url": "http://x", "title": "TCS Q2 beats",
        "description": "profit up", "publishedAt": "2026-07-10T10:00:00Z",
    }]}
    items = NewsApiCollector._parse(data)
    assert items == [{"source": "newsapi:ET", "url": "http://x",
                      "title": "TCS Q2 beats", "body": "profit up",
                      "ts": "2026-07-10T10:00:00Z"}]


def test_newsdata_parse():
    data = {"results": [{
        "source_id": "mint", "link": "http://y", "title": "Rupee slips",
        "description": "vs dollar", "pubDate": "2026-07-10 09:00:00",
    }]}
    items = NewsDataCollector._parse(data)
    assert items[0]["source"] == "newsdata:mint" and items[0]["url"] == "http://y"


def test_currents_parse_and_empty():
    data = {"news": [{
        "author": "", "url": "http://z", "title": "Gold rallies",
        "description": "safe haven", "published": "2026-07-10 08:00:00 +0000",
    }]}
    items = CurrentsCollector._parse(data)
    assert items[0]["source"] == "currents:wire" and items[0]["title"] == "Gold rallies"
    assert NewsApiCollector._parse({}) == []
    assert NewsDataCollector._parse({"results": None}) == []


def test_throttle_gates_second_call():
    c = NewsApiCollector("k", min_interval_s=3600.0)
    assert c._throttled() is False   # first call passes
    assert c._throttled() is True    # immediate second call is gated
