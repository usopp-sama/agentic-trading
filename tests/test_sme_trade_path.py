"""WS-3: the SME trade path is a config switch, not a code deletion.

With ``ATS_SME_TRADE_PATH=false`` the news/spike -> SME -> proposal
autonomous path must spend nothing and publish nothing, while manual runs
still produce full analysis (opinions + CIO synthesis) — just no orders.
"""

from __future__ import annotations

import asyncio

import pytest

import ats.services.agents.service as agent_mod
from ats.core.config import get_settings
from ats.core.events import Event, Topic
from ats.core.schemas import Opinion, ProposedPosition, Stance
from ats.services.agents.service import AgentService


class _BusSpy:
    def __init__(self):
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic, payload):
        self.published.append((topic, payload))


class _RuntimeStub:
    async def run(self, persona, symbol, bus):
        return Opinion(sme=persona["id"], symbol=symbol,
                       stance=Stance.BUY, conviction=0.8)


class _CioStub:
    def aggregate(self, symbol, opinions, weights, macro_tilt):
        return ProposedPosition(symbol=symbol, action="BUY",
                                target_weight=0.05, conviction=0.8)


@pytest.fixture()
def svc(monkeypatch):
    monkeypatch.setattr(agent_mod, "eval_window_open", lambda: True)
    s = AgentService()
    s._bus = _BusSpy()
    s._runtime = _RuntimeStub()
    s._cio = _CioStub()
    s._symbol_personas = [{"id": "sme_a", "family": "A", "weight": 1.0,
                           "status": "active"}]
    return s


def _set_path(monkeypatch, enabled: bool):
    monkeypatch.setattr(get_settings(), "sme_trade_path", enabled)


def test_path_on_publishes_proposal(svc, monkeypatch):
    _set_path(monkeypatch, True)
    asyncio.run(svc.run_symbol("TCS.NS"))
    topics = [t for t, _ in svc._bus.published]
    assert Topic.PROPOSAL in topics


def test_path_off_still_analyzes_but_never_proposes(svc, monkeypatch):
    _set_path(monkeypatch, False)
    opinions, proposal = asyncio.run(svc.run_symbol("TCS.NS"))
    assert opinions and proposal.action == "BUY"  # analysis intact
    assert svc._bus.published == []               # but no order path


def test_path_off_ignores_news_and_spikes(svc, monkeypatch):
    _set_path(monkeypatch, False)
    called = []

    async def _spy_evaluate(symbols, force=None):
        called.append(symbols)

    monkeypatch.setattr(svc, "_evaluate", _spy_evaluate)
    asyncio.run(svc._on_sentiment(Event(Topic.SENTIMENT, {
        "tickers": ["TCS.NS"], "score": -0.9, "title": "bad news"})))
    asyncio.run(svc._on_spike(Event(Topic.VOLUME_SPIKE, {
        "symbol": "TCS.NS", "zscore": 4.0})))
    assert called == []  # zero autonomous LLM spend


def test_path_on_news_still_evaluates(svc, monkeypatch):
    _set_path(monkeypatch, True)
    called = []

    async def _spy_evaluate(symbols, force=None):
        called.append(list(symbols))

    monkeypatch.setattr(svc, "_evaluate", _spy_evaluate)
    monkeypatch.setattr(svc, "_maybe_refresh_macro_from_news",
                        _spy_evaluate)  # avoid runtime macro pass
    asyncio.run(svc._on_sentiment(Event(Topic.SENTIMENT, {
        "tickers": ["TCS.NS"], "score": -0.9, "title": "bad news"})))
    assert called and called[0] == ["TCS.NS"]
