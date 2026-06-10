"""Zerodha Kite broker adapter (DORMANT in v1).

This is a structural stub: it conforms to ``BrokerAdapter`` and contains the
shape of real order placement (token refresh, rate-limit handling,
reconciliation) but hard-refuses to place real orders unless the real-money
gate is explicitly open AND credentials are configured. It is never reached in
v1 because the gate is disabled.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.logging import get_logger

log = get_logger("ats.kite")


class KiteAdapter:
    name = "kite"

    def __init__(self) -> None:
        self._kite = None  # would hold a kiteconnect.KiteConnect instance

    def _ensure_ready(self) -> None:
        settings = get_settings()
        if not settings.real_money_enabled:
            raise RuntimeError("Real-money gate is CLOSED; Kite adapter must not run.")
        if not (settings.kite_api_key and settings.kite_access_token):
            raise RuntimeError("Kite credentials are not configured.")
        # Real init would happen here (lazy import of kiteconnect, token refresh).
        raise NotImplementedError(
            "Kite live trading is intentionally not enabled in v1. Enable only "
            "after paper/shadow validation and the SEBI algo-compliance checklist."
        )

    def submit(self, symbol, side, qty, order_type="MARKET", limit_price=None, decision_id=None) -> dict:  # pragma: no cover
        self._ensure_ready()
        # Unreachable in v1. Real implementation: map symbol->instrument_token,
        # kite.place_order(...), poll order status, reconcile fills.
        raise NotImplementedError
