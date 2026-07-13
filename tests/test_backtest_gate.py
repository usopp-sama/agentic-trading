"""Tests for the strategy backtest harness and the shadow->paper gate."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.backtest import (
    portfolio_returns,
    replay_per_symbol,
    run_gate,
)
from ats.services.strategies.base import Strategy
from ats.services.strategies.library_trend_mr import MacdAdxTrend


def _frame(close: np.ndarray) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2023-01-01", periods=len(close), name="date")
    return pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5,
         "close": close, "volume": np.full(len(close), 1e6)},
        index=idx,
    )


class _AlwaysLong(Strategy):
    id = "always_long"
    style = "trend"
    min_bars = 5

    def evaluate(self, symbol, df):
        return SignalModel(strategy=self.id, symbol=symbol, stance=Stance.BUY,
                           conviction=1.0, features={})


class _AlwaysFlat(Strategy):
    id = "always_flat"
    style = "other"
    min_bars = 5

    def evaluate(self, symbol, df):
        return SignalModel(strategy=self.id, symbol=symbol, stance=Stance.NEUTRAL,
                           conviction=0.0, features={})


def test_replay_positions_are_lookahead_safe():
    df = _frame(100.0 + np.arange(60))
    positions = replay_per_symbol(_AlwaysLong(), {"X": df}, step=1)
    # Long-only always-long -> all 1.0 once warmed up.
    assert positions["X"].iloc[-1] == 1.0


def test_always_long_on_uptrend_has_positive_sharpe():
    panel = {f"S{i}": _frame(100.0 * (1.001 ** np.arange(250))) for i in range(3)}
    positions = replay_per_symbol(_AlwaysLong(), panel, step=1)
    rets = portfolio_returns(positions, panel, fee_bps=1.0)
    assert rets.sum() > 0  # rode the uptrend


def test_gate_promotes_winner_holds_flat():
    panel = {f"S{i}": _frame(100.0 * (1.0015 ** np.arange(250))) for i in range(3)}
    report = run_gate(
        panel,
        per_symbol_strategies=[_AlwaysLong(), _AlwaysFlat()],
        universe_strategies=[],
        dsr_threshold=0.5, min_obs=20, step=1,
    )
    by_id = {r.strategy: r for r in report.results}
    assert by_id["always_long"].sharpe > 0
    # Flat strategy never trades -> no active obs -> cannot pass.
    assert by_id["always_flat"].n_obs == 0
    assert not by_id["always_flat"].passes


def test_gate_n_trials_override_penalizes_dsr():
    # Pinning n_trials higher applies a bigger multiple-testing penalty, so the
    # same strategy's deflated Sharpe drops. Lets a --only subset stay comparable
    # to the full 26-way baseline (E5b).
    rng = np.random.default_rng(0)
    daily = 0.0006 + 0.011 * rng.standard_normal(300)   # moderate Sharpe (~0.9), unsaturated DSR
    close = 100.0 * np.cumprod(1.0 + daily)
    panel = {"S": _frame(close)}
    kw = dict(per_symbol_strategies=[_AlwaysLong()], universe_strategies=[],
              dsr_threshold=0.5, min_obs=20, step=1)
    dsr_solo = run_gate(panel, n_trials=1, **kw).results[0].deflated_sharpe
    dsr_full = run_gate(panel, n_trials=200, **kw).results[0].deflated_sharpe
    assert dsr_solo > dsr_full


def test_gate_handles_real_strategy_without_crashing():
    panel = {"X": _frame(100.0 + 1.0 * np.arange(200))}
    report = run_gate(panel, per_symbol_strategies=[MacdAdxTrend()],
                      universe_strategies=[], dsr_threshold=0.9, min_obs=10, step=2)
    assert report.results and report.results[0].strategy == "macd_adx_trend"
