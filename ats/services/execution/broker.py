"""Broker adapter interface.

Both the paper broker and the real Kite adapter implement ``submit`` with the
same signature, so the autonomy switch can route to either transparently. The
real adapter additionally refuses to run unless the real-money gate is open.
"""

from __future__ import annotations

from typing import Protocol


class BrokerAdapter(Protocol):
    name: str

    def submit(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        limit_price: float | None = None,
        decision_id: int | None = None,
    ) -> dict: ...
