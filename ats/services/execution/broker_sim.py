"""BrokerSim: a Kite-shaped broker simulator over the AccountLedger.

The interface (``BrokerAPI``) mirrors the shape of Zerodha Kite Connect —
``place_order`` / ``cancel_order`` / ``order_status`` / ``positions`` /
``holdings`` / ``margins`` / ``ltp`` — so that when the real Kite adapter is
built it implements the *same* interface and the swap is one class, zero logic
changes.

Money flow per order (the "bank account" integration):
    place_order(BUY)  → ledger.reserve(ref, est_value)   # cash held
        fill          → ledger.settle(ref, BUY, value, fees)
        reject/cancel → ledger.release(ref)
    place_order(SELL) → holdings check (long-only, no cash hold needed)
        fill          → ledger.settle(ref, SELL, value, fees)

Order lifecycle (validated transitions, even though the sim fills instantly):
    STAGED → SUBMITTED → ACKED → FILLED
                       ↘ REJECTED          (validation/funds/price failures)
    STAGED/SUBMITTED/ACKED → CANCELLED     (explicit cancel before fill)

Fills reuse the same fee model (`fees.py`) and adverse-slippage rule as the
original paper broker, and write the same ``Order``/``Fill`` rows and position
updates (`portfolio.apply_fill`), so the Activity page and P&L pipeline see
BrokerSim fills exactly like paper-broker fills.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Fill, Order
from ats.services.accounts import AccountLedger, InsufficientFunds
from ats.services.execution.fees import compute_charges
from ats.services.execution.portfolio import apply_fill, get_positions

log = get_logger("ats.broker_sim")

SLIPPAGE_BPS = 5.0  # adverse slippage on market fills, same as paper broker

# Valid order-state transitions. Terminal states have no exits.
_TRANSITIONS: dict[str, set[str]] = {
    "STAGED": {"SUBMITTED", "REJECTED", "CANCELLED"},
    "SUBMITTED": {"ACKED", "REJECTED", "CANCELLED"},
    "ACKED": {"PARTIAL", "FILLED", "REJECTED", "CANCELLED"},
    "PARTIAL": {"PARTIAL", "FILLED", "CANCELLED"},
    "FILLED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}
TERMINAL_STATES = frozenset(k for k, v in _TRANSITIONS.items() if not v)


def can_transition(from_state: str, to_state: str) -> bool:
    return to_state in _TRANSITIONS.get(from_state, set())


class BrokerAPI(ABC):
    """The broker contract. BrokerSim implements it now; KiteAdapter later."""

    @abstractmethod
    def place_order(
        self, account_id: str, symbol: str, side: str, qty: int,
        order_type: str = "MARKET", limit_price: float | None = None,
        decision_id: int | None = None,
    ) -> dict: ...

    @abstractmethod
    def cancel_order(self, order_id: int) -> dict: ...

    @abstractmethod
    def order_status(self, order_id: int) -> dict: ...

    @abstractmethod
    def positions(self, account_id: str) -> list[dict]: ...

    @abstractmethod
    def margins(self, account_id: str) -> dict: ...

    @abstractmethod
    def ltp(self, symbol: str) -> float | None: ...


class BrokerSim(BrokerAPI):
    """Simulated broker: instant validated fills, real money discipline."""

    name = "broker_sim"

    def __init__(self, price_fn: Callable[[str], "float | None"] | None = None) -> None:
        self._price_fn = price_fn or (lambda _s: None)
        self._ledgers: dict[str, AccountLedger] = {}

    def set_price_fn(self, price_fn: Callable[[str], "float | None"]) -> None:
        self._price_fn = price_fn

    def ledger(self, account_id: str) -> AccountLedger:
        if account_id not in self._ledgers:
            self._ledgers[account_id] = AccountLedger(account_id)
        return self._ledgers[account_id]

    # -- BrokerAPI ------------------------------------------------------------
    def place_order(
        self, account_id: str, symbol: str, side: str, qty: int,
        order_type: str = "MARKET", limit_price: float | None = None,
        decision_id: int | None = None,
    ) -> dict:
        side = side.upper()

        # STAGED: persist the order first so every attempt leaves a record.
        order_id = self._create_order(
            account_id, symbol, side, qty, order_type, limit_price, decision_id
        )
        ref = f"order:{order_id}"

        # Validation gauntlet — any failure is a journaled REJECTED, not an exception.
        if side not in ("BUY", "SELL"):
            return self._reject(order_id, account_id, ref, f"invalid side {side!r}")
        if qty <= 0:
            return self._reject(order_id, account_id, ref, "qty must be positive")

        ref_price = limit_price or self._price_fn(symbol)
        if ref_price is None or ref_price <= 0:
            return self._reject(order_id, account_id, ref, f"no price for {symbol}")

        if side == "BUY":
            try:
                self.ledger(account_id).reserve(ref, qty * ref_price)
            except InsufficientFunds as e:
                return self._reject(order_id, account_id, ref, str(e), release=False)
        else:
            held = {p["symbol"]: p["qty"] for p in get_positions(account_id)}
            if held.get(symbol, 0) < qty:
                return self._reject(
                    order_id, account_id, ref,
                    f"long-only: hold {held.get(symbol, 0)} {symbol}, tried to sell {qty}",
                )

        # SUBMITTED → ACKED → FILLED (instant in sim; the states still exist so
        # the same code path works when a real broker answers asynchronously).
        self._set_status(order_id, "SUBMITTED")
        self._set_status(order_id, "ACKED")
        return self._fill(order_id, account_id, ref, symbol, side, qty, ref_price)

    def cancel_order(self, order_id: int) -> dict:
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                return {"status": "ERROR", "reason": f"unknown order {order_id}"}
            if not can_transition(order.status, "CANCELLED"):
                return {"status": order.status, "reason": "not cancellable"}
            order.status = "CANCELLED"
            account, symbol = order.account, order.symbol
        self.ledger(account).release(f"order:{order_id}", note=f"cancel {symbol}")
        log.info("order_cancelled", extra={"order_id": order_id, "account": account})
        return {"status": "CANCELLED", "order_id": order_id}

    def order_status(self, order_id: int) -> dict:
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                return {"status": "ERROR", "reason": f"unknown order {order_id}"}
            return {
                "order_id": order.id, "account": order.account,
                "symbol": order.symbol, "side": order.side, "qty": order.qty,
                "order_type": order.order_type, "limit_price": order.limit_price,
                "status": order.status, "decision_id": order.decision_id,
            }

    def positions(self, account_id: str) -> list[dict]:
        return get_positions(account_id)

    def margins(self, account_id: str) -> dict:
        return self.ledger(account_id).balance().as_dict()

    def ltp(self, symbol: str) -> float | None:
        return self._price_fn(symbol)

    # -- PaperBroker-compatible shim (drop-in for ExecutionService) -------------
    account = "paper"  # default; ExecutionService-style callers may set it

    def submit(
        self, symbol: str, side: str, qty: int, order_type: str = "MARKET",
        limit_price: float | None = None, decision_id: int | None = None,
    ) -> dict:
        return self.place_order(
            self.account, symbol, side, qty, order_type, limit_price, decision_id
        )

    # -- internals ------------------------------------------------------------
    def _create_order(
        self, account_id: str, symbol: str, side: str, qty: int,
        order_type: str, limit_price: float | None, decision_id: int | None,
    ) -> int:
        with session_scope() as s:
            order = Order(
                decision_id=decision_id, account=account_id, broker=self.name,
                symbol=symbol, side=side, qty=max(qty, 0),
                order_type=order_type, limit_price=limit_price, status="STAGED",
            )
            s.add(order)
            s.flush()
            return order.id

    def _set_status(self, order_id: int, status: str) -> None:
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise RuntimeError(f"order {order_id} vanished")
            if not can_transition(order.status, status):
                raise RuntimeError(
                    f"illegal order transition {order.status} → {status} (order {order_id})"
                )
            order.status = status

    def _reject(
        self, order_id: int, account_id: str, ref: str, reason: str,
        release: bool = True,
    ) -> dict:
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is not None and can_transition(order.status, "REJECTED"):
                order.status = "REJECTED"
        if release:
            self.ledger(account_id).release(ref, note=f"reject: {reason[:80]}")
        log.info("order_rejected", extra={"order_id": order_id, "reason": reason})
        return {"status": "REJECTED", "order_id": order_id, "reason": reason}

    def _fill(
        self, order_id: int, account_id: str, ref: str,
        symbol: str, side: str, qty: int, ref_price: float,
    ) -> dict:
        # Adverse slippage: pay up to buy, receive less to sell.
        slip = ref_price * (SLIPPAGE_BPS / 10_000.0)
        fill_price = ref_price + slip if side == "BUY" else ref_price - slip
        charges = compute_charges(side, qty, fill_price)
        gross = qty * fill_price

        # Money first: if settlement fails the order rejects and nothing fills.
        try:
            self.ledger(account_id).settle(
                ref, side, gross, charges.total, note=f"{side} {qty} {symbol}"
            )
        except InsufficientFunds as e:
            return self._reject(order_id, account_id, ref, f"settlement failed: {e}")

        self._set_status(order_id, "FILLED")
        with session_scope() as s:
            s.add(Fill(
                order_id=order_id, qty=qty, price=round(fill_price, 2),
                fees=charges.total, slippage=round(abs(slip) * qty, 2),
            ))
        # Position leg only — the ledger settle above already moved the cash;
        # apply_fill's cash leg would double-count it.
        result = apply_fill(
            account_id, symbol, side, qty, fill_price, charges.total, update_cash=False
        )

        log.info("sim_fill", extra={
            "account": account_id, "symbol": symbol, "side": side, "qty": qty,
            "price": round(fill_price, 2), "fees": charges.total,
        })
        return {
            "status": "FILLED", "order_id": order_id, "symbol": symbol,
            "side": side, "qty": qty, "fill_price": round(fill_price, 2),
            "fees": charges.total,
            "realized_delta": result["realized_delta"], "cash": result["cash"],
        }
