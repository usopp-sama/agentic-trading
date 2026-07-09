"""Closed-trade outcomes: FIFO pairing, fee-true P&L, excursions, benchmark.

Fills are seeded directly (orders + fills tables); outcomes must rebuild the
round trips exactly — quantities conserved, buy fees prorated, MFE/MAE and
the NIFTYBEES-relative return read from seeded daily bars.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import ats.core.db as db
from ats.core.models import Base, Fill, Ohlcv, Order
from ats.services.dashboard.outcomes import closed_trades

T0 = datetime(2026, 6, 1, 10, 0)


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


def _fill(account: str, symbol: str, side: str, qty: int, price: float,
          fees: float, ts: datetime) -> None:
    with db.session_scope() as s:
        order = Order(account=account, broker="test", symbol=symbol,
                      side=side, qty=qty, status="FILLED")
        s.add(order)
        s.flush()
        s.add(Fill(order_id=order.id, qty=qty, price=price, fees=fees, ts=ts))


def _bars(symbol: str, start: datetime, closes: list[float],
          high_pad: float = 2.0, low_pad: float = 2.0) -> None:
    with db.session_scope() as s:
        for i, c in enumerate(closes):
            s.add(Ohlcv(symbol=symbol, ts=start + timedelta(days=i), interval="1d",
                        open=c, high=c + high_pad, low=c - low_pad, close=c))


def test_simple_round_trip_fee_true(memdb):
    _fill("paper", "X.NS", "BUY", 10, 100.0, 10.0, T0)
    _fill("paper", "X.NS", "SELL", 10, 110.0, 12.0, T0 + timedelta(days=5))
    trades = closed_trades()
    assert len(trades) == 1
    t = trades[0]
    assert (t["qty"], t["entry_price"], t["exit_price"]) == (10, 100.0, 110.0)
    assert t["gross_pnl"] == 100.0
    assert t["fees"] == 22.0          # all buy fees + sell fees
    assert t["net_pnl"] == 78.0
    assert t["holding_days"] == 5
    assert t["return_pct"] == 10.0


def test_fifo_across_two_lots_prorates_buy_fees(memdb):
    _fill("paper", "X.NS", "BUY", 5, 100.0, 5.0, T0)                       # ₹1/share
    _fill("paper", "X.NS", "BUY", 5, 120.0, 5.0, T0 + timedelta(days=1))   # ₹1/share
    _fill("paper", "X.NS", "SELL", 8, 130.0, 8.0, T0 + timedelta(days=3))
    trades = closed_trades()
    assert len(trades) == 1
    t = trades[0]
    assert t["qty"] == 8
    assert t["entry_price"] == pytest.approx(107.5)   # (5*100 + 3*120) / 8
    assert t["fees"] == pytest.approx(8.0 + 8.0)      # 8 shares' buy fees + sell fees
    assert t["gross_pnl"] == pytest.approx((130.0 - 107.5) * 8)
    # The remaining 2-share lot closes later as its own trade.
    _fill("paper", "X.NS", "SELL", 2, 90.0, 2.0, T0 + timedelta(days=4))
    trades = closed_trades()
    assert len(trades) == 2
    tail = next(tr for tr in trades if tr["qty"] == 2)
    assert tail["entry_price"] == 120.0
    assert tail["net_pnl"] == pytest.approx((90.0 - 120.0) * 2 - 4.0)


def test_partial_closes_and_account_isolation(memdb):
    _fill("solo_a", "X.NS", "BUY", 10, 100.0, 0.0, T0)
    _fill("solo_a", "X.NS", "SELL", 4, 105.0, 0.0, T0 + timedelta(days=1))
    _fill("solo_b", "X.NS", "BUY", 3, 100.0, 0.0, T0)
    trades_a = closed_trades(account="solo_a")
    assert len(trades_a) == 1 and trades_a[0]["qty"] == 4
    assert closed_trades(account="solo_b") == []       # still open, no round trip
    assert len(closed_trades()) == 1                    # all accounts


def test_sell_without_tracked_entry_is_skipped(memdb):
    _fill("paper", "X.NS", "SELL", 5, 100.0, 1.0, T0)
    assert closed_trades() == []


def test_mfe_mae_and_benchmark_relative(memdb):
    _fill("paper", "X.NS", "BUY", 10, 100.0, 0.0, T0)
    _fill("paper", "X.NS", "SELL", 10, 104.0, 0.0, T0 + timedelta(days=4))
    # Symbol path spikes to 112 high and dips to 93 low inside the window.
    _bars("X.NS", T0, [100, 110, 95, 102, 104], high_pad=2.0, low_pad=2.0)
    # Benchmark rises 100 → 108 over the same window: the trade underperformed.
    _bars("NIFTYBEES.NS", T0, [100, 102, 104, 106, 108], high_pad=0.0, low_pad=0.0)
    t = closed_trades()[0]
    assert t["mfe_pct"] == pytest.approx(12.0)   # high 112 vs entry 100
    assert t["mae_pct"] == pytest.approx(-7.0)   # low 93 vs entry 100
    assert t["benchmark_return_pct"] == pytest.approx(8.0)
    assert t["alpha_pct"] == pytest.approx(4.0 - 8.0)  # +4% trade, -4% vs index
