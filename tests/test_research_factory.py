"""Slow-loop research factory: registry lifecycle, roles, budget, committee.

A fake LLM returns canned JSON per role so every path is deterministic and
offline; the registry is exercised end-to-end (propose → … → LIVE) with the
illegal moves asserted to fail.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core import state
from ats.core.models import AllocationRecommendation, Base, ResearchNote
from ats.services.research import hypotheses as registry
from ats.services.research import roles as R
from ats.services.research.factory import ResearchFactoryService
from ats.services.research.hypotheses import RegistryError
from ats.services.strategies.allocation import apply_committee_tilt


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


class FakeLLM:
    """Canned-JSON chat client; records what it was asked."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    def chat(self, system, messages, json_mode=False):
        self.calls.append((system, messages[-1]["content"]))
        return self.reply


# --- registry lifecycle -----------------------------------------------------------
def test_full_lifecycle_and_audit_trail(memdb):
    h = registry.propose(agent="strategy_researcher", title="Momo after RBI days",
                         thesis="drift after policy days")
    assert h["stage"] == "PROPOSED"
    h = registry.specify(h["id"], rule="Buy NIFTYBEES at close on MPC day, exit +3 sessions")
    assert h["stage"] == "SPECIFIED"
    h = registry.attach_backtest(h["id"], {"sharpe": 0.9, "deflated_sharpe": 0.4, "windows": 6})
    assert h["stage"] == "BACKTESTED"
    for stage in ("SHADOW", "PAPER", "LIVE"):
        h = registry.advance(h["id"], stage, actor="human")
        assert h["stage"] == stage
    moves = [(e["from"], e["to"]) for e in h["events"]]
    assert moves[0] == ("", "PROPOSED")
    assert ("BACKTESTED", "SHADOW") in moves and ("PAPER", "LIVE") in moves


def test_illegal_moves_rejected(memdb):
    h = registry.propose(agent="a", title="skip the gate")
    with pytest.raises(RegistryError):
        registry.advance(h["id"], "SHADOW", actor="a")  # no gate result
    with pytest.raises(RegistryError):
        registry.advance(h["id"], "SPECIFIED", actor="a")  # no rule attached
    with pytest.raises(RegistryError):
        registry.specify(h["id"], rule="   ")  # blank rule
    registry.advance(h["id"], "REJECTED", actor="human", note="not testable")
    with pytest.raises(RegistryError):
        registry.advance(h["id"], "PROPOSED", actor="a")  # REJECTED is terminal


def test_survival_scores(memdb):
    a = registry.propose(agent="researcher_x", title="one")
    registry.specify(a["id"], rule="r")
    registry.attach_backtest(a["id"], {"sharpe": 1.2})
    registry.advance(a["id"], "SHADOW", actor="gate")
    b = registry.propose(agent="researcher_x", title="two")
    registry.advance(b["id"], "REJECTED", actor="gate")
    registry.propose(agent="researcher_x", title="three")  # in flight
    scores = {s["agent"]: s for s in registry.survival_scores()}
    rec = scores["researcher_x"]
    assert (rec["proposed"], rec["survived"], rec["rejected"], rec["in_flight"]) == (3, 1, 1, 1)
    assert rec["survival_rate"] == 0.5


# --- role runs ---------------------------------------------------------------------
def _factory(reply: str) -> tuple[ResearchFactoryService, FakeLLM]:
    llm = FakeLLM(reply)
    svc = ResearchFactoryService(llm=llm, committee_llm=llm)
    return svc, llm


def test_researcher_creates_specified_hypotheses(memdb):
    reply = json.dumps({"hypotheses": [
        {"title": "Delivery-backed breakouts", "thesis": "flows persist",
         "rule": "Buy on 20d high + delivery% > 60; exit 10d low", "params": {"hold": 10},
         "universe": ["NIFTY50"], "evidence": "archive digest"},
        {"title": "Vague idea", "thesis": "no rule so must be dropped", "rule": ""},
    ]})
    svc, _ = _factory(reply)
    out = svc.run_role("strategy_researcher", actor="human")
    assert out["ok"] and out["hypotheses"] == 1
    rows = registry.list_all()
    mine = [h for h in rows if h["agent"] == "strategy_researcher"]
    assert len(mine) == 1
    assert mine[0]["stage"] == "SPECIFIED"
    assert "delivery" in mine[0]["rule"].lower()


def test_macro_pass_writes_note(memdb):
    reply = json.dumps({"commentary": "Range-bound; RBI on hold.",
                        "regime_view": "range/normal", "risk_flags": ["budget week"]})
    svc, _ = _factory(reply)
    out = svc.run_role("macro_analyst", actor="human")
    assert out["ok"] and out["notes"] == 1
    with db.session_scope() as s:
        note = s.execute(select(ResearchNote)).scalars().one()
        assert note.role == "macro_analyst"
        assert "RBI" in note.content
        assert note.meta["risk_flags"] == ["budget week"]


def test_unparseable_reply_becomes_note_never_registry_rows(memdb):
    svc, _ = _factory("[heuristic] the mock provider answers in prose, not JSON")
    out = svc.run_role("strategy_researcher", actor="human")
    assert out["ok"] and out["hypotheses"] == 0
    assert registry.list_all() == []
    with db.session_scope() as s:
        note = s.execute(select(ResearchNote)).scalars().one()
        assert note.meta.get("parse_error") is True


