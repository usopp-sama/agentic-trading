"""Simulated demat (depository) account — the securities leg (P2).

Completes the Indian trading simulation: bank ledger (cash) + broker (orders) +
**demat (settled securities)**. A BUY fill creates *pending* holdings that
settle T+1 (a daily settlement pass moves pending → settled); a SELL debits
settled first, then pending, and refuses to over-sell the total position.

Pure DB functions (no bus, no network). Posted to from ``portfolio.apply_fill``
— the single chokepoint both brokers share — so the main book and every league
solo account get a demat account automatically.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import DematAccount, DematHolding

log = get_logger("ats.demat")


class DematError(RuntimeError):
    """An impossible demat operation (e.g. over-selling)."""


def _bo_id(account_id: str) -> str:
    """A deterministic fake 16-digit beneficiary-owner id for the profile."""
    digest = hashlib.sha256(account_id.encode()).hexdigest()
    return f"{int(digest[:16], 16) % (10 ** 16):016d}"


def get_or_create_account(account_id: str, dp_name: str = "ATS Depository") -> dict:
    with session_scope() as s:
        row = s.get(DematAccount, account_id)
        if row is None:
            row = DematAccount(account_id=account_id, dp_name=dp_name, bo_id=_bo_id(account_id))
            s.add(row)
            s.flush()
        return {"account_id": row.account_id, "dp_name": row.dp_name, "bo_id": row.bo_id}


def _holding(s, account_id: str, symbol: str) -> DematHolding:
    row = s.execute(
        select(DematHolding).where(
            DematHolding.account_id == account_id, DematHolding.symbol == symbol
        )
    ).scalar_one_or_none()
    if row is None:
        row = DematHolding(account_id=account_id, symbol=symbol)
        s.add(row)
        s.flush()
    return row


def record_buy(account_id: str, symbol: str, qty: int, price: float) -> None:
    """A BUY fill: add ``qty`` pending shares (settle T+1) and reprice avg cost."""
    if qty <= 0:
        return
    get_or_create_account(account_id)
    with session_scope() as s:
        h = _holding(s, account_id, symbol)
        held = h.qty_settled + h.qty_pending
        new_total = held + qty
        h.avg_cost = ((h.avg_cost * held) + price * qty) / new_total if new_total else 0.0
        h.qty_pending += qty


def record_sell(account_id: str, symbol: str, qty: int) -> None:
    """A SELL fill: debit settled first, then pending. Refuses to over-sell the
    total position (a real constraint — you cannot deliver shares you don't hold)."""
    if qty <= 0:
        return
    with session_scope() as s:
        h = _holding(s, account_id, symbol)
        total = h.qty_settled + h.qty_pending
        if qty > total:
            raise DematError(
                f"over-sell: {account_id}/{symbol} holds {total}, tried to sell {qty}"
            )
        from_settled = min(qty, h.qty_settled)
        h.qty_settled -= from_settled
        h.qty_pending -= (qty - from_settled)
        if h.qty_settled + h.qty_pending == 0:
            h.avg_cost = 0.0


def settle_pending(account_id: str | None = None) -> int:
    """T+1 settlement: move pending → settled (all accounts, or one). Returns the
    number of shares settled."""
    moved = 0
    with session_scope() as s:
        q = select(DematHolding).where(DematHolding.qty_pending > 0)
        if account_id is not None:
            q = q.where(DematHolding.account_id == account_id)
        for h in s.execute(q).scalars().all():
            moved += h.qty_pending
            h.qty_settled += h.qty_pending
            h.qty_pending = 0
    if moved:
        log.info("demat_settled", extra={"shares": moved, "account": account_id or "all"})
    return moved


def holdings(account_id: str) -> list[dict]:
    with session_scope() as s:
        rows = s.execute(
            select(DematHolding)
            .where(DematHolding.account_id == account_id)
            .order_by(DematHolding.symbol)
        ).scalars().all()
        return [
            {"symbol": h.symbol, "qty_settled": h.qty_settled,
             "qty_pending": h.qty_pending, "qty_total": h.qty_settled + h.qty_pending,
             "avg_cost": round(h.avg_cost, 2)}
            for h in rows if (h.qty_settled + h.qty_pending) > 0
        ]


def account_summary(account_id: str) -> dict:
    acct = get_or_create_account(account_id)
    hs = holdings(account_id)
    return {
        **acct,
        "holdings": hs,
        "pending": sum(h["qty_pending"] for h in hs),
        "symbols": len(hs),
    }


def check_positions_vs_demat(account_id: str) -> list[str]:
    """Reconciliation third leg (P2): broker positions must equal demat
    settled+pending per symbol."""
    from ats.services.execution.portfolio import get_positions

    pos = {p["symbol"]: p["qty"] for p in get_positions(account_id)}
    dem = {h["symbol"]: h["qty_total"] for h in holdings(account_id)}
    out: list[str] = []
    for sym in sorted(set(pos) | set(dem)):
        if pos.get(sym, 0) != dem.get(sym, 0):
            out.append(f"{account_id}/{sym}: positions {pos.get(sym, 0)} != demat {dem.get(sym, 0)}")
    return out
