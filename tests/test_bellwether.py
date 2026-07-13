"""Tests for Bellwether P1 - the figure registry + GDELT collector.

No network: the GDELT HTTP layer is injected. Covers the pure parsers, the
registry integrity, the 429 backoff-and-retry, and the daily corpus assembly.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ats.services.bellwether import figures as fig_mod
from ats.services.bellwether.collector import _merge_daily, _verdict, collect_figure
from ats.services.bellwether.gdelt import (
    GdeltClient,
    GdeltError,
    parse_artlist,
    parse_timeline,
)


# --- registry ---------------------------------------------------------------
def test_registry_is_valid_and_filterable():
    fig_mod.validate()  # raises on any malformed entry
    assert "modi" in fig_mod.FIGURES
    subset = fig_mod.get_figures(["modi", "trump", "nonexistent"])
    assert {f.key for f in subset} == {"modi", "trump"}
    assert fig_mod.get_figures([]) == fig_mod.all_figures()


# --- pure parsers -----------------------------------------------------------
def test_parse_timeline_extracts_dated_values():
    payload = {"timeline": [{"series": "Average Tone", "data": [
        {"date": "20230101T000000Z", "value": 1.5},
        {"date": "20230102T000000Z", "value": -0.5},
        {"date": "bad", "value": 9},          # dropped
    ]}]}
    out = parse_timeline(payload)
    assert out == [{"date": "2023-01-01", "value": 1.5},
                   {"date": "2023-01-02", "value": -0.5}]
    assert parse_timeline({}) == []


def test_parse_artlist_shapes_headlines():
    payload = {"articles": [
        {"seendate": "20260713T161500Z", "title": "Modi on infra push",
         "url": "http://x", "domain": "x.com", "sourcecountry": "India"},
    ]}
    out = parse_artlist(payload)
    assert len(out) == 1 and out[0]["country"] == "India"
    assert out[0]["title"].startswith("Modi")
    assert parse_artlist({}) == []


# --- client: 429 backoff-and-retry (no real network, no real sleeping) ------
class _FakeHttp:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, url, params):
        self.calls += 1
        return self._responses.pop(0)


def test_client_retries_on_429_then_succeeds():
    ok = {"timeline": [{"data": [{"date": "20230101T000000Z", "value": 0.2}]}]}
    http = _FakeHttp([(429, None, "rate limited"),
                      (429, None, "rate limited"),
                      (200, ok, "")])
    slept: list[float] = []
    client = GdeltClient(delay=0, backoff=1.0, max_retries=4,
                         http_get=http, sleep=slept.append)
    out = client.timeline_tone('"Narendra Modi"', date(2023, 1, 1), date(2023, 1, 2))
    assert http.calls == 3                       # two 429s then success
    assert out == [{"date": "2023-01-01", "value": 0.2}]
    assert len(slept) >= 2                        # backed off between retries


def test_client_raises_after_exhausting_retries():
    http = _FakeHttp([(429, None, "x")] * 5)
    client = GdeltClient(delay=0, backoff=0.0, max_retries=2, http_get=http, sleep=lambda _: None)
    try:
        client.get({"mode": "timelinetone"})
        assert False, "should have raised"
    except GdeltError:
        pass


# --- collector assembly -----------------------------------------------------
def test_merge_daily_joins_tone_and_volume():
    tone = [{"date": "2023-01-01", "value": 1.0}, {"date": "2023-01-02", "value": 2.0}]
    vol = [{"date": "2023-01-01", "value": 10.0}, {"date": "2023-01-02", "value": 20.0}]
    df = _merge_daily(tone, vol)
    assert list(df.columns) == ["tone", "volume"]
    assert df["tone"].tolist() == [1.0, 2.0] and df["volume"].tolist() == [10.0, 20.0]
    assert _merge_daily([], vol).empty


def test_verdict_thresholds():
    start, end = date(2023, 1, 1), date(2026, 1, 1)  # ~3y
    rich = pd.DataFrame({"tone": [0.0] * 500, "volume": [1] * 500},
                        index=pd.date_range("2023-01-01", periods=500))  # ~46% of ~3y
    assert _verdict(rich, start, end) == "RICH"
    assert _verdict(pd.DataFrame(columns=["tone", "volume"]), start, end) == "UNAVAILABLE"


def test_collect_figure_uses_injected_client(monkeypatch):
    tone = {"timeline": [{"data": [{"date": "20230101T000000Z", "value": 0.3}]}]}
    vol = {"timeline": [{"data": [{"date": "20230101T000000Z", "value": 5.0}]}]}
    arts = {"articles": [{"seendate": "20230101T000000Z", "title": "hi",
                          "url": "u", "domain": "d", "sourcecountry": "India"}]}
    http = _FakeHttp([(200, tone, ""), (200, vol, ""), (200, arts, "")])
    client = GdeltClient(delay=0, http_get=http, sleep=lambda _: None)
    corpus = collect_figure(client, fig_mod.FIGURES["modi"], date(2023, 1, 1), date(2023, 1, 2))
    assert len(corpus.daily) == 1
    assert corpus.headlines[0]["title"] == "hi"
    assert corpus.stats()["figure"] == "modi"
