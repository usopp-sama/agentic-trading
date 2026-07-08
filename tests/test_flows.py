"""Flow anomalies (WS-5): pump signature, NSE parsers, veto modes.

Engineered bar paths make the signature unambiguous; the service tests use
a fake market-data source and canned NSE CSVs, so everything runs offline.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core import state
from ats.core.config import get_settings
from ats.core.models import Base, FlowDaily
from ats.services.flows import collectors
from ats.services.flows.service import FLOW_VETO_KEY, FlowsService
from ats.services.flows.signature import pump_signature
from ats.services.risk.event_calendar import EventRiskService


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


def _frame(close, volume) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2026-05-01", periods=len(close), name="date")
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99,
         "close": close, "volume": np.asarray(volume, dtype=float)},
        index=idx,
    )


def _pump_frame(n: int = 40) -> pd.DataFrame:
    """Quiet base, then 5 sessions of +3%/day on 6x volume."""
    close = np.concatenate([np.full(n - 5, 100.0),
                            100.0 * (1.03 ** np.arange(1, 6))])
    volume = np.concatenate([np.full(n - 5, 1_000_000.0),
                             np.full(5, 6_000_000.0)])
    return _frame(close, volume)


def _quiet_frame(n: int = 40) -> pd.DataFrame:
    return _frame(100.0 + 0.1 * np.arange(n), np.full(n, 1_000_000.0))


def _delivery(values) -> pd.Series:
    idx = [date(2026, 5, 1) + timedelta(days=i) for i in range(len(values))]
    return pd.Series(list(values), index=idx, dtype=float)


# --- signature ---------------------------------------------------------------------
def test_pump_with_falling_delivery_confirms():
    dlv = _delivery([60.0] * 35 + [30.0] * 5)  # churn: delivery halves on the surge
    sig = pump_signature("X.NS", _pump_frame(), dlv)
    assert sig.triggered and sig.score == 1.0
    assert any("delivery falling" in r for r in sig.reasons)


def test_pump_without_delivery_data_is_unconfirmed():
    sig = pump_signature("X.NS", _pump_frame(), None)
    assert sig.triggered and sig.score == 0.7
    assert "delivery_unconfirmed" in sig.reasons


def test_surge_with_rising_delivery_is_accumulation_not_pump():
    dlv = _delivery([55.0] * 35 + [70.0] * 5)  # delivery RISES on the surge
    sig = pump_signature("X.NS", _pump_frame(), dlv)
    assert not sig.triggered and sig.score == 0.0
    assert any("delivery holding" in r for r in sig.reasons)


def test_quiet_tape_is_clean():
    sig = pump_signature("X.NS", _quiet_frame(), None)
    assert not sig.triggered and sig.score == 0.0


def test_price_surge_on_normal_volume_is_clean():
    close = np.concatenate([np.full(35, 100.0), 100.0 * (1.03 ** np.arange(1, 6))])
    sig = pump_signature("X.NS", _frame(close, np.full(40, 1_000_000.0)), None)
    assert not sig.triggered


def test_short_history_refuses_to_guess():
    sig = pump_signature("X.NS", _quiet_frame(10), None)
    assert not sig.triggered and sig.reasons == ["insufficient_history"]


# --- NSE parsers ---------------------------------------------------------------------
_BHAV_CSV = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
RELIANCE, EQ, 07-Jul-2026, 2500, 2510, 2550, 2490, 2540, 2545, 2530, 1000000, 25300, 50000, 620000, 62.00
TCS, EQ, 07-Jul-2026, 4000, 4010, 4090, 3990, 4080, 4085, 4050, 500000, 20250, 30000, 200000, 40.00
JUNK, BE, 07-Jul-2026, 10, 10, 11, 9, 10, 10, 10, 100, 1, 10, 50, 50.00
NODATA, EQ, 07-Jul-2026, 10, 10, 11, 9, 10, 10, 10, 100, 1, 10, -, -
"""

_BULK_CSV = """Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks
07-Jul-2026,RELIANCE,Reliance Industries,BIG FUND LLP,BUY,"2,000,000",2540.00,-
07-Jul-2026,TCS,Tata Consultancy,OTHER FUND,SELL,"1,000,000",4080.00,-
"""


