"""Core allocation sleeve — the boring, primary ballast (plan §2).

Regime-aware weights across NIFTYBEES (equity) / GOLDBEES (gold) /
LIQUIDBEES (cash proxy), recomputed on a weekly cadence and immediately on
a regime flip. Deterministic, LLM-free, and deliberately dull: this sleeve
is expected to carry most of the realistic return at near-zero cost while
the alpha sleeves fight over the rest.

The regime is classified from the equity ETF's own close series with the
same pure functions the RegimeService uses (no service wiring needed), so
this strategy is a self-contained function of its inputs and trivially
backtestable.

Signal semantics: on each rebalance (weekly or regime flip) it emits one
signal per ETF — BUY with conviction = target weight for meaningful
allocations, SELL for de-emphasized ones — and stays silent between
rebalances. Deliberately: the slow loop decided the weights calmly; the
fast/medium loops apply them mechanically.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import UniverseStrategy
from quant.analysis.regime import (
    TREND_DOWN,
    TREND_UP,
    VOL_CRISIS,
    classify,
)

EQUITY = "NIFTYBEES.NS"
GOLD = "GOLDBEES.NS"
CASH = "LIQUIDBEES.NS"

# Target weights per regime: (equity, gold, cash-proxy). Conservative by
# construction — crisis vol always dominates the trend axis.
_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "up": (0.70, 0.20, 0.10),
    "range": (0.50, 0.30, 0.20),
    "down": (0.25, 0.40, 0.35),
    "crisis": (0.15, 0.35, 0.50),
}
# Below this target weight an ETF is de-emphasized: exit rather than hold.
_MIN_HOLD_WEIGHT = 0.20


class CoreAllocation(UniverseStrategy):
    id = "core_allocation"
    style = "other"  # ballast fits every regime; never dampened by the tilt
    min_bars = 210   # 200-day MA for the trend axis

    def __init__(self, rebalance_days: int = 7) -> None:
        self.rebalance_days = rebalance_days
        self._last_rebalance: date | None = None
        self._last_regime: str | None = None

    def symbols(self) -> list[str]:
        return [EQUITY, GOLD, CASH]

    # --- the weights table -------------------------------------------------
    @staticmethod
    def target_weights(trend: str, vol: str) -> tuple[float, float, float]:
        if vol == VOL_CRISIS:
            return _WEIGHTS["crisis"]
        if trend == TREND_UP:
            return _WEIGHTS["up"]
        if trend == TREND_DOWN:
            return _WEIGHTS["down"]
        return _WEIGHTS["range"]

    # --- evaluation ----------------------------------------------------------
    def evaluate_universe(
        self, history: dict[str, pd.DataFrame]
    ) -> list[SignalModel]:
        eq = history.get(EQUITY)
        if eq is None or len(eq) < self.min_bars:
            return []

        regime = classify(eq["close"])
        last_ts = eq.index[-1]
        today = (
            last_ts.date()
            if isinstance(last_ts, (pd.Timestamp, datetime))
            else date.today()
        )

        flipped = self._last_regime is not None and regime.label != self._last_regime
        due = (
            self._last_rebalance is None
            or today - self._last_rebalance >= timedelta(days=self.rebalance_days)
        )
        if not (due or flipped):
            self._last_regime = regime.label
            return []

        self._last_rebalance = today
        self._last_regime = regime.label
        weights = dict(zip((EQUITY, GOLD, CASH), self.target_weights(regime.trend, regime.vol)))

        signals: list[SignalModel] = []
        for symbol, weight in weights.items():
            if symbol not in history or history[symbol].empty:
                continue  # can't act on what we can't see; skip, don't guess
            if weight >= _MIN_HOLD_WEIGHT:
                stance, conviction = Stance.BUY, weight
            else:
                stance, conviction = Stance.SELL, 0.4
            signals.append(self._signal(
                symbol, stance, conviction,
                target_weight=weight, regime=regime.label,
                trigger="regime_flip" if flipped else "weekly_rebalance",
            ))
        return signals
