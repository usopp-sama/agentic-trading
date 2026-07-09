"""QA-5: financial-statements persistence + CSV import (no network)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ats.core import db
from ats.core.models import Base, FinancialStatements
from ats.services.fundamentals.import_csv import parse_statements_csv
from ats.services.fundamentals.statements import (
    StatementSnapshot,
    latest_statements,
    persist_statements,
)


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


def test_persist_and_read_roundtrip(memdb):
    snaps = [
        StatementSnapshot(symbol="INFY.NS", as_of=date(2023, 3, 31), revenue=1000,
                          net_income=200, total_assets=5000, source="csv"),
        StatementSnapshot(symbol="INFY.NS", as_of=date(2024, 3, 31), revenue=1200,
                          net_income=250, total_assets=5200, source="csv"),
    ]
    assert persist_statements(snaps) == 2
    rows = latest_statements("INFY.NS", n=4)
    assert [r["as_of"] for r in rows] == [date(2024, 3, 31), date(2023, 3, 31)]  # newest first
    assert rows[0]["revenue"] == 1200 and rows[0]["net_income"] == 250


def test_persist_is_idempotent_upsert(memdb):
    snap = StatementSnapshot(symbol="TCS.NS", as_of=date(2024, 3, 31), revenue=100)
    persist_statements([snap])
    snap.revenue = 999  # same (symbol, period, as_of) -> update in place
    persist_statements([snap])
    with db.session_scope() as s:
        rows = s.execute(select(FinancialStatements).where(
            FinancialStatements.symbol == "TCS.NS")).scalars().all()
        assert len(rows) == 1 and rows[0].revenue == 999


CSV = """symbol,period,as_of,revenue,ebit,net_income,total_assets,shares_outstanding,source
INFY.NS,annual,2024-03-31,1200,300,250,5200,4100,screener
INFY.NS,annual,2023-03-31,1000,,200,5000,,screener
BADROW,annual,,1,2,3,4,5,x
"""


def test_parse_statements_csv():
    snaps = parse_statements_csv(CSV)
    # BADROW (no as_of) is skipped
    assert len(snaps) == 2
    s0 = snaps[0]
    assert s0.symbol == "INFY.NS" and s0.as_of == date(2024, 3, 31)
    assert s0.revenue == 1200 and s0.net_income == 250 and s0.source == "screener"
    # blank cells become None (missing stays missing)
    s1 = snaps[1]
    assert s1.ebit is None and s1.shares_outstanding is None


def test_csv_import_then_persist(memdb):
    snaps = parse_statements_csv(CSV)
    assert persist_statements(snaps) == 2
    rows = latest_statements("INFY.NS")
    assert rows[0]["revenue"] == 1200
    assert rows[1]["ebit"] is None
