"""BrokerSim invariants: orders, money, and positions must always agree.

Isolated in-memory SQLite; no network, no real broker, same fixture pattern
as the rest of the suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import Base, Fill, Order
from ats.services.accounts import AccountLedger
from ats.services.execution.broker_sim import (
    BrokerSim,
    TERMINAL_STATES,
    can_transition,
)

ACCT = "solo_donch"
START = 100_000.0


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
    prices = {"RELIANCE": 2500.0, "TCS": 4000.0}
    sim = BrokerSim(price_fn=prices.get)
    AccountLedger(ACCT).deposit(START, note="funding")
    return sim


# --- state machine ------------------------------------------------------------
def test_lifecycle_transitions():
    assert can_transition("STAGED", "SUBMITTED")
    assert can_transition("SUBMITTED", "ACKED")
    assert can_transition("ACKED", "FILLED")
    assert can_transition("STAGED", "REJECTED")
    assert can_transition("ACKED", "CANCELLED")
    # illegal jumps
    assert not can_transition("STAGED", "FILLED")
    assert not can_transition("FILLED", "CANCELLED")
    for t in TERMINAL_STATES:
        assert not any(can_transition(t, s) for s in
                       ("STAGED", "SUBMITTED", "ACKED", "FILLED", "CANCELLED"))


# --- happy path -----------------------------------------------------------------
def test_buy_fills_and_money_reconciles(broker):
    res = broker.place_order(ACCT, "RELIANCE", "BUY", 10)
    assert res["status"] == "FILLED"
    assert res["fill_price"] > 2500.0  # adverse slippage on a buy

    bal = broker.margins(ACCT)
    expected_cash = round(START - 10 * res["fill_price"] - res["fees"], 2)
    assert bal["cash"] == expected_cash
    assert bal["reserved"] == 0.0  # hold fully released on settle

    pos = broker.positions(ACCT)
    assert len(pos) == 1
    assert pos[0]["symbol"] == "RELIANCE"
    assert pos[0]["qty"] == 10


def test_round_trip_conserves_money_minus_frictions(broker):
    buy = broker.place_order(ACCT, "TCS", "BUY", 5)
    sell = broker.place_order(ACCT, "TCS", "SELL", 5)
    assert sell["status"] == "FILLED"
    assert sell["fill_price"] < 4000.0  # adverse slippage on a sell

    bal = broker.margins(ACCT)
    frictions = (
        buy["fees"] + sell["fees"]
        + 5 * (buy["fill_price"] - sell["fill_price"])
    )
    assert bal["cash"] == pytest.approx(START - frictions, abs=0.05)
    assert broker.positions(ACCT) == []  # flat


def test_order_status_reflects_final_state(broker):
    res = broker.place_order(ACCT, "RELIANCE", "BUY", 2)
    st = broker.order_status(res["order_id"])
    assert st["status"] == "FILLED"
    assert st["account"] == ACCT
    assert st["qty"] == 2


# --- rejection paths -------------------------------------------------------------
def test_unknown_symbol_rejects_and_releases(broker):
    res = broker.place_order(ACCT, "NOSUCH", "BUY", 10)
    assert res["status"] == "REJECTED"
    bal = broker.margins(ACCT)
    assert bal["cash"] == START
    assert bal["reserved"] == 0.0


def test_insufficient_funds_rejects_cleanly(broker):
    res = broker.place_order(ACCT, "TCS", "BUY", 100)  # ~4L > 1L
    assert res["status"] == "REJECTED"
    assert "reserve" in res["reason"] or "available" in res["reason"]
    bal = broker.margins(ACCT)
    assert bal["cash"] == START
    assert bal["reserved"] == 0.0
    assert broker.positions(ACCT) == []


def test_oversell_rejected_long_only(broker):
    broker.place_order(ACCT, "RELIANCE", "BUY", 3)
    res = broker.place_order(ACCT, "RELIANCE", "SELL", 5)
    assert res["status"] == "REJECTED"
    assert "long-only" in res["reason"]
    assert broker.positions(ACCT)[0]["qty"] == 3  # untouched


def test_bad_qty_and_side_rejected(broker):
    assert broker.place_order(ACCT, "TCS", "BUY", 0)["status"] == "REJECTED"
    assert broker.place_order(ACCT, "TCS", "HOLD", 1)["status"] == "REJECTED"


def test_rejected_orders_leave_a_record(broker):
    broker.place_order(ACCT, "NOSUCH", "BUY", 10)
    with db.session_scope() as s:
        rows = s.execute(select(Order).where(Order.account == ACCT)).scalars().all()
    assert any(o.status == "REJECTED" for o in rows)


# --- cancel ---------------------------------------------------------------------
def test_cancel_unknown_and_filled_orders(broker):
    assert broker.cancel_order(999_999)["status"] == "ERROR"
    res = broker.place_order(ACCT, "RELIANCE", "BUY", 1)
    out = broker.cancel_order(res["order_id"])
    assert out["status"] == "FILLED"  # too late; not cancellable
    assert out["reason"] == "not cancellable"


# --- segregation -----------------------------------------------------------------
def test_two_accounts_never_mix(broker):
    other = "solo_rsi2"
    AccountLedger(other).deposit(50_000.0)
    broker.place_order(ACCT, "RELIANCE", "BUY", 4)
    broker.place_order(other, "TCS", "BUY", 2)

    assert broker.margins(ACCT)["cash"] < START
    assert broker.margins(other)["cash"] < 50_000.0
    assert {p["symbol"] for p in broker.positions(ACCT)} == {"RELIANCE"}
    assert {p["symbol"] for p in broker.positions(other)} == {"TCS"}


# --- ledger/journal agreement -----------------------------------------------------
def test_every_fill_has_a_settlement_entry(broker):
    res = broker.place_order(ACCT, "RELIANCE", "BUY", 2)
    stmt = AccountLedger(ACCT).statement()
    kinds = [e["kind"] for e in stmt]
    assert "RESERVE" in kinds
    assert "SETTLE_DEBIT" in kinds
    ref = f"order:{res['order_id']}"
    assert any(e["ref"] == ref and e["kind"] == "SETTLE_DEBIT" for e in stmt)
    with db.session_scope() as s:
        fills = s.execute(select(Fill)).scalars().all()
    assert len(fills) == 1


def test_paperbroker_compat_shim(broker):
    broker.account = ACCT
    res = broker.submit("RELIANCE", "BUY", 1)
    assert res["status"] == "FILLED"
    assert set(res) >= {"order_id", "fill_price", "fees", "cash", "realized_delta"}
