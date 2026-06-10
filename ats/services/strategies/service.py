"""Strategy Service.

Reacts to BAR events with a strict ordering per bar:

1. **Mark sleeves** — each strategy's virtual book accrues today's
   close-to-close return on yesterday's holdings (look-ahead safe), and
   completed days are persisted for attribution + decay detection.
2. **Evaluate per-symbol strategies** over the symbol's history.
3. **Evaluate universe strategies** (pairs/cross-sectional) once per
   poll cycle, when the last watchlist symbol's bar arrives.

Every emitted signal passes through the regime tilt (conviction is
dampened — never boosted — when the strategy's style mismatches the
current market regime) and updates its sleeve's virtual holdings. The
latest signal per (strategy, symbol) is kept in memory; actionable
signals are persisted/published only on a stance change to avoid
flooding the DB on every poll.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
from sqlalchemy import select

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Signal, SleevePnl, Strategy as StrategyRow
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.allocation import (
    conviction_multipliers,
    inverse_vol_weights,
)
from ats.services.strategies.library import (
    default_strategies,
    default_universe_strategies,
)
from ats.services.strategies.sleeves import FinalizedDay, SleeveTracker

log = get_logger("ats.strategies")

_HISTORY_BARS = 400  # enough for 200-SMA filters and 12-1 momentum


class StrategyService:
    name = "strategies"

    def __init__(self) -> None:
        self._strategies = default_strategies()
        self._universe_strategies = default_universe_strategies()
        self._bus: EventBus | None = None
        self._md = None
        self._regime = None
        self._status: dict[str, str] = {}
        # latest[symbol][strategy_id] = SignalModel
        self._latest: dict[str, dict[str, SignalModel]] = {}
        settings = get_settings()
        self._sleeves = SleeveTracker(
            decay_sharpe=settings.sleeve_decay_sharpe,
            decay_min_days=settings.sleeve_decay_min_days,
        )
        # Inverse-vol capital allocation across sleeves (recomputed daily).
        self._alloc_weights: dict[str, float] = {}
        self._alloc_mult: dict[str, float] = {}

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        self._regime = ctx.orchestrator.get("regime")
        self._status = self._load_status()
        ctx.bus.subscribe(Topic.BAR, self._on_bar)

    async def _on_bar(self, evt) -> None:
        symbol = evt.payload.get("symbol")
        if not symbol or self._md is None:
            return
        df = self._md.get_history(symbol, limit=_HISTORY_BARS)
        if df.empty:
            return

        # 1) Sleeves first: today's return belongs to yesterday's holdings.
        await self._mark_sleeves(symbol, df)

        # 2) Per-symbol strategies.
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
            await self._handle_signal(sig, strat.style)

        # 3) Universe strategies, once per poll cycle (on the last symbol's
        # bar, when every history in the cycle is fresh).
        watchlist = self._md.watchlist()
        if watchlist and symbol == watchlist[-1]:
            await self._run_universe_strategies(watchlist)

    async def _run_universe_strategies(self, watchlist: list[str]) -> None:
        for strat in self._universe_strategies:
            if self._status.get(strat.id) == "paused":
                continue
            needed = strat.symbols() or watchlist
            history: dict[str, pd.DataFrame] = {}
            for sym in needed:
                df = self._md.get_history(sym, limit=_HISTORY_BARS)
                if not df.empty:
                    history[sym] = df
            try:
                signals = strat.evaluate_universe(history)
            except Exception as exc:  # noqa: BLE001
                log.warning("strategy_error", extra={"strategy": strat.id, "error": str(exc)})
                continue
            for sig in signals:
                await self._handle_signal(sig, strat.style)

    async def _handle_signal(self, sig: SignalModel, style: str) -> None:
        # Regime tilt: dampen conviction when the style mismatches the
        # current market regime (never boost; see quant.analysis.regime).
        if self._regime is not None and sig.conviction > 0:
            tilt = self._regime.tilt_for(style)
            if tilt < 1.0:
                sig = sig.model_copy(
                    update={
                        "conviction": round(sig.conviction * tilt, 4),
                        "features": {
                            **sig.features,
                            "regime_tilt": tilt,
                            "regime": self._regime.current().label,
                        },
                    }
                )

        # Sleeve capital allocation: dampen the voice of sleeves that earn
        # a below-top inverse-vol weight (the top sleeve keeps 1.0).
        alloc = self._alloc_mult.get(sig.strategy, 1.0)
        if alloc < 1.0 and sig.conviction > 0:
            sig = sig.model_copy(
                update={
                    "conviction": round(sig.conviction * alloc, 4),
                    "features": {
                        **sig.features,
                        "sleeve_weight": self._alloc_weights.get(sig.strategy),
                    },
                }
            )

        # Long-only sleeves: bullish stances hold the name, others are flat.
        self._sleeves.update_holding(sig.strategy, sig.symbol, sig.stance.direction)

        per_symbol = self._latest.setdefault(sig.symbol, {})
        prev = per_symbol.get(sig.strategy)
        per_symbol[sig.strategy] = sig
        changed = prev is None or prev.stance != sig.stance
        if sig.stance != Stance.NEUTRAL and changed:
            self._persist(sig)
            if self._bus is not None:
                await self._bus.publish(Topic.SIGNAL, sig.model_dump(mode="json"))

    # --- sleeves -------------------------------------------------------------
    async def _mark_sleeves(self, symbol: str, df: pd.DataFrame) -> None:
        close = float(df["close"].iloc[-1])
        last_ts = df.index[-1]
        day = last_ts.date() if isinstance(last_ts, (pd.Timestamp, datetime)) else date.today()
        finalized = self._sleeves.mark_bar(symbol, close, day)
        if finalized:
            self._reallocate()
        for fin in finalized:
            self._persist_sleeve_day(fin)
            if fin.decayed and self._bus is not None:
                sharpe = self._sleeves.rolling_sharpe(fin.strategy)
                log.warning(
                    "strategy_decay",
                    extra={"strategy": fin.strategy, "sharpe": sharpe, "days": fin.day.isoformat()},
                )
                await self._bus.publish(
                    Topic.ALERT,
                    {
                        "kind": "strategy_decay",
                        "strategy": fin.strategy,
                        "sharpe": sharpe,
                        "message": (
                            f"Sleeve {fin.strategy} rolling Sharpe {sharpe} fell below "
                            "the decay threshold; review before it keeps trading."
                        ),
                    },
                )

    def _reallocate(self) -> None:
        """Recompute inverse-vol sleeve weights on each completed day."""
        self._alloc_weights = inverse_vol_weights(self._sleeves.returns_by_sleeve())
        self._alloc_mult = conviction_multipliers(self._alloc_weights)
        with session_scope() as s:
            for sid, weight in self._alloc_weights.items():
                row = s.get(StrategyRow, sid)
                if row is not None:
                    row.weight = self._alloc_mult.get(sid, 1.0)
                    row.allocation_pct = weight

    @staticmethod
    def _persist_sleeve_day(fin: FinalizedDay) -> None:
        with session_scope() as s:
            row = s.execute(
                select(SleevePnl).where(
                    SleevePnl.strategy == fin.strategy, SleevePnl.day == fin.day
                )
            ).scalar_one_or_none()
            if row is None:
                row = SleevePnl(strategy=fin.strategy, day=fin.day)
                s.add(row)
            row.ret = fin.ret
            row.equity = fin.equity
            row.holdings = fin.holdings

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

    # --- accessors for agents/risk/dashboard --------------------------------
    def latest_for(self, symbol: str) -> list[SignalModel]:
        return list(self._latest.get(symbol, {}).values())

    def all_latest(self) -> dict[str, list[SignalModel]]:
        return {sym: list(d.values()) for sym, d in self._latest.items()}

    def sleeve_stats(self) -> list[dict]:
        stats = self._sleeves.stats()
        for s in stats:
            s["alloc_weight"] = self._alloc_weights.get(s["strategy"])
        return stats

    @staticmethod
    def _load_status() -> dict[str, str]:
        with session_scope() as s:
            rows = s.execute(select(StrategyRow)).scalars().all()
            return {r.id: r.status for r in rows}
