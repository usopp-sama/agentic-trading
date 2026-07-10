"""Portfolio accounting: cash, positions, realized/unrealized PnL, equity.

Cash is held per account in ``kv_state``; positions live in the ``positions``
table. v1 is long-only (sells are clamped to current holdings, no shorting) to
keep the safe foundation simple.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import KvState, Position

log = get_logger("ats.portfolio")

PriceFn = Callable[[str], "float | None"]


def _cash_key(account: str) -> str:
    return f"cash:{account}"


def get_cash(account: str = "paper") -> float:
    with session_scope() as s:
        row = s.get(KvState, _cash_key(account))
        if row is None:
            cash = get_settings().paper_starting_capital
            s.add(KvState(key=_cash_key(account), value={"cash": cash}))
            return cash
        return float(row.value.get("cash", 0.0))


def _set_cash(account: str, cash: float) -> None:
    with session_scope() as s:
        row = s.get(KvState, _cash_key(account))
        if row is None:
            s.add(KvState(key=_cash_key(account), value={"cash": cash}))
        else:
            row.value = {"cash": round(cash, 2)}


def apply_fill(
    account: str,
    symbol: str,
    side: str,
    qty: int,
    price: float,
    fees: float,
    update_cash: bool = True,
) -> dict:
    """Apply a fill to cash + position. Returns the realized PnL delta.

    ``update_cash=False`` applies only the position leg — used by callers that
    manage cash through the AccountLedger (BrokerSim), where settlement has
    already moved the money and updating it here would double-count.
    """
    side = side.upper()
    realized_delta = 0.0
    eff_sell = 0
    with session_scope() as s:
        pos = s.execute(
            select(Position).where(
                Position.account == account, Position.symbol == symbol
            )
        ).scalar_one_or_none()
        if pos is None:
            pos = Position(account=account, symbol=symbol, qty=0, avg_price=0.0)
            s.add(pos)

        if side == "BUY":
            new_qty = pos.qty + qty
            if new_qty > 0:
                pos.avg_price = (pos.qty * pos.avg_price + qty * price) / new_qty
            pos.qty = new_qty
        else:  # SELL - clamp to holdings (long-only)
            sell_qty = min(qty, pos.qty)
            eff_sell = sell_qty
            realized_delta = (price - pos.avg_price) * sell_qty
            pos.realized_pnl += realized_delta
            pos.qty -= sell_qty
            if pos.qty == 0:
                pos.avg_price = 0.0

    # Demat leg (P2): mirror the securities into the profile's depository account
    # — the same effective qty that moved the position (so the three reconcile).
    try:
        from ats.services.accounts import demat

        if side == "BUY":
            demat.record_buy(account, symbol, qty, price)
        elif eff_sell > 0:
            demat.record_sell(account, symbol, eff_sell)
    except Exception as exc:  # noqa: BLE001 — demat is a mirror; never break a fill
        log.warning("demat_post_failed",
                    extra={"account": account, "symbol": symbol, "error": str(exc)})

    if not update_cash:
        return {"realized_delta": round(realized_delta, 2), "cash": get_cash(account)}

    cash = get_cash(account)
    if side == "BUY":
        cash -= qty * price + fees
    else:
        sell_qty = qty  # cash from what we sold (already clamped in DB path)
        cash += sell_qty * price - fees
    _set_cash(account, cash)
    return {"realized_delta": round(realized_delta, 2), "cash": round(cash, 2)}


def get_positions(account: str = "paper") -> list[dict]:
    with session_scope() as s:
        rows = s.execute(
            select(Position).where(
                Position.account == account, Position.qty != 0
            )
        ).scalars().all()
        return [
            {
                "symbol": p.symbol,
                "qty": p.qty,
                "avg_price": round(p.avg_price, 2),
                "realized_pnl": round(p.realized_pnl, 2),
            }
            for p in rows
        ]


def snapshot(account: str, price_fn: PriceFn) -> dict:
    cash = get_cash(account)
    positions = get_positions(account)
    holdings_value = 0.0
    unrealized = 0.0
    for p in positions:
        px = price_fn(p["symbol"]) or p["avg_price"]
        mv = p["qty"] * px
        holdings_value += mv
        unrealized += (px - p["avg_price"]) * p["qty"]
        p["last_price"] = round(px, 2)
        p["market_value"] = round(mv, 2)
        p["unrealized_pnl"] = round((px - p["avg_price"]) * p["qty"], 2)
    equity = cash + holdings_value
    return {
        "account": account,
        "cash": round(cash, 2),
        "holdings_value": round(holdings_value, 2),
        "equity": round(equity, 2),
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(sum(p["realized_pnl"] for p in positions), 2),
        "positions": positions,
    }
