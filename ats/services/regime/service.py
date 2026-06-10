"""Regime Service.

Reads the configured reference index (default Nifty 50) on each of its
bars and classifies the market regime along two axes: trend
(up/down/range) and volatility (calm/normal/crisis). Publishes a REGIME
event whenever the state changes and serves as the in-process oracle the
strategy layer (conviction tilts) and risk layer (crisis exposure cuts)
query. Degrades to the neutral default when history is short, so it is
always safe to consult.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from quant.analysis.regime import RegimeState, VOL_CRISIS, classify, tilt_for

log = get_logger("ats.regime")


class RegimeService:
    name = "regime"

    def __init__(self) -> None:
        self._bus: EventBus | None = None
        self._md = None
        self._ref: str = ""
        self._state = RegimeState()

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        self._ref = get_settings().regime_reference_symbol
        ctx.bus.subscribe(Topic.BAR, self._on_bar)

    async def _on_bar(self, evt) -> None:
        if evt.payload.get("symbol") != self._ref or self._md is None:
            return
        df = self._md.get_history(self._ref, limit=400)
        if df.empty:
            return
        new = classify(df["close"])
        if new != self._state:
            log.info(
                "regime_change",
                extra={"from": self._state.label, "to": new.label, "ref": self._ref},
            )
            self._state = new
            if self._bus is not None:
                await self._bus.publish(
                    Topic.REGIME,
                    {"trend": new.trend, "vol": new.vol, "label": new.label},
                )
        else:
            self._state = new

    # --- accessors for the strategy and risk layers ------------------------
    def current(self) -> RegimeState:
        return self._state

    def tilt_for(self, style: str) -> float:
        """Dampen-only conviction multiplier for a strategy style."""
        return tilt_for(style, self._state)

    def is_crisis(self) -> bool:
        return self._state.vol == VOL_CRISIS
