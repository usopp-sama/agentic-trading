"""The paper-book reset must truly clean the book: every trade/holding/ledger
row gone, every account's cash back to starting capital, across all accounts —
while leaving reference data alone."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import (
    Base,
    DematHolding,
    Fill,
    Instrument,
    LedgerEntry,
    Order,
    Position,
)
from ats.services.accounts import AccountLedger


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


def _seed_book(capital: float) -> None:
    # Two accounts with cash movements + holds (main + a league solo).
    AccountLedger("paper").deposit(capital)
    AccountLedger("paper").reserve("ord-1", 5_000.0)
    AccountLedger("solo_alpha").deposit(capital)
    with db.session_scope() as s:
        s.add(Instrument(symbol="RELIANCE.NS", name="Reliance", active=True))  # reference — must survive
        order = Order(account="paper", symbol="RELIANCE.NS", side="BUY", qty=1, status="FILLED")
        s.add(order)
        s.flush()
        s.add(Fill(order_id=order.id, qty=1, price=100.0))
        s.add(Position(account="paper", symbol="RELIANCE.NS", qty=1, avg_price=100.0))
        s.add(DematHolding(account_id="paper", symbol="RELIANCE.NS", qty_settled=1))


def test_reset_wipes_book_and_resets_all_accounts(memdb):
    from scripts.reset_paper_book import reset

    capital = 1_000_000.0
    _seed_book(capital)

    # Precondition: the book is dirty.
    with db.session_scope() as s:
        assert s.execute(select(Fill)).scalars().all()
        assert s.execute(select(LedgerEntry)).scalars().all()
    assert AccountLedger("paper").balance().reserved > 0   # a hold is outstanding

    result = reset()

    # Every trade/holding/ledger row is gone.
    with db.session_scope() as s:
        for model in (Fill, Order, Position, DematHolding, LedgerEntry):
            assert s.execute(select(model)).scalars().all() == [], model.__tablename__
        # Reference data survives.
        assert s.execute(select(Instrument)).scalars().all(), "instruments must survive"

    # Both accounts are back to clean starting capital with no holds.
    for acc in ("paper", "solo_alpha"):
        bal = AccountLedger(acc).balance()
        assert bal.cash == capital and bal.reserved == 0.0, acc
    assert set(result["accounts"]) >= {"paper", "solo_alpha"}


def test_reset_refuses_with_real_money_enabled(memdb, monkeypatch):
    from ats.core.config import get_settings
    from scripts import reset_paper_book

    settings = get_settings()
    monkeypatch.setattr(settings, "real_money_enabled", True, raising=False)
    monkeypatch.setattr(reset_paper_book, "get_settings", lambda: settings)
    with pytest.raises(SystemExit):
        reset_paper_book.reset()
