"""Tests for the research metrics export and the learning attribution horizon.

Uses an isolated in-memory SQLite (StaticPool so every session shares one
connection) so it never touches the dev database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import Attribution, Base, SmeTrackRecord, Strategy as StrategyRow
from ats.services.learning.service import LearningService
from ats.services.metrics.service import MetricsService


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


class _StubMarketData:
    def __init__(self, price: float) -> None:
        self._price = price

    def latest_price(self, symbol: str):
        return self._price


def _add_attribution(ts: datetime, entry: float = 100.0) -> None:
    with db.session_scope() as s:
        s.add(Attribution(
            ts=ts, decision_id=None, symbol="X.NS", side="BUY",
            entry_price=entry, contributors={"sme_a": {"contribution": 0.5, "conviction": 0.8}},
            evaluated=False,
        ))


# --- learning attribution horizon -------------------------------------------
def test_attribution_waits_for_horizon(memdb):
    svc = LearningService()
    svc._md = _StubMarketData(price=110.0)
    svc._horizon_days = 5
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _add_attribution(now - timedelta(days=6))   # past horizon -> evaluate
    _add_attribution(now - timedelta(days=1))   # in-flight -> skip
    result = svc.evaluate(force=False)
    assert result["evaluated"] == 1
    with db.session_scope() as s:
        rows = s.execute(select(Attribution)).scalars().all()
        evaluated = [r.evaluated for r in rows]
        assert sorted(evaluated) == [False, True]


def test_force_evaluates_all_regardless_of_horizon(memdb):
    svc = LearningService()
    svc._md = _StubMarketData(price=110.0)
    svc._horizon_days = 5
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _add_attribution(now - timedelta(hours=1))
    _add_attribution(now - timedelta(hours=2))
    result = svc.evaluate(force=True)
    assert result["evaluated"] == 2


def test_horizon_zero_scores_on_next_tick(memdb):
    svc = LearningService()
    svc._md = _StubMarketData(price=90.0)  # negative forward return
    svc._horizon_days = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _add_attribution(now)
    assert svc.evaluate(force=False)["evaluated"] == 1
    # Contributor's positive call was wrong (price fell) -> recorded as a loss.
    with db.session_scope() as s:
        tr = s.get(SmeTrackRecord, "sme_a")
        assert tr is not None and tr.n == 1 and tr.wins == 0


# --- metrics export ----------------------------------------------------------
def test_metrics_export_writes_parquet_and_log(memdb, tmp_path):
    with db.session_scope() as s:
        s.add(StrategyRow(id="xs_momentum", name="XS Mom", type="momentum",
                          status="shadow", weight=1.0, allocation_pct=0.0))
        s.add(SmeTrackRecord(sme="sme_a", n=10, wins=6, hit_rate=0.6, brier=0.2,
                             pnl_contrib=0.05, vote_weight=1.1, promoted_weight=0.0,
                             status="shadow"))
    svc = MetricsService()
    svc._dir = tmp_path
    out = svc.export_daily()
    assert out["files"]
    strat_files = list(tmp_path.glob("strategies_*.parquet"))
    sme_files = list(tmp_path.glob("smes_*.parquet"))
    assert strat_files and sme_files
    df = pd.read_parquet(strat_files[0])
    assert "xs_momentum" in set(df["strategy"])
    assert (tmp_path / "research_log.jsonl").exists()
    log_text = (tmp_path / "research_log.jsonl").read_text().strip()
    assert "params" in log_text and "xs_mom_formation" in log_text


def test_metrics_export_survives_empty_db(memdb, tmp_path):
    svc = MetricsService()
    svc._dir = tmp_path
    out = svc.export_daily()
    # No strategies/SMEs yet, but the research log line is still appended.
    assert (tmp_path / "research_log.jsonl").exists()
    assert isinstance(out["files"], list)
