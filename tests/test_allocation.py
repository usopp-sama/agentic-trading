"""Tests for inverse-vol capital allocation across sleeves (Part 8.4)."""

from __future__ import annotations

import numpy as np
import pytest

from ats.services.strategies.allocation import (
    conviction_multipliers,
    inverse_vol_weights,
)


def _noise(scale: float, n: int = 60, seed: int = 1) -> list[float]:
    rng = np.random.default_rng(seed)
    return list(scale * rng.standard_normal(n))


def test_equal_vol_gives_equal_weights():
    rets = {"a": _noise(0.01, seed=1), "b": _noise(0.01, seed=1), "c": _noise(0.01, seed=1)}
    w = inverse_vol_weights(rets)
    assert all(v == pytest.approx(1 / 3, abs=1e-6) for v in w.values())
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)


def test_low_vol_sleeve_gets_more_capital():
    rets = {"calm": _noise(0.005), "wild": _noise(0.03)}
    w = inverse_vol_weights(rets)
    assert w["calm"] > w["wild"]
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)


def test_cap_binds_on_extreme_vol_gap():
    rets = {
        "tiny": _noise(0.0001),
        "a": _noise(0.02, seed=2),
        "b": _noise(0.02, seed=3),
        "c": _noise(0.02, seed=4),
    }
    w = inverse_vol_weights(rets, floor=0.05, cap=0.35)
    assert w["tiny"] == pytest.approx(0.35, abs=1e-6)  # capped, not 99%
    assert all(0.05 - 1e-9 <= v <= 0.35 + 1e-9 for v in w.values())
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)


def test_two_sleeves_relax_unsatisfiable_cap():
    # Two sleeves cannot both sit under a 35% cap; the cap relaxes to
    # 1.25/n = 62.5% so the inverse-vol ordering survives.
    rets = {"a": _noise(0.005), "b": _noise(0.03)}
    w = inverse_vol_weights(rets, floor=0.05, cap=0.35)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)
    assert w["a"] > w["b"]
    assert max(w.values()) <= 0.625 + 1e-9


def test_short_history_gets_equal_share_prior():
    rets = {"new": [0.01] * 5, "calm": _noise(0.01, seed=5), "wild": _noise(0.01, seed=6)}
    w = inverse_vol_weights(rets, min_days=20)
    # The new sleeve is treated as average risk: between the others, not 0.
    assert w["new"] > 0.05
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)


def test_no_history_at_all_is_equal_weight():
    w = inverse_vol_weights({"a": [], "b": [], "c": [], "d": []})
    assert all(v == pytest.approx(0.25) for v in w.values())


def test_multipliers_are_dampen_only_with_top_at_one():
    mult = conviction_multipliers({"a": 0.5, "b": 0.3, "c": 0.2})
    assert mult["a"] == pytest.approx(1.0)
    assert 0.0 < mult["c"] < mult["b"] < 1.0


def test_empty_inputs():
    assert inverse_vol_weights({}) == {}
    assert conviction_multipliers({}) == {}
