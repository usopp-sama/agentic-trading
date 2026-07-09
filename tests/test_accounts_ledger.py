"""AccountLedger invariants: the simulated bank account must never lie.

Uses an isolated in-memory SQLite (StaticPool) — same pattern as the other
DB-backed tests; never touches the dev database.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import Base, KvState, LedgerEntry
from ats.services.accounts import AccountLedger, InsufficientFunds, LedgerError
from ats.services.accounts.ledger import FEE_BUFFER_PCT


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
def acct(memdb) -> AccountLedger:
    ledger = AccountLedger("solo_test")
    ledger.deposit(100_000.0, note="initial funding")
    return ledger


# --- funding -----------------------------------------------------------------
def test_deposit_sets_balance_and_journals(acct):
    bal = acct.balance()
    assert bal.cash == 100_000.0
    assert bal.reserved == 0.0
    assert bal.available == 100_000.0
    stmt = acct.statement()
    assert len(stmt) == 1
    assert stmt[0]["kind"] == "DEPOSIT"
    assert stmt[0]["cash_after"] == 100_000.0


def test_withdraw_respects_available(acct):
    acct.withdraw(40_000.0)
    assert acct.balance().cash == 60_000.0
    with pytest.raises(InsufficientFunds):
        acct.withdraw(60_000.01)


def test_negative_and_zero_amounts_rejected(acct):
    with pytest.raises(LedgerError):
        acct.deposit(0)
    with pytest.raises(LedgerError):
        acct.deposit(-5)
    with pytest.raises(LedgerError):
        acct.withdraw(-1)


# --- reserve / release ---------------------------------------------------------
def test_reserve_holds_cash_with_fee_buffer(acct):
    acct.reserve("ord-1", 10_000.0)
    bal = acct.balance()
    expected_hold = round(10_000.0 * (1 + FEE_BUFFER_PCT), 2)
    assert bal.cash == 100_000.0            # cash unchanged by a hold
    assert bal.reserved == expected_hold
    assert bal.available == round(100_000.0 - expected_hold, 2)


def test_reserve_beyond_available_fails(acct):
    acct.reserve("ord-1", 60_000.0)
    with pytest.raises(InsufficientFunds):
        acct.reserve("ord-2", 45_000.0)     # 60k+ buffer already held


def test_reserve_is_idempotent_per_ref(acct):
    acct.reserve("ord-1", 10_000.0)
    acct.reserve("ord-1", 12_000.0)         # replaces, not stacks
    expected = round(12_000.0 * (1 + FEE_BUFFER_PCT), 2)
    assert acct.balance().reserved == expected


def test_release_frees_hold_and_is_noop_without_one(acct):
    acct.reserve("ord-1", 10_000.0)
    acct.release("ord-1")
    bal = acct.balance()
    assert bal.reserved == 0.0
    assert bal.available == 100_000.0
    # releasing again must not corrupt anything
    acct.release("ord-1")
    assert acct.balance().available == 100_000.0


# --- settle -----------------------------------------------------------------
def test_buy_settle_debits_cash_and_clears_hold(acct):
    acct.reserve("ord-1", 10_000.0)
    acct.settle("ord-1", "BUY", gross_value=10_005.0, fees=25.0)
    bal = acct.balance()
    assert bal.reserved == 0.0
    assert bal.cash == round(100_000.0 - 10_005.0 - 25.0, 2)


def test_sell_settle_credits_cash_net_of_fees(acct):
    acct.settle("ord-2", "SELL", gross_value=5_000.0, fees=12.5)
    assert acct.balance().cash == round(100_000.0 + 5_000.0 - 12.5, 2)


def test_buy_settle_cannot_overdraw(acct):
    acct.withdraw(95_000.0)
    with pytest.raises(InsufficientFunds):
        acct.settle("ord-3", "BUY", gross_value=6_000.0, fees=10.0)
    # failed settle must not have moved anything
    assert acct.balance().cash == 5_000.0


def test_settle_validates_side_and_fees(acct):
    with pytest.raises(LedgerError):
        acct.settle("x", "HOLD", 100.0, 1.0)
    with pytest.raises(LedgerError):
        acct.settle("x", "BUY", 100.0, -1.0)


# --- journal integrity ---------------------------------------------------------
def test_journal_running_balance_reconciles(acct):
    acct.reserve("ord-1", 20_000.0)
    acct.settle("ord-1", "BUY", 20_010.0, 45.0)
    acct.settle("ord-9", "SELL", 8_000.0, 18.0)
    acct.withdraw(1_000.0)

    entries = list(reversed(acct.statement()))  # oldest first
    cash = 0.0
    for e in entries:
        cash = round(cash + e["amount"], 2)
        assert cash == e["cash_after"], f"journal drift at {e}"
    assert cash == acct.balance().cash


def test_accounts_are_segregated(memdb):
    a = AccountLedger("solo_a")
    b = AccountLedger("solo_b")
    a.deposit(50_000.0)
    b.deposit(75_000.0)
    a.reserve("o1", 10_000.0)
    assert a.balance().cash == 50_000.0
    assert b.balance().reserved == 0.0
    assert b.balance().cash == 75_000.0


def test_legacy_cash_key_stays_in_sync(memdb):
    ledger = AccountLedger("main")
    ledger.deposit(100_000.0)
    ledger.settle("o1", "BUY", 10_000.0, 20.0)
    with db.session_scope() as s:
        row = s.get(KvState, "cash:main")
        assert row is not None
        assert row.value["cash"] == ledger.balance().cash


def test_journal_is_append_only_rowcount(memdb):
    ledger = AccountLedger("solo_j")
    ledger.deposit(10_000.0)
    ledger.reserve("o1", 1_000.0)
    ledger.release("o1")
    with db.session_scope() as s:
        n = len(s.execute(select(LedgerEntry).where(
            LedgerEntry.account == "solo_j")).scalars().all())
    assert n == 3  # DEPOSIT + RESERVE + RELEASE, nothing rewritten
