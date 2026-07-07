"""Reconciliation: any drift between book, ledger, and broker halts entries."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core import state
from ats.core.models import Base, KvState, LedgerEntry, Position
from ats.services.accounts import AccountLedger
from ats.services.execution.broker_sim import BrokerSim
from ats.services.execution.reconcile import (
    ReconciliationService,
    entries_halted,
    reconcile_account,
)

ACCT = "solo_test"
PRICES = {"RELIANCE.NS": 2500.0}


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


@pytest.fixture()
def broker(memdb):
    sim = BrokerSim(price_fn=PRICES.get)
    AccountLedger(ACCT).deposit(100_000.0)
    sim.place_order(ACCT, "RELIANCE.NS", "BUY", 4)
    sim.place_order(ACCT, "RELIANCE.NS", "SELL", 2)
    return sim


class _LeagueStub:
    def __init__(self, broker):
        self._broker = broker

    def accounts(self):
        return [ACCT]


class _OrchStub:
    def __init__(self, broker):
        self._league = _LeagueStub(broker)

    def get(self, name):
        return self._league if name == "league" else None


# --- clean books reconcile -------------------------------------------------------
def test_clean_account_reconciles(broker):
    res = reconcile_account(ACCT, ledger_backed=True, broker=broker)
    assert res["ok"], res["mismatches"]


# --- each drift class is caught -----------------------------------------------------
def test_position_drift_detected(broker):
    with db.session_scope() as s:
        pos = s.execute(select(Position).where(Position.account == ACCT)).scalar_one()
        pos.qty += 1  # phantom share
    res = reconcile_account(ACCT, ledger_backed=True, broker=broker)
    assert not res["ok"]
    assert any("fills replay" in m for m in res["mismatches"])


def test_journal_tamper_detected(broker):
    with db.session_scope() as s:
        entry = s.execute(
            select(LedgerEntry).where(LedgerEntry.account == ACCT)
            .order_by(LedgerEntry.id.desc())
        ).scalars().first()
        entry.cash_after += 500.0
    res = reconcile_account(ACCT, ledger_backed=True, broker=broker)
    assert not res["ok"]
    assert any("journal" in m or "live cash" in m for m in res["mismatches"])


def test_legacy_cash_drift_detected(broker):
    with db.session_scope() as s:
        row = s.get(KvState, f"cash:{ACCT}")
        row.value = {"cash": float(row.value["cash"]) + 123.0}
    res = reconcile_account(ACCT, ledger_backed=True, broker=broker)
    assert not res["ok"]
    assert any("legacy" in m for m in res["mismatches"])


# --- the halt ------------------------------------------------------------------------
def test_mismatch_halts_entries_until_human_release(broker):
    svc = ReconciliationService()
    svc._orch = _OrchStub(broker)

    report = svc.run_sync()
    assert report["ok"]
    assert not entries_halted()

    with db.session_scope() as s:
        pos = s.execute(select(Position).where(Position.account == ACCT)).scalar_one()
        pos.qty += 3
    report = svc.run_sync()
    assert not report["ok"]
    assert entries_halted()

    # engage-only-auto, release-only-human
    svc.release(actor="human")
    assert not entries_halted()
    assert state.get_kv("recon:last").get("ok") is False


def test_paper_account_checked_without_ledger(memdb):
    # The main combined book has no ledger journal; positions-vs-fills only.
    res = reconcile_account("paper", ledger_backed=False)
    assert res["ok"]
