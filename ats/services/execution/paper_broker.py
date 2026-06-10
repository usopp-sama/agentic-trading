"""Paper broker: simulates fills against the latest price with slippage + fees.

Implements the same ``submit`` interface a real broker adapter will, so the
autonomy switch (Phase 7) can route to either without caring which is which.
"""

from __future__ import annotations

from collections.abc import Callable

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Fill, Order
from ats.services.execution.fees import compute_charges
from ats.services.execution.portfolio import apply_fill

log = get_logger("ats.paper_broker")

# Adverse slippage applied to the fill price (5 bps).
SLIPPAGE_BPS = 5.0


class PaperBroker:
    name = "paper"

    def __init__(self, account: str = "paper", price_fn: Callable[[str], "float | None"] | None = None) -> None:
        self.account = account
        self._price_fn = price_fn or (lambda _s: None)

    def set_price_fn(self, price_fn: Callable[[str], "float | None"]) -> None:
        self._price_fn = price_fn

    def submit(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        limit_price: float | None = None,
        decision_id: int | None = None,
    ) -> dict:
        side = side.upper()
        if qty <= 0:
            return {"status": "REJECTED", "reason": "qty must be positive"}
        ref_price = limit_price or self._price_fn(symbol)
        if ref_price is None:
            return {"status": "REJECTED", "reason": f"no price for {symbol}"}

        # Adverse slippage: pay up to buy, receive less to sell.
        slip = ref_price * (SLIPPAGE_BPS / 10_000.0)
        fill_price = ref_price + slip if side == "BUY" else ref_price - slip
        charges = compute_charges(side, qty, fill_price)

        with session_scope() as s:
            order = Order(
                decision_id=decision_id,
                account=self.account,
                broker=self.name,
                symbol=symbol,
                side=side,
                qty=qty,
                order_type=order_type,
                limit_price=limit_price,
                status="FILLED",
                broker_order_id=None,
            )
            s.add(order)
            s.flush()  # get order.id
            order_id = order.id
            s.add(
                Fill(
                    order_id=order_id,
                    qty=qty,
                    price=round(fill_price, 2),
                    fees=charges.total,
                    slippage=round(abs(slip) * qty, 2),
                )
            )

        result = apply_fill(self.account, symbol, side, qty, fill_price, charges.total)
        log.info(
            "paper_fill",
            extra={
                "symbol": symbol, "side": side, "qty": qty,
                "price": round(fill_price, 2), "fees": charges.total,
                "realized_delta": result["realized_delta"],
            },
        )
        return {
            "status": "FILLED",
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "fill_price": round(fill_price, 2),
            "fees": charges.total,
            "realized_delta": result["realized_delta"],
            "cash": result["cash"],
        }
