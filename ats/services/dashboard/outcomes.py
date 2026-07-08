"""Closed-trade outcomes (plan §9.4): was the exit any good?

Round trips are rebuilt FIFO from filled orders per (account, symbol) and
annotated with the fields a trade review actually needs:

- holding period + realized P&L **after fees** (buy fees prorated per share,
  sell fees on the closing leg);
- max favorable / adverse excursion over the holding window (daily bars);
- what NIFTYBEES did over the same window — a trade that made 2% while the
  index made 3% is a loss in disguise, and gets shown as one.

Everything is computed on demand from ``fills``/``orders``/``ohlcv`` — no
new tables, no state to drift.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.models import Fill, Ohlcv, Order

BENCHMARK_SYMBOL = "NIFTYBEES.NS"


def closed_trades(account: str | None = None, limit: int = 50) -> list[dict]:
    """The most recent ``limit`` closed round trips, newest exit first."""
    with session_scope() as s:
        rows = s.execute(
            select(Fill, Order).join(Order, Fill.order_id == Order.id)
            .where(Order.status == "FILLED")
            .order_by(Fill.id.asc())
        ).all()

        lots: dict[tuple[str, str], deque] = {}
        trades: list[dict] = []
        for fill, order in rows:
            if account and order.account != account:
                continue
            key = (order.account, order.symbol)
            if order.side == "BUY":
                fee_ps = (fill.fees / fill.qty) if fill.qty else 0.0
                lots.setdefault(key, deque()).append(
                    [fill.qty, fill.price, fill.ts, fee_ps]
                )
                continue
            # SELL: consume lots FIFO into one closed trade per sell fill.
            open_lots = lots.get(key)
            if not open_lots:
                continue  # sell without a tracked entry (pre-history) — skip
            remaining = fill.qty
            qty_closed = 0
            cost = entry_fees = 0.0
            first_entry_ts = open_lots[0][2]
            while remaining > 0 and open_lots:
                lot = open_lots[0]
                take = min(remaining, lot[0])
                cost += take * lot[1]
                entry_fees += take * lot[3]
                qty_closed += take
                lot[0] -= take
                remaining -= take
                if lot[0] == 0:
                    open_lots.popleft()
            if qty_closed <= 0:
                continue
            entry_px = cost / qty_closed
            gross = (fill.price - entry_px) * qty_closed
            fees = entry_fees + fill.fees
            trades.append({
                "account": order.account, "symbol": order.symbol,
                "qty": qty_closed,
                "entry_ts": first_entry_ts, "exit_ts": fill.ts,
                "entry_price": round(entry_px, 2),
                "exit_price": round(fill.price, 2),
                "gross_pnl": round(gross, 2),
                "fees": round(fees, 2),
                "net_pnl": round(gross - fees, 2),
                "return_pct": round((fill.price / entry_px - 1.0) * 100, 2)
                if entry_px else None,
                "holding_days": max(0, (fill.ts - first_entry_ts).days)
                if fill.ts and first_entry_ts else None,
            })

        trades = sorted(trades, key=lambda t: t["exit_ts"] or datetime.min,
                        reverse=True)[:limit]
        for t in trades:
            _annotate(s, t)
            t["entry_ts"] = t["entry_ts"].isoformat() if t["entry_ts"] else None
            t["exit_ts"] = t["exit_ts"].isoformat() if t["exit_ts"] else None
        return trades


def _annotate(s, trade: dict) -> None:
    """Attach MFE/MAE and the benchmark-relative return over the window."""
    entry, exit_ = trade["entry_ts"], trade["exit_ts"]
    if not entry or not exit_:
        return
    lo = entry - timedelta(days=1)
    hi = exit_ + timedelta(days=1)

    bars = s.execute(
        select(Ohlcv).where(
            Ohlcv.symbol == trade["symbol"], Ohlcv.interval == "1d",
            Ohlcv.ts >= lo, Ohlcv.ts <= hi,
        ).order_by(Ohlcv.ts)
    ).scalars().all()
    if bars and trade["entry_price"]:
        e = trade["entry_price"]
        trade["mfe_pct"] = round((max(b.high for b in bars) / e - 1.0) * 100, 2)
        trade["mae_pct"] = round((min(b.low for b in bars) / e - 1.0) * 100, 2)

    bench = s.execute(
        select(Ohlcv).where(
            Ohlcv.symbol == BENCHMARK_SYMBOL, Ohlcv.interval == "1d",
            Ohlcv.ts >= lo, Ohlcv.ts <= hi,
        ).order_by(Ohlcv.ts)
    ).scalars().all()
    if len(bench) >= 2 and bench[0].close:
        bench_ret = (bench[-1].close / bench[0].close - 1.0) * 100
        trade["benchmark_return_pct"] = round(bench_ret, 2)
        if trade.get("return_pct") is not None:
            trade["alpha_pct"] = round(trade["return_pct"] - bench_ret, 2)
