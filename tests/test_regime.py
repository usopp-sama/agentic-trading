"""Tests for the market regime classifier (pure functions)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import regime


def _series(values) -> pd.Series:
    return pd.Series(np.asarray(values, dtype=float))


def test_short_history_defaults_to_neutral():
    state = regime.classify(_series(np.linspace(100, 110, 50)))
    assert state.trend == regime.TREND_RANGE
    assert state.vol == regime.VOL_NORMAL


def test_rising_series_is_uptrend():
    close = _series(100.0 * (1.0 + 0.001) ** np.arange(300))
    assert regime.classify_trend(close) == regime.TREND_UP


def test_falling_series_is_downtrend():
    close = _series(100.0 * (1.0 - 0.001) ** np.arange(300))
    assert regime.classify_trend(close) == regime.TREND_DOWN


def test_flat_series_is_range():
    rng = np.random.default_rng(3)
    close = _series(100.0 + 0.1 * rng.standard_normal(300))
    assert regime.classify_trend(close) == regime.TREND_RANGE


def test_vol_spike_is_crisis():
    rng = np.random.default_rng(5)
    calm = 0.002 * rng.standard_normal(280)
    wild = 0.06 * rng.standard_normal(40)
    close = _series(100.0 * np.exp(np.cumsum(np.concatenate([calm, wild]))))
    assert regime.classify_vol(close) == regime.VOL_CRISIS


def test_quiet_tail_is_calm():
    rng = np.random.default_rng(5)
    wild = 0.04 * rng.standard_normal(280)
    calm = 0.001 * rng.standard_normal(60)
    close = _series(100.0 * np.exp(np.cumsum(np.concatenate([wild, calm]))))
    assert regime.classify_vol(close) == regime.VOL_CALM


def test_tilt_dampens_mismatched_styles_only():
    up = regime.RegimeState(trend=regime.TREND_UP)
    rng_ = regime.RegimeState(trend=regime.TREND_RANGE)
    # Trend strategies keep full conviction in trends, are dampened in ranges.
    assert regime.tilt_for("trend", up) == 1.0
    assert regime.tilt_for("trend", rng_) < 1.0
    # Mean reversion is the mirror image.
    assert regime.tilt_for("mean_reversion", rng_) == 1.0
    assert regime.tilt_for("mean_reversion", up) < 1.0
    # Unknown styles are never modified, and tilts never boost.
    assert regime.tilt_for("arbitrage", up) == 1.0
    for style in ("trend", "momentum", "mean_reversion", "other"):
        for state in (up, rng_):
            assert 0.0 < regime.tilt_for(style, state) <= 1.0
