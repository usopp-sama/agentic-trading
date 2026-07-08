"""Core allocation sleeve: regime → weights, cadence, and flip semantics.

Engineered price paths make the regime unambiguous; the sleeve must map it
to the right ETF weights, rebalance weekly, rebalance immediately on a
regime flip, and stay silent in between.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.strategies.core_allocation import (
    CASH,
    EQUITY,
    GOLD,
    CoreAllocation,
)


def _frame(close: np.ndarray, start: str = "2024-01-01") -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range(start, periods=len(close), name="date")
    return pd.DataFrame(
        {
            "open": np.concatenate([[close[0]], close[:-1]]),
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        },
        index=idx,
    )


def _uptrend(n: int = 260) -> np.ndarray:
    # Steady climb: price ends well above its 200-day MA, vol shrinking.
    return 100.0 + 0.3 * np.arange(n)


def _crisis(n: int = 260) -> np.ndarray:
    # Long quiet base, then a violently volatile 30-bar crash: trend down
    # AND realized vol at its own extreme -> crisis weights must win.
    rng = np.random.default_rng(7)
    base = 100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.004, size=n - 30))
    crash = [base[-1]]
    for i in range(30):
        crash.append(crash[-1] * (0.90 if i % 2 == 0 else 1.02))
    return np.concatenate([base, crash[1:]])


def _history(close: np.ndarray) -> dict[str, pd.DataFrame]:
    # Gold drifts, cash proxy is flat: only the equity series drives regime.
    n = len(close)
    return {
        EQUITY: _frame(close),
        GOLD: _frame(60.0 + 0.01 * np.arange(n)),
        CASH: _frame(np.full(n, 1000.0)),
    }


def _by_symbol(signals) -> dict[str, object]:
    return {s.symbol: s for s in signals}


# --- regime → weights ----------------------------------------------------------
def test_uptrend_overweights_equity():
    sigs = _by_symbol(CoreAllocation().evaluate_universe(_history(_uptrend())))
    assert sigs[EQUITY].stance == Stance.BUY
    assert sigs[EQUITY].conviction == 0.70
    assert sigs[GOLD].stance == Stance.BUY
    assert sigs[GOLD].conviction == 0.20
    # 10% cash target is below the hold floor -> de-emphasize, exit.
    assert sigs[CASH].stance == Stance.SELL
    assert sigs[EQUITY].features["trigger"] == "weekly_rebalance"


def test_crisis_flees_to_cash_and_gold():
    sigs = _by_symbol(CoreAllocation().evaluate_universe(_history(_crisis())))
    assert sigs[CASH].stance == Stance.BUY
    assert sigs[CASH].conviction == 0.50
    assert sigs[GOLD].stance == Stance.BUY
    # 15% equity is below the hold floor in a crisis -> exit.
    assert sigs[EQUITY].stance == Stance.SELL
    assert "crisis" in sigs[EQUITY].features["regime"]


def test_weights_always_sum_to_one():
    from ats.services.strategies.core_allocation import _WEIGHTS

    for label, (eq, gold, cash) in _WEIGHTS.items():
        assert abs(eq + gold + cash - 1.0) < 1e-9, label


# --- cadence -------------------------------------------------------------------
def test_silent_between_rebalances():
    strat = CoreAllocation(rebalance_days=7)
    up = _uptrend()
    assert strat.evaluate_universe(_history(up))  # first pass rebalances
    # Next day, same regime: silence.
    assert strat.evaluate_universe(_history(np.append(up, up[-1] + 0.3))) == []


def test_weekly_rebalance_fires_after_cadence():
    strat = CoreAllocation(rebalance_days=7)
    up = _uptrend()
    assert strat.evaluate_universe(_history(up))
    # 6 more business days (>= 7 calendar days later): due again.
    ext = np.concatenate([up, up[-1] + 0.3 * np.arange(1, 7)])
    sigs = strat.evaluate_universe(_history(ext))
    assert sigs and sigs[0].features["trigger"] == "weekly_rebalance"


def test_regime_flip_rebalances_immediately():
    strat = CoreAllocation(rebalance_days=7)
    up = _uptrend()
    assert strat.evaluate_universe(_history(up))
    # Three violent bars flip the vol axis to crisis well inside the week.
    flip = np.concatenate([up, [up[-1] * 0.88, up[-1] * 0.97, up[-1] * 0.80]])
    sigs = strat.evaluate_universe(_history(flip))
    assert sigs, "flip must rebalance before the weekly cadence"
    assert sigs[0].features["trigger"] == "regime_flip"
    assert _by_symbol(sigs)[CASH].stance == Stance.BUY


# --- guards ---------------------------------------------------------------------
def test_short_history_is_silent():
    sigs = CoreAllocation().evaluate_universe(_history(_uptrend(100)))
    assert sigs == []


def test_missing_etf_history_is_skipped_not_guessed():
    hist = _history(_uptrend())
    del hist[GOLD]
    sigs = CoreAllocation().evaluate_universe(hist)
    symbols = {s.symbol for s in sigs}
    assert GOLD not in symbols
    assert EQUITY in symbols and CASH in symbols
