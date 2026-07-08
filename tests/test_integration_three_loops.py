"""Three-loop integration: every component wired together, offline.

The real InMemoryEventBus carries a strategy signal through the REAL
services — StrategyTrader consensus → RiskService guardrails/vetoes →
ExecutionService paper fill on the main book, while LeagueService trades
the same signal in the strategy's own ₹1L ledger-backed account. Then the
protective layers are exercised against that live state: reconciliation
(clean → corrupted → halted → released), the manual veto (entries blocked,
exits pass), and the slow loop's committee tilt reaching the medium loop's
allocator. Finally the production wiring itself is audited: every expected
service must register.

Each scenario runs inside ONE event loop (the bus dispatch task lives on
it); DB assertions happen after the loop returns — SQLite keeps the state.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.events import InMemoryEventBus, Topic
from ats.core.models import (
    AllocationRecommendation,
    Base,
    Decision,
    Fill,
    Instrument,
    Order,
    Position,
)
from ats.services.accounts.ledger import AccountLedger
from ats.services.accounts.league import LeagueService, solo_account
from ats.services.execution.reconcile import ReconciliationService, entries_halted
from ats.services.execution.service import ExecutionService
from ats.services.execution.strategy_trader import StrategyTraderService
from ats.services.research.factory import ResearchFactoryService
from ats.services.risk.event_calendar import EventRiskService
from ats.services.risk.service import RiskService

PRICES = {"RELIANCE.NS": 2500.0, "TCS.NS": 4000.0, "NIFTYBEES.NS": 280.0}


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
    with db.session_scope() as s:
        s.add(Instrument(symbol="RELIANCE.NS", sector="Energy", instrument_type="EQ"))
        s.add(Instrument(symbol="TCS.NS", sector="IT", instrument_type="EQ"))
        s.add(Instrument(symbol="NIFTYBEES.NS", sector="Index ETF", instrument_type="ETF"))
    yield eng


class FakeMD:
    def watchlist(self):
        return list(PRICES)

    def latest_price(self, symbol):
        return PRICES.get(symbol)

    def get_history(self, symbol, limit=400):
        import pandas as pd

        return pd.DataFrame()

    def quote_age_s(self, symbol):
        return 1.0  # fresh quote — the staleness guard must let entries pass

    def feed_healthy(self):
        return True

    def data_status(self):
        return {"live": len(PRICES), "total": len(PRICES), "degraded": False}


class FakeRegime:
    def is_crisis(self):
        return False

    def current(self):
        return SimpleNamespace(label="up/normal")

    def tilt_for(self, style):
        return 1.0


class FakeScheduler:
    def add_job(self, *a, **k):
        return None


class MiniOrch:
    def __init__(self, services: dict) -> None:
        self._services = services
        self.scheduler = FakeScheduler()

    def get(self, name):
        return self._services.get(name)


class FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    def chat(self, system, messages, json_mode=False):
        return self.reply


async def _wire() -> tuple[InMemoryEventBus, dict]:
    """Start the real service graph on a real bus (no schedulers)."""
    bus = InMemoryEventBus()
    services: dict = {}
    orch = MiniOrch(services)
    ctx = SimpleNamespace(bus=bus, scheduler=FakeScheduler(), orchestrator=orch)

    services.update({
        "market_data": FakeMD(), "regime": FakeRegime(),
        "execution": ExecutionService(), "risk": RiskService(),
        "strategy_trader": StrategyTraderService(), "league": LeagueService(),
        "event_risk": EventRiskService(), "reconcile": ReconciliationService(),
    })
    for name in ("execution", "risk", "strategy_trader", "league",
                 "event_risk", "reconcile"):
        await services[name].start(ctx)
    await bus.start()
    return bus, services


async def _drain(bus: InMemoryEventBus) -> None:
    """Wait until the dispatch loop has gone quiet."""
    idle = 0
    for _ in range(500):
        await asyncio.sleep(0.01)
        idle = idle + 1 if bus._queue.empty() else 0
        if idle >= 5:
            return
    raise AssertionError("event bus never went idle")


def _sig(strategy: str, symbol: str, stance: str = "buy", conviction: float = 0.8) -> dict:
    return {"strategy": strategy, "symbol": symbol,
            "stance": stance, "conviction": conviction}


def _proposal(symbol: str, weight: float) -> dict:
    return {"symbol": symbol, "action": "BUY" if weight > 0 else "SELL",
            "target_weight": weight, "conviction": 0.9,
            "rationale": "test", "contributors": {}}


# --------------------------------------------------------------------------- #
def test_signal_to_fill_on_main_book_and_solo_account(memdb):
    async def scenario():
        bus, svc = await _wire()
        await bus.publish(Topic.SIGNAL, _sig("sma_crossover", "RELIANCE.NS"))
        await bus.publish(Topic.SIGNAL, _sig("donchian_trend", "RELIANCE.NS"))
        await _drain(bus)
        report = svc["reconcile"].run_sync()
        await bus.stop()
        return report

    report = asyncio.run(scenario())
    # The whole multi-account state must reconcile exactly.
    assert report["ok"], report["mismatches"]

    with db.session_scope() as s:
        orders = s.execute(select(Order)).scalars().all()
        fills = s.execute(select(Fill)).scalars().all()
        decisions = s.execute(select(Decision)).scalars().all()

    by_account: dict[str, list] = {}
    for o in orders:
        by_account.setdefault(o.account, []).append(o)
    fill_by_order = {f.order_id: f for f in fills}

    # Main book: the consensus proposal walked Risk → Execution → paper fill.
    assert "paper" in by_account
    main = by_account["paper"][0]
    assert main.status == "FILLED" and main.side == "BUY"
    assert main.decision_id is not None
    decision = next(d for d in decisions if d.id == main.decision_id)
    assert decision.status == "filled"  # approved → filled once executed
    assert decision.contributors.get("source") == "strategy_consensus"
    main_fill = fill_by_order[main.id]
    # Guardrail held: notional within the per-order cap at the reference
    # price (the fill itself pays up to 5 bps adverse slippage on top).
    assert main_fill.qty * PRICES["RELIANCE.NS"] <= 50_000.0
    assert main_fill.qty * main_fill.price <= 50_000.0 * 1.001

    # League: each voting strategy also traded its OWN ₹1L account.
    for sid in ("sma_crossover", "donchian_trend"):
        acct = solo_account(sid)
        assert acct in by_account, f"{acct} never traded"
        solo = by_account[acct][0]
        assert solo.status == "FILLED"
        f = fill_by_order[solo.id]
        # Sized to its own equity: ≤ 10% of ₹1L, not of the ₹10L main book.
        assert f.qty * f.price <= 10_000.0 + 1
        bal = AccountLedger(acct).balance()
        assert bal.cash == pytest.approx(100_000.0 - f.qty * f.price - f.fees, abs=0.05)
        assert bal.reserved == 0.0


def test_reconcile_halts_entries_until_human_release(memdb):
    async def scenario():
        bus, svc = await _wire()
        await bus.publish(Topic.SIGNAL, _sig("sma_crossover", "RELIANCE.NS"))
        await _drain(bus)
        assert svc["reconcile"].run_sync()["ok"]

        # Corrupt the solo book by one share — the drift reconcile exists to catch.
        acct = solo_account("sma_crossover")
        with db.session_scope() as s:
            pos = s.execute(select(Position).where(Position.account == acct)).scalar_one()
            pos.qty += 1
        report = svc["reconcile"].run_sync()
        assert not report["ok"] and entries_halted()

        # New entries are refused at the risk layer while halted…
        blocked = await svc["risk"].evaluate_proposal(_proposal("TCS.NS", 0.05))

        # …until the book is fixed and a HUMAN releases.
        with db.session_scope() as s:
            pos = s.execute(select(Position).where(Position.account == acct)).scalar_one()
            pos.qty -= 1
        assert svc["reconcile"].run_sync()["ok"]
        svc["reconcile"].release(actor="human")
        halted_after = entries_halted()
        approved = await svc["risk"].evaluate_proposal(_proposal("TCS.NS", 0.05))
        await bus.stop()
        return blocked, halted_after, approved

    blocked, halted_after, approved = asyncio.run(scenario())
    assert blocked == {"status": "blocked", "applied": ["recon_halt"]}
    assert halted_after is False
    assert approved["status"] == "approved"


def test_manual_veto_blocks_entries_but_exits_pass(memdb):
    async def scenario():
        bus, svc = await _wire()
        # Hold RELIANCE first (clean tape), then engage the global manual veto.
        await bus.publish(Topic.SIGNAL, _sig("sma_crossover", "RELIANCE.NS"))
        await _drain(bus)
        svc["event_risk"].set_manual_veto(None, engaged=True, reason="operator doubt")

        entry = await svc["risk"].evaluate_proposal(_proposal("TCS.NS", 0.05))
        # Exits always pass: flattening the held name sails through the veto.
        exit_ = await svc["risk"].evaluate_proposal(_proposal("RELIANCE.NS", 0.0))
        await bus.stop()
        return entry, exit_

    entry, exit_ = asyncio.run(scenario())
    assert entry["status"] == "vetoed"
    assert "veto:manual_global" in entry["applied"]
    assert exit_["status"] == "approved" and exit_["side"] == "SELL"


def test_committee_tilt_reaches_the_allocator(memdb):
    """Slow loop → medium loop: an approved tilt changes the sleeve weights."""
    reply = json.dumps({"summary": "trend regime", "rationale": "evidence",
                        "tilts": {"donchian_trend": 0.10, "mean_reversion": -0.10}})
    factory = ResearchFactoryService(llm=FakeLLM(reply), committee_llm=FakeLLM(reply))
    factory.run_role("committee", actor="human")
    with db.session_scope() as s:
        rec_id = s.execute(select(AllocationRecommendation)).scalars().one().id
    factory.approve_recommendation(rec_id, actor="human")

    from ats.services.strategies.service import StrategyService

    strat_svc = StrategyService()
    returns = {"donchian_trend": [0.001] * 30, "mean_reversion": [0.001] * 30}
    strat_svc._sleeves = SimpleNamespace(
        returns_by_sleeve=lambda: returns,
        rolling_sharpe=lambda sid: 1.0,
    )
    strat_svc._reallocate()
    w = strat_svc._alloc_weights
    # Identical sleeves would split 50/50; the approved tilt must separate them.
    assert w["donchian_trend"] > 0.5 > w["mean_reversion"]
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_production_wiring_registers_every_service():
    """The wiring is fault-isolated (a broken import is silently skipped), so
    the boot audit is this assertion: every expected service must register."""
    from ats.server.wiring import build_orchestrator

    orch = build_orchestrator()
    registered = {s.name for s in getattr(orch, "services", [])}
    expected = {
        "market_data", "regime", "fundamentals", "options_data", "scraper",
        "nlp", "strategies", "knowledge", "agents", "flows", "event_risk",
        "risk", "execution", "strategy_trader", "league", "reconcile",
        "vol_premium", "email", "telegram", "watchdog", "learning",
        "metrics", "rules", "research", "dashboard",
    }
    missing = expected - registered
    assert not missing, f"services failed to register: {sorted(missing)}"
