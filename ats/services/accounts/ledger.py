"""AccountLedger: the simulated bank account behind every trading book.

Each account (main, sme_legacy, solo_<strategy>, benchmark, ...) holds cash,
a set of per-order reservations (holds), and an append-only journal — the
"passbook". No trading logic lives here; the ledger only knows money.

State model
-----------
- ``cash``      total money in the account (excludes nothing; holds are a view)
- ``reserved``  sum of active holds (cash earmarked for staged orders)
- ``available`` cash - reserved  → what a new order may reserve against

Persistence: the balance + holds live in one ``kv_state`` row per account
(key ``ledger:<account>``), written atomically per operation. Every operation
appends a ``LedgerEntry`` journal row. The legacy ``cash:<account>`` key used
by ``portfolio.py`` is kept in sync so existing dashboards/tests keep working
until execution is fully migrated to the ledger.

Flow of an order's money:
    reserve(ref, est_cost)      # order staged   → hold created
    settle(ref, side, value, fees)  # order filled → hold released, cash moves
    release(ref)                # order rejected/cancelled → hold released
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import KvState, LedgerEntry

log = get_logger("ats.accounts.ledger")

# Reserve slightly more than the estimated order value so fees/slippage on the
# fill never overdraw the hold (released on settle; never charged twice).
FEE_BUFFER_PCT = 0.005  # 0.5%


class LedgerError(RuntimeError):
    """Base error for ledger operations."""


class InsufficientFunds(LedgerError):
    """Raised when a withdraw/reserve exceeds the available balance."""


@dataclass(frozen=True)
class Balance:
    cash: float
    reserved: float

    @property
    def available(self) -> float:
        return round(self.cash - self.reserved, 2)

    def as_dict(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "reserved": round(self.reserved, 2),
            "available": self.available,
        }


def _state_key(account: str) -> str:
    return f"ledger:{account}"


def _legacy_cash_key(account: str) -> str:
    return f"cash:{account}"


class AccountLedger:
    """All operations are atomic: state write + journal append in one txn."""

    def __init__(self, account: str) -> None:
        if not account or len(account) > 24:
            raise LedgerError(f"invalid account name: {account!r}")
        self.account = account

    # -- reads ---------------------------------------------------------------
    def balance(self) -> Balance:
        with session_scope() as s:
            state = self._load(s)
        return Balance(cash=state["cash"], reserved=sum(state["holds"].values()))

    def holds(self) -> dict[str, float]:
        with session_scope() as s:
            return dict(self._load(s)["holds"])

    def statement(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """The passbook: newest first."""
        with session_scope() as s:
            q = select(LedgerEntry).where(LedgerEntry.account == self.account)
            if since is not None:
                q = q.where(LedgerEntry.ts >= since)
            if until is not None:
                q = q.where(LedgerEntry.ts <= until)
            rows = s.execute(
                q.order_by(LedgerEntry.ts.desc(), LedgerEntry.id.desc()).limit(limit)
            ).scalars().all()
            return [
                {
                    "ts": r.ts.isoformat(),
                    "kind": r.kind,
                    "amount": r.amount,
                    "reserved_delta": r.reserved_delta,
                    "ref": r.ref,
                    "note": r.note,
                    "cash_after": r.cash_after,
                    "reserved_after": r.reserved_after,
                }
                for r in rows
            ]

    # -- funding ---------------------------------------------------------------
    def deposit(self, amount: float, note: str = "") -> Balance:
        amount = self._positive(amount)
        return self._apply("DEPOSIT", cash_delta=amount, note=note)

    def withdraw(self, amount: float, note: str = "") -> Balance:
        amount = self._positive(amount)
        bal = self.balance()
        if amount > bal.available:
            raise InsufficientFunds(
                f"{self.account}: withdraw {amount:.2f} > available {bal.available:.2f}"
            )
        return self._apply("WITHDRAW", cash_delta=-amount, note=note)

    # -- order money flow ------------------------------------------------------
    def reserve(self, ref: str, amount: float, note: str = "") -> Balance:
        """Hold cash for a staged order. Idempotent per ref (re-reserve replaces)."""
        amount = self._positive(amount)
        buffered = round(amount * (1.0 + FEE_BUFFER_PCT), 2)
        with session_scope() as s:
            state = self._load(s)
            holds = state["holds"]
            existing = holds.get(ref, 0.0)
            reserved_now = sum(holds.values()) - existing
            if buffered > state["cash"] - reserved_now:
                raise InsufficientFunds(
                    f"{self.account}: reserve {buffered:.2f} for {ref} > available "
                    f"{state['cash'] - reserved_now:.2f}"
                )
            holds[ref] = buffered
            self._write(
                s, state,
                kind="RESERVE", cash_delta=0.0, reserved_delta=buffered - existing,
                ref=ref, note=note or f"hold for {ref}",
            )
        bal = self.balance()
        log.info("ledger_reserve", extra={"account": self.account, "ref": ref, "amount": buffered})
        return bal

    def release(self, ref: str, note: str = "") -> Balance:
        """Release a hold (order cancelled/rejected). No-op if no hold exists."""
        with session_scope() as s:
            state = self._load(s)
            held = state["holds"].pop(ref, 0.0)
            if held:
                self._write(
                    s, state,
                    kind="RELEASE", cash_delta=0.0, reserved_delta=-held,
                    ref=ref, note=note or f"release hold for {ref}",
                )
        return self.balance()

    def settle(
        self, ref: str, side: str, gross_value: float, fees: float, note: str = ""
    ) -> Balance:
        """Settle a fill: release the hold, then move cash.

        BUY  → cash -= gross_value + fees   (SETTLE_DEBIT)
        SELL → cash += gross_value - fees   (SETTLE_CREDIT)

        A BUY settle may exceed its hold slightly (slippage); allowed as long
        as total cash stays non-negative.
        """
        side = side.upper()
        if side not in ("BUY", "SELL"):
            raise LedgerError(f"settle side must be BUY/SELL, got {side!r}")
        gross_value = self._positive(gross_value)
        if fees < 0:
            raise LedgerError("fees must be >= 0")

        with session_scope() as s:
            state = self._load(s)
            held = state["holds"].pop(ref, 0.0)
            if side == "BUY":
                delta = -(gross_value + fees)
                kind = "SETTLE_DEBIT"
                if state["cash"] + delta < 0:
                    # put the hold back before failing — nothing changed
                    if held:
                        state["holds"][ref] = held
                    raise InsufficientFunds(
                        f"{self.account}: settle {ref} needs {-delta:.2f}, cash {state['cash']:.2f}"
                    )
            else:
                delta = gross_value - fees
                kind = "SETTLE_CREDIT"
            self._write(
                s, state,
                kind=kind, cash_delta=delta, reserved_delta=-held,
                ref=ref, note=note or f"settle {side} {ref}",
            )
        bal = self.balance()
        log.info(
            "ledger_settle",
            extra={"account": self.account, "ref": ref, "side": side,
                   "gross": gross_value, "fees": fees, "cash": bal.cash},
        )
        return bal

    # -- internals ---------------------------------------------------------------
    @staticmethod
    def _positive(amount: float) -> float:
        amount = round(float(amount), 2)
        if amount <= 0:
            raise LedgerError(f"amount must be positive, got {amount}")
        return amount

    def _load(self, s) -> dict:
        row = s.get(KvState, _state_key(self.account))
        if row is None:
            return {"cash": 0.0, "holds": {}}
        value = dict(row.value or {})
        return {
            "cash": float(value.get("cash", 0.0)),
            "holds": {k: float(v) for k, v in dict(value.get("holds", {})).items()},
        }

    def _write(
        self, s, state: dict, *, kind: str, cash_delta: float,
        reserved_delta: float, ref: str | None = None, note: str = "",
    ) -> None:
        """Persist new state + journal entry inside the caller's session."""
        state["cash"] = round(state["cash"] + cash_delta, 2)
        reserved_after = round(sum(state["holds"].values()), 2)

        payload = {"cash": state["cash"], "holds": state["holds"]}
        row = s.get(KvState, _state_key(self.account))
        if row is None:
            s.add(KvState(key=_state_key(self.account), value=payload))
        else:
            row.value = payload

        # Keep the legacy cash key in sync for portfolio.py / existing pages.
        legacy = s.get(KvState, _legacy_cash_key(self.account))
        if legacy is None:
            s.add(KvState(key=_legacy_cash_key(self.account), value={"cash": state["cash"]}))
        else:
            legacy.value = {"cash": state["cash"]}

        s.add(LedgerEntry(
            account=self.account,
            kind=kind,
            amount=round(cash_delta, 2),
            reserved_delta=round(reserved_delta, 2),
            ref=ref,
            note=note[:256],
            cash_after=state["cash"],
            reserved_after=reserved_after,
        ))

    def _apply(self, kind: str, *, cash_delta: float, note: str = "") -> Balance:
        with session_scope() as s:
            state = self._load(s)
            self._write(s, state, kind=kind, cash_delta=cash_delta,
                        reserved_delta=0.0, note=note)
        return self.balance()
