"""P2: simulated demat account — T+1 settlement, over-sell refusal, recon."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import Base, Position
from ats.services.accounts import demat
from ats.services.execution.portfolio import apply_fill, get_positions


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


def test_buy_is_pending_then_settles_t1(memdb):
    demat.record_buy("main", "INFY", 10, 100.0)
    h = demat.holdings("main")[0]
    assert h["qty_pending"] == 10 and h["qty_settled"] == 0 and h["avg_cost"] == 100.0
    assert demat.settle_pending() == 10
    h = demat.holdings("main")[0]
    assert h["qty_settled"] == 10 and h["qty_pending"] == 0


def test_over_sell_is_refused(memdb):
    demat.record_buy("main", "INFY", 5, 100.0)
    with pytest.raises(demat.DematError):
        demat.record_sell("main", "INFY", 6)


def test_sell_debits_settled_before_pending(memdb):
    demat.record_buy("main", "INFY", 10, 100.0)
    demat.settle_pending()                       # 10 settled
    demat.record_buy("main", "INFY", 5, 110.0)   # +5 pending
    demat.record_sell("main", "INFY", 12)        # 10 settled + 2 pending
    h = demat.holdings("main")[0]
    assert h["qty_settled"] == 0 and h["qty_pending"] == 3


def test_bo_id_is_16_digit_and_stable(memdb):
    a = demat.get_or_create_account("solo_x")
    assert len(a["bo_id"]) == 16 and a["bo_id"].isdigit()
    assert demat.get_or_create_account("solo_x")["bo_id"] == a["bo_id"]


def test_apply_fill_posts_to_demat_and_reconciles(memdb):
    # every fill (main or league solo) mirrors into a demat account
    apply_fill("league_solo_1", "INFY", "BUY", 10, 100.0, 5.0)
    assert get_positions("league_solo_1")[0]["qty"] == 10
    assert demat.holdings("league_solo_1")[0]["qty_total"] == 10
    assert demat.check_positions_vs_demat("league_solo_1") == []   # reconciled

    # selling reduces both in lockstep
    apply_fill("league_solo_1", "INFY", "SELL", 4, 105.0, 3.0)
    assert get_positions("league_solo_1")[0]["qty"] == 6
    assert demat.holdings("league_solo_1")[0]["qty_total"] == 6
    assert demat.check_positions_vs_demat("league_solo_1") == []


def test_recon_flags_demat_drift(memdb):
    # a position with no matching demat holding must be caught
    with db.session_scope() as s:
        s.add(Position(account="main", symbol="TCS", qty=7, avg_price=100.0))
    mm = demat.check_positions_vs_demat("main")
    assert mm and "TCS" in mm[0] and "demat 0" in mm[0]
