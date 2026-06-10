"""Strategy Service.

Reacts to BAR events: runs each active strategy over the symbol's history,
keeps the latest signal per (strategy, symbol), and publishes/persists
actionable signals (it persists only when a signal's stance changes, to avoid
flooding the DB on every poll).
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Signal, Strategy as StrategyRow
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.library import default_strategies

log = get_logger("ats.strategies")


class StrategyService:
    name = "strategies"

    def __init__(self) -> None:
        self._strategies = default_strategies()
        self._bus: EventBus | None = None
        self._md = None
        self._status: dict[str, str] = {}
        # latest[symbol][strategy_id] = SignalModel
        self._latest: dict[str, dict[str, SignalModel]] = {}

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        self._status = self._load_status()
        ctx.bus.subscribe(Topic.BAR, self._on_bar)

    async def _on_bar(self, evt) -> None:
        symbol = evt.payload.get("symbol")
        if not symbol or self._md is None:
            return
        df = self._md.get_history(symbol)
        if df.empty:
            return
        per_symbol = self._latest.setdefault(symbol, {})
        for strat in self._strategies:
            if self._status.get(strat.id) == "paused":
                continue
            try:
                sig = strat.evaluate(symbol, df)
            except Exception as exc:  # noqa: BLE001
                log.warning("strategy_error", extra={"strategy": strat.id, "symbol": symbol, "error": str(exc)})
                continue
            if sig is None:
                continue
            prev = per_symbol.get(strat.id)
            per_symbol[strat.id] = sig
            changed = prev is None or prev.stance != sig.stance
            if sig.stance != Stance.NEUTRAL and changed:
                self._persist(sig)
                if self._bus is not None:
                    await self._bus.publish(Topic.SIGNAL, sig.model_dump(mode="json"))

    @staticmethod
    def _persist(sig: SignalModel) -> None:
        with session_scope() as s:
            s.add(
                Signal(
                    strategy=sig.strategy,
                    symbol=sig.symbol,
                    stance=sig.stance.value,
                    conviction=sig.conviction,
                    features=sig.features,
                )
            )

    # --- accessors for agents/risk ----------------------------------------
    def latest_for(self, symbol: str) -> list[SignalModel]:
        return list(self._latest.get(symbol, {}).values())

    def all_latest(self) -> dict[str, list[SignalModel]]:
        return {sym: list(d.values()) for sym, d in self._latest.items()}

    @staticmethod
    def _load_status() -> dict[str, str]:
        with session_scope() as s:
            rows = s.execute(select(StrategyRow)).scalars().all()
            return {r.id: r.status for r in rows}