def test_committee_recommendation_clamped_and_persisted(memdb):
    reply = json.dumps({"summary": "Lean into trend", "rationale": "regime up",
                        "tilts": {"donchian_trend": 0.5,      # clamps to +0.10
                                  "mean_reversion": -0.03,
                                  "not_a_strategy": 0.9}})    # unknown id dropped
    svc, _ = _factory(reply)
    out = svc.run_role("committee", actor="human")
    assert out["ok"] and out["recommendations"] == 1
    with db.session_scope() as s:
        rec = s.execute(select(AllocationRecommendation)).scalars().one()
        assert rec.status == "pending"
        assert rec.tilts == {"donchian_trend": 0.10, "mean_reversion": -0.03}


def test_budget_blocks_scheduler_but_not_human(memdb, monkeypatch):
    svc, llm = _factory(json.dumps({"commentary": "x", "regime_view": "", "risk_flags": []}))
    monkeypatch.setattr(ResearchFactoryService, "budget_status",
                        lambda self: {"budget_inr": 500.0, "used_inr": 501.0, "exhausted": True})
    out = svc.run_role("macro_analyst")  # scheduler actor
    assert out["skipped"] == "budget" and not llm.calls
    out = svc.run_role("macro_analyst", actor="human")  # you clicked, you pay
    assert out["ok"] and len(llm.calls) == 1


def test_role_failure_is_contained(memdb):
    class Boom:
        def chat(self, *a, **k):
            raise RuntimeError("provider down")

    svc = ResearchFactoryService(llm=Boom(), committee_llm=Boom())
    out = svc.run_role("risk_reviewer", actor="human")
    assert out["ok"] is False and "provider down" in out["error"]
    with db.session_scope() as s:
        assert s.execute(select(ResearchNote)).scalars().one().meta["error"] is True


# --- committee approval + tilt application ------------------------------------------
def test_approve_sets_bounded_tilt_kv(memdb):
    reply = json.dumps({"summary": "s", "rationale": "r",
                        "tilts": {"donchian_trend": 0.08}})
    svc, _ = _factory(reply)
    svc.run_role("committee", actor="human")
    with db.session_scope() as s:
        rec_id = s.execute(select(AllocationRecommendation)).scalars().one().id
    out = svc.approve_recommendation(rec_id, actor="human")
    assert out["status"] == "approved"
    assert state.get_kv("research:committee_tilt")["tilts"] == {"donchian_trend": 0.08}
    # Already decided → guard.
    assert svc.approve_recommendation(rec_id)["reason"] == "already decided"


def test_reject_leaves_no_tilt(memdb):
    reply = json.dumps({"summary": "s", "rationale": "r", "tilts": {"ts_momentum": -0.05}})
    svc, _ = _factory(reply)
    svc.run_role("committee", actor="human")
    with db.session_scope() as s:
        rec_id = s.execute(select(AllocationRecommendation)).scalars().one().id
    assert svc.reject_recommendation(rec_id)["status"] == "rejected"
    assert state.get_kv("research:committee_tilt") == {}


def test_apply_committee_tilt_bounds_and_renormalizes():
    w = {"a": 0.5, "b": 0.5}
    out = apply_committee_tilt(w, {"a": 0.10}, max_tilt=0.10)
    assert abs(sum(out.values()) - 1.0) < 1e-9
    assert out["a"] > 0.5 > out["b"]
    # A wild tilt is clamped to the bound, so the shift is identical to +10%.
    assert apply_committee_tilt(w, {"a": 5.0}, max_tilt=0.10) == out
    # Empty tilt = no-op.
    assert apply_committee_tilt(w, {}) == w


# --- seeds + maintenance -------------------------------------------------------------
def test_seed_hypotheses_idempotent(memdb):
    svc, _ = _factory("{}")
    svc.seed_default_hypotheses()
    svc.seed_default_hypotheses()
    rows = registry.list_all()
    assert len(rows) == 3
    by_title = {h["title"]: h for h in rows}
    veto = by_title["Flow-anomaly veto: refuse entries on pump signatures"]
    assert veto["stage"] == "SPECIFIED" and veto["agent"] == "human"
    ride = by_title["Institutional-flow momentum in liquid names"]
    assert ride["stage"] == "PROPOSED"  # deliberately unspecified until Hyp A pays
    # QA-8: the confluence sleeve is seeded as a specified hypothesis.
    conf = by_title["Confluence: composite summary + level support"]
    assert conf["stage"] == "SPECIFIED" and conf["agent"] == "human"


def test_nightly_maintenance_is_llm_free(memdb):
    svc, llm = _factory("{}")
    out = svc.nightly_maintenance()
    assert llm.calls == []          # zero LLM spend at night
    assert "news_24h" in out
    with db.session_scope() as s:
        note = s.execute(select(ResearchNote)).scalars().one()
        assert note.role == "nightly_digest"


# --- output parsing -------------------------------------------------------------------
def test_parse_output_tolerates_fences_and_prose():
    assert R.parse_output('```json\n{"a": 1}\n```') == {"a": 1}
    assert R.parse_output('Sure! Here you go: {"a": {"b": 2}} hope that helps') == {"a": {"b": 2}}
    assert R.parse_output("no json here") is None
    assert R.parse_output("[1, 2]") is None  # non-object JSON refused
    assert R.parse_output("") is None


def test_clamp_tilts_drops_junk():
    out = R.clamp_tilts({"x": "0.2", "y": "junk", "z": 0.0}, 0.10, known_ids={"x", "y", "z"})
    assert out == {"x": 0.10}