def test_parse_bhavdata_eq_only_with_symbol_mapping():
    rows = collectors.parse_bhavdata(_BHAV_CSV)
    assert {r["symbol"] for r in rows} == {"RELIANCE.NS", "TCS.NS"}
    rel = next(r for r in rows if r["symbol"] == "RELIANCE.NS")
    assert rel["delivery_pct"] == 62.0


def test_parse_bulk_deals():
    rows = collectors.parse_bulk_deals(_BULK_CSV)
    assert len(rows) == 2
    assert rows[0] == {"symbol": "RELIANCE.NS", "day": date(2026, 7, 7),
                       "side": "BUY", "qty": 2_000_000.0}
    assert rows[1]["side"] == "SELL"


# --- service ---------------------------------------------------------------------------
class FakeMD:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self._frames = frames

    def watchlist(self) -> list[str]:
        return list(self._frames)

    def get_history(self, symbol: str, limit: int = 60) -> pd.DataFrame:
        return self._frames.get(symbol, pd.DataFrame()).tail(limit)


def _service(frames: dict[str, pd.DataFrame]) -> FlowsService:
    svc = FlowsService()
    svc._md = FakeMD(frames)
    return svc


def test_collect_stores_watchlist_rows_only(memdb, monkeypatch):
    day = date(2026, 7, 7)
    monkeypatch.setattr(collectors, "fetch_delivery", lambda d: [
        {"symbol": "RELIANCE.NS", "delivery_pct": 62.0},
        {"symbol": "NOTWATCHED.NS", "delivery_pct": 10.0},
    ])
    monkeypatch.setattr(collectors, "fetch_bulk_deals", lambda: [
        {"symbol": "RELIANCE.NS", "day": day, "side": "BUY", "qty": 1000.0},
    ])
    svc = _service({"RELIANCE.NS": _quiet_frame()})
    out = svc.collect(day)
    assert out == {"collected": 1, "deals": 1}
    with db.session_scope() as s:
        rows = s.execute(select(FlowDaily)).scalars().all()
        assert len(rows) == 1
        assert rows[0].symbol == "RELIANCE.NS"
        assert rows[0].delivery_pct == 62.0
        assert rows[0].bulk_buy_qty == 1000.0 and rows[0].deals == 1


def test_shadow_mode_records_but_never_blocks(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "flows_veto_mode", "shadow")
    svc = _service({"PUMP.NS": _pump_frame(), "QUIET.NS": _quiet_frame()})
    out = svc.recompute_vetoes()
    assert out == {"vetoed": 1, "mode": "shadow"}
    kv = state.get_kv(FLOW_VETO_KEY)
    assert "PUMP.NS" in kv and kv["PUMP.NS"]["shadow"] is True
    # EventRisk must NOT enforce a shadow veto.
    assert "flow_anomaly" not in EventRiskService().active_vetoes("PUMP.NS")


def test_active_mode_blocks_entries(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "flows_veto_mode", "active")
    svc = _service({"PUMP.NS": _pump_frame()})
    svc.recompute_vetoes()
    vetoes = EventRiskService().active_vetoes("PUMP.NS")
    assert "flow_anomaly" in vetoes
    assert "flow_anomaly" not in EventRiskService().active_vetoes("CLEAN.NS")


def test_off_mode_clears_vetoes(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "flows_veto_mode", "active")
    svc = _service({"PUMP.NS": _pump_frame()})
    svc.recompute_vetoes()
    assert state.get_kv(FLOW_VETO_KEY)
    monkeypatch.setattr(get_settings(), "flows_veto_mode", "off")
    assert svc.recompute_vetoes() == {"vetoed": 0, "mode": "off"}
    assert state.get_kv(FLOW_VETO_KEY) == {}


def test_delivery_series_feeds_signature_end_to_end(memdb, monkeypatch):
    """Stored delivery rows must reach the signature: rising delivery clears
    the same tape that would otherwise be vetoed unconfirmed."""
    monkeypatch.setattr(get_settings(), "flows_veto_mode", "active")
    svc = _service({"PUMP.NS": _pump_frame()})
    today = date.today()
    for i in range(25):
        svc._upsert("PUMP.NS", today - timedelta(days=30 - i), delivery_pct=55.0)
    for i in range(5):
        svc._upsert("PUMP.NS", today - timedelta(days=4 - i), delivery_pct=75.0)
    out = svc.recompute_vetoes()
    assert out["vetoed"] == 0  # delivery-backed surge = accumulation, no veto
