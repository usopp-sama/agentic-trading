"""League invariants: solo accounts trade only their own signals with their
own money; the benchmark buys once and holds; standings math is truthful.

Isolated in-memory SQLite, no network — same fixture pattern as the suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core import state
from ats.core.models import Base, PnlDaily
from ats.services.accounts import AccountLedger
from ats.services.accounts.league import (
    BENCHMARK_ACCOUNT,
    LeagueService,
    league_roster,
    solo_account,
)
from ats.services.execution.broker_sim import BrokerSim

PRICES = {"RELIANCE.NS": 2500.0, "TCS.NS": 4000.0, "NIFTYBEES.NS": 280.0}
CAPITAL = 100_000.0


class _StubMD:
    def latest_price(self, symbol):
        return PRICES.get(symbol)


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
def league(memdb):
    svc = LeagueService()
    svc._md = _StubMD()
    svc._broker = BrokerSim(price_fn=svc.price_of)
    svc._roster = {"donchian_trend": solo_account("donchian_trend"),
                   "rsi2_reversion": solo_account("rsi2_reversion")}
    svc._itypes = {"RELIANCE.NS": "EQ", "TCS.NS": "EQ",
                   "NIFTYBEES.NS": "ETF", "^NSEI": "INDEX", "GC=F": "COMMODITY"}
    from ats.core.config import get_settings

    svc._fund_accounts(get_settings())
    return svc


def _sig(strategy, symbol, stance, conviction=1.0):
    return {"strategy": strategy, "symbol": symbol,
            "stance": stance, "conviction": conviction}


# --- roster + funding ---------------------------------------------------------
def test_auto_roster_is_paper_strategies_without_vol_premium():
    roster = league_roster()
    assert "vol_premium" not in roster
    assert "donchian_trend" in roster
    assert all(a.startswith("solo_") and len(a) <= 24 for a in roster.values())


def test_funding_is_idempotent(league):
    from ats.core.config import get_settings

    league._fund_accounts(get_settings())  # second call must not re-fund
    for account in league.accounts():
        assert AccountLedger(account).balance().cash == CAPITAL


# --- solo trading ---------------------------------------------------------------
def test_bullish_signal_buys_within_position_cap(league):
    res = league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    assert res["status"] == "FILLED"
    acct = solo_account("donchian_trend")
    pos = league._broker.positions(acct)
    assert pos[0]["symbol"] == "RELIANCE.NS"
    # 10% cap of a 1L account = Rs 10k -> 4 shares at 2500
    assert pos[0]["qty"] * 2500.0 <= 0.10 * CAPITAL
    # the other solo account is untouched
    assert league._broker.positions(solo_account("rsi2_reversion")) == []


def test_non_roster_strategy_is_ignored(league):
    res = league.handle_signal(_sig("sma_crossover", "RELIANCE.NS", "buy"))
    assert res["status"] == "not_in_league"


def test_bearish_signal_exits_full_position(league):
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    res = league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "sell"))
    assert res["status"] == "FILLED"
    assert league._broker.positions(solo_account("donchian_trend")) == []


def test_bearish_signal_when_flat_is_noop(league):
    res = league.handle_signal(_sig("donchian_trend", "TCS.NS", "sell"))
    assert res["status"] == "no_action"


def test_repeat_bullish_signal_does_not_stack(league):
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    qty0 = league._broker.positions(solo_account("donchian_trend"))[0]["qty"]
    res = league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "strong_buy"))
    assert res["status"] == "no_action"
    assert league._broker.positions(solo_account("donchian_trend"))[0]["qty"] == qty0


def test_indices_and_commodities_never_trade(league):
    assert league.handle_signal(_sig("donchian_trend", "^NSEI", "buy"))["status"] == "not_tradeable"
    assert league.handle_signal(_sig("donchian_trend", "GC=F", "buy"))["status"] == "not_tradeable"


def test_kill_switch_blocks_league(league):
    state.engage_kill_switch(actor="test", reason="drill")
    res = league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    assert res["status"] == "killed"
    state.release_kill_switch(actor="test")


def test_daily_loss_blocks_entries_but_not_exits(league):
    from datetime import date

    acct = solo_account("donchian_trend")
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    # Fake a day-open equity far above current -> >3% daily loss.
    state.set_kv(f"league:day_open:{acct}",
                 {"day": date.today().isoformat(), "equity": CAPITAL * 2})
    res = league.handle_signal(_sig("donchian_trend", "TCS.NS", "buy"))
    assert res["status"] == "entry_blocked_daily_loss"
    # Exit on the held name still passes.
    res = league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "sell"))
    assert res["status"] == "FILLED"


# --- benchmark --------------------------------------------------------------------
def test_benchmark_buys_once_and_holds(league):
    from ats.core.config import get_settings

    res = league._seed_benchmark(get_settings())
    assert res["status"] == "FILLED"
    pos = league._broker.positions(BENCHMARK_ACCOUNT)
    assert pos[0]["symbol"] == "NIFTYBEES.NS"
    assert pos[0]["qty"] > 300  # ~all-in at 280
    assert state.get_kv("league:benchmark_seeded").get("done") is True


# --- accounting reads ----------------------------------------------------------------
def test_record_equity_writes_pnl_rows(league):
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    out = league.record_equity()
    assert set(out) == set(league.accounts())
    with db.session_scope() as s:
        rows = s.execute(select(PnlDaily)).scalars().all()
    by_acct = {r.account: r for r in rows}
    assert by_acct[solo_account("donchian_trend")].equity < CAPITAL  # fees drag
    assert by_acct[BENCHMARK_ACCOUNT].equity == CAPITAL  # untouched cash


def test_league_table_shape_and_math(league):
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    league.record_equity()
    table = league.league_table()
    accounts = {r["account"] for r in table["table"]}
    assert {"paper", BENCHMARK_ACCOUNT,
            solo_account("donchian_trend"), solo_account("rsi2_reversion")} <= accounts
    donch = next(r for r in table["table"]
                 if r["account"] == solo_account("donchian_trend"))
    assert donch["trades"] == 1
    assert donch["fees"] > 0
    assert donch["positions"] == 1
    assert donch["return_pct"] == pytest.approx(
        100.0 * (donch["equity"] / CAPITAL - 1.0), abs=0.01)


def test_equity_curves_normalize_to_100(league):
    league.record_equity()
    curves = league.equity_curves()
    for series in curves.values():
        assert series[0]["norm"] == 100.0


def test_account_detail_passbook_reconciles(league):
    league.handle_signal(_sig("donchian_trend", "RELIANCE.NS", "buy"))
    detail = league.account_detail(solo_account("donchian_trend"))
    kinds = [e["kind"] for e in detail["passbook"]]
    assert "DEPOSIT" in kinds and "RESERVE" in kinds and "SETTLE_DEBIT" in kinds
    # newest entry's cash_after equals the live balance
    assert detail["passbook"][0]["cash_after"] == detail["balance"]["cash"]
    assert detail["strategy"] == "donchian_trend"
    assert detail["orders"][0]["status"] == "FILLED"
