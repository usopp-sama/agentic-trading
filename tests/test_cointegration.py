"""Tests for the self-contained Engle-Granger cointegration toolkit."""

from __future__ import annotations

import numpy as np

from quant.analysis.cointegration import adf_test, engle_granger


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = phi * y[i - 1] + rng.standard_normal()
    return y


def test_adf_rejects_unit_root_for_stationary_series():
    stat = _ar1(300, phi=0.5, seed=0)
    adf_stat, crit5 = adf_test(stat)
    assert adf_stat < crit5  # reject unit root -> stationary


def test_adf_does_not_reject_random_walk():
    rng = np.random.default_rng(1)
    rw = np.cumsum(rng.standard_normal(300))
    adf_stat, crit5 = adf_test(rw)
    assert adf_stat > crit5  # cannot reject unit root -> non-stationary


def test_adf_handles_short_series_gracefully():
    stat, crit = adf_test(np.arange(5.0))
    assert np.isnan(stat)


def test_engle_granger_detects_cointegration():
    rng = np.random.default_rng(2)
    x = np.cumsum(rng.standard_normal(300)) + 50.0
    noise = _ar1(300, phi=0.6, seed=3) * 0.3
    y = 2.0 * x + noise
    res = engle_granger(y, x)
    assert res.cointegrated
    assert abs(res.beta - 2.0) < 0.2  # recovers the true hedge ratio


def test_engle_granger_rejects_independent_walks():
    rng = np.random.default_rng(4)
    x = np.cumsum(rng.standard_normal(300)) + 50.0
    y = np.cumsum(rng.standard_normal(300)) + 50.0
    res = engle_granger(y, x)
    assert not res.cointegrated
