"""Tests for the backtest-hygiene toolkit (walk-forward, MC, DSR)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.backtest.validation import (
    deflated_sharpe_ratio,
    grid_search,
    monte_carlo_drawdowns,
    plateau_ratio,
    walk_forward,
    walk_forward_splits,
)


def _trend_prices(n: int = 500, seed: int = 11) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = 0.0006 + 0.01 * rng.standard_normal(n)
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(100.0 * np.cumprod(1.0 + rets), index=idx)


def _direction_signal(prices: pd.Series, go: int = 1) -> pd.Series:
    return pd.Series(float(go), index=prices.index)


# --- splits ---------------------------------------------------------------------
def test_splits_are_ordered_and_non_overlapping():
    splits = walk_forward_splits(500, train=252, test=63)
    assert len(splits) >= 2
    for train_sl, test_sl in splits:
        assert train_sl.stop == test_sl.start          # test follows train
        assert test_sl.stop - test_sl.start == 63
    # Consecutive windows advance by the test size (no test overlap).
    assert splits[1][1].start - splits[0][1].start == 63


def test_splits_validate_inputs():
    with pytest.raises(ValueError):
        walk_forward_splits(100, train=1, test=10)


# --- grid search + walk-forward -----------------------------------------------------
def test_grid_search_picks_long_in_uptrend():
    prices = _trend_prices()
    best, results = grid_search(prices, _direction_signal, {"go": [-1, 0, 1]})
    assert best == {"go": 1}
    assert len(results) == 3


def test_walk_forward_reports_out_of_sample_only():
    prices = _trend_prices()
    result = walk_forward(
        prices, _direction_signal, {"go": [-1, 1]}, train=150, test=50
    )
    assert result.oos is not None
    n_windows = len(result.windows)
    assert n_windows == len(walk_forward_splits(len(prices), 150, 50))
    assert len(result.oos_returns) == n_windows * 50
    # Long-only optimum on an uptrend: stitched OOS equity should grow.
    assert result.oos.total_return > 0
    assert all(w["params"] == {"go": 1} for w in result.windows)


def test_walk_forward_with_too_little_data():
    prices = _trend_prices(100)
    result = walk_forward(prices, _direction_signal, {"go": [1]}, train=252, test=63)
    assert result.oos is None and result.windows == []


# --- Monte Carlo ----------------------------------------------------------------------
def test_monte_carlo_is_deterministic_and_ordered():
    rng = np.random.default_rng(3)
    rets = pd.Series(0.0004 + 0.012 * rng.standard_normal(500))
    a = monte_carlo_drawdowns(rets, n_sims=300, seed=7)
    b = monte_carlo_drawdowns(rets, n_sims=300, seed=7)
    assert a == b  # deterministic under a fixed seed
    # Severity ordering: median <= p90 <= p95 <= worst (all negative).
    assert a["dd_p50"] >= a["dd_p90"] >= a["dd_p95"] >= a["dd_worst"]
    assert a["dd_worst"] <= 0.0
    assert a["cagr_p05"] <= a["cagr_p50"]


def test_monte_carlo_needs_enough_data():
    with pytest.raises(ValueError):
        monte_carlo_drawdowns(pd.Series([0.01] * 10), block=5)


# --- plateau --------------------------------------------------------------------------
def test_plateau_flat_grid_scores_high_spike_scores_low():
    flat = {10: 1.00, 20: 0.97, 30: 0.95, 40: 0.93}
    spiky = {10: 1.00, 20: 0.10, 30: 0.05, 40: 0.02}
    assert plateau_ratio(flat) > 0.9
    assert plateau_ratio(spiky) < 0.5


def test_plateau_handles_negatives_and_empty():
    assert plateau_ratio({1: -0.5, 2: -1.0}) == 0.0
    with pytest.raises(ValueError):
        plateau_ratio({})


# --- deflated Sharpe -------------------------------------------------------------------
def test_dsr_penalizes_many_trials():
    one = deflated_sharpe_ratio(sharpe=1.5, n_trials=1, n_obs=504)
    many = deflated_sharpe_ratio(sharpe=1.5, n_trials=200, n_obs=504)
    assert one > many  # same Sharpe is less impressive after 200 tries


def test_dsr_strong_edge_survives_modest_search():
    assert deflated_sharpe_ratio(sharpe=2.5, n_trials=10, n_obs=756) > 0.95


def test_dsr_zero_sharpe_is_no_discovery():
    assert deflated_sharpe_ratio(sharpe=0.0, n_trials=50, n_obs=504) < 0.5


def test_dsr_fat_tails_reduce_confidence():
    # Premise requires an edge that survives deflation (SR above the
    # noise-expected max); only then do fatter tails cost confidence.
    normal = deflated_sharpe_ratio(2.0, n_trials=10, n_obs=756, kurtosis=3.0)
    fat = deflated_sharpe_ratio(2.0, n_trials=10, n_obs=756, kurtosis=12.0)
    assert normal > 0.5  # the edge is real before widening the bars
    assert fat < normal


def test_dsr_validates_inputs():
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(1.0, n_trials=0, n_obs=100)
