"""Tests for the proven-strategy library (roadmap Part 7).

Each strategy is exercised on engineered price paths where the correct
answer is unambiguous, plus guard tests for the filters that protect
capital (trend filter, skip window, long-only pair legs).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.strategies.library import (
    DonchianTrend,
    PairsZScore,
    Rsi2MeanReversion,
    TimeSeriesMomentum,
)


def _frame(close: np.ndarray, spread: float = 0.5) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2024-01-01", periods=len(close), name="date")
    return pd.DataFrame(
        {
            "open": np.concatenate([[close[0]], close[:-1]]),
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        },
        index=idx,
    )


# --- Donchian trend following ------------------------------------------------
def test_donchian_buys_breakout():
    # Strictly rising: every close is a breakout of the prior 55-bar high.
    df = _frame(100.0 + np.arange(80) * 2.0)
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.conviction > 0


def test_donchian_sells_breakdown():
    df = _frame(300.0 - np.arange(80) * 2.0)
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.SELL


def test_donchian_neutral_inside_channel():
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.05, size=80))
    df = _frame(close, spread=8.0)  # wide bars -> wide channel -> no breakout
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.NEUTRAL


# --- RSI(2) pullback ----------------------------------------------------------
def test_rsi2_buys_pullback_in_uptrend():
    # Long steady uptrend, then two sharp down days: oversold but still
    # comfortably above the 200-SMA.
    close = list(100.0 * (1.002 ** np.arange(248)))
    close += [close[-1] * 0.97, close[-1] * 0.94]
    sig = Rsi2MeanReversion().evaluate("X", _frame(np.array(close)))
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["trend_ok"] is True
    assert sig.conviction >= 0.5


def test_rsi2_stands_aside_below_trend():
    # Oversold in a downtrend must NOT buy (the falling-knife filter).
    close = 400.0 * (0.998 ** np.arange(248))
    close = np.concatenate([close, [close[-1] * 0.97, close[-1] * 0.94]])
    sig = Rsi2MeanReversion().evaluate("X", _frame(close))
    assert sig is not None and sig.stance == Stance.NEUTRAL
    assert sig.features["trend_ok"] is False


def test_rsi2_exits_overbought():
    close = list(100.0 * (1.002 ** np.arange(248)))
    close += [close[-1] * 1.03, close[-1] * 1.06]  # two strong up days
    sig = Rsi2MeanReversion().evaluate("X", _frame(np.array(close)))
    assert sig is not None and sig.stance == Stance.SELL


# --- 12-1 time-series momentum -------------------------------------------------
def test_momentum_buys_uptrend_despite_recent_dip():
    # Strong year-long climb, then a sharp final month. The skip window
    # must ignore the recent crash and still read positive momentum.
    climb = 100.0 * (1.001 ** np.arange(280))
    dip = climb[-1] * (0.99 ** np.arange(1, 21))
    sig = TimeSeriesMomentum().evaluate("X", _frame(np.concatenate([climb, dip])))
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["mom_return"] > 0


def test_momentum_sells_downtrend():
    decline = 400.0 * (0.999 ** np.arange(300))
    sig = TimeSeriesMomentum().evaluate("X", _frame(decline))
    assert sig is not None and sig.stance == Stance.SELL


def test_momentum_neutral_when_flat():
    rng = np.random.default_rng(13)
    flat = 100.0 + np.cumsum(rng.normal(0.0, 0.02, size=300))
    sig = TimeSeriesMomentum().evaluate("X", _frame(flat))
    assert sig is not None and sig.stance == Stance.NEUTRAL


def test_momentum_requires_enough_history():
    short = _frame(100.0 + np.arange(100, dtype=float))
    assert TimeSeriesMomentum().evaluate("X", short) is None


# --- Pairs z-score --------------------------------------------------------------
def _pair_history(diverge: float) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(17)
    base = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, size=120)))
    a = base * 1.5
    b = base.copy()
    # Push A rich vs B over the last bars.
    a[-3:] = a[-3:] * (1.0 + diverge)
    return {"A": _frame(a), "B": _frame(b)}


def test_pairs_buys_cheap_leg_when_spread_stretches():
    strat = PairsZScore(pairs=[("A", "B")])
    signals = {s.symbol: s for s in strat.evaluate_universe(_pair_history(0.10))}
    assert signals["B"].stance == Stance.BUY      # cheap leg
    assert signals["A"].stance == Stance.SELL     # rich leg (flatten only)
    assert signals["A"].features["zscore"] >= 2.0


def test_pairs_neutral_when_converged():
    strat = PairsZScore(pairs=[("A", "B")])
    signals = strat.evaluate_universe(_pair_history(0.0))
    assert all(s.stance == Stance.NEUTRAL for s in signals)


def test_pairs_skips_missing_leg():
    strat = PairsZScore(pairs=[("A", "MISSING")])
    history = {"A": _frame(100.0 + np.arange(120, dtype=float))}
    assert strat.evaluate_universe(history) == []


def test_pairs_declares_needed_symbols():
    strat = PairsZScore(pairs=[("A", "B"), ("B", "C")])
    assert strat.symbols() == ["A", "B", "C"]
