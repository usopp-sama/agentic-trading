"""Tests for capital allocation across sleeves (Part 8.4, stages 2-4)."""

from __future__ import annotations

import numpy as np
import pytest

from ats.services.strategies.allocation import (
    _solve_erc,
    allocate,
    conviction_multipliers,
    erc_weights,
    inverse_vol_weights,
    performance_tilt,
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
    assert erc_weights({}) == {}
    assert allocate({}) == {}
    assert performance_tilt({}, {}) == {}


# --- stage 3: equal risk contribution ----------------------------------------
def test_erc_solver_equalizes_risk_contributions():
    cov = np.array(
        [
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.02],
            [0.00, 0.02, 0.01],
        ]
    )
    w = _solve_erc(cov)
    rc = w * (cov @ w)
    assert w.sum() == pytest.approx(1.0, abs=1e-9)
    assert (w > 0).all()
    assert rc.max() / rc.min() == pytest.approx(1.0, abs=1e-4)


def test_erc_downweights_correlated_pair():
    # Sleeves a and b are near-duplicates (one bet); c is independent
    # with the SAME vol. Inverse-vol can't see this; ERC must hand the
    # diversifier more capital than either twin.
    rng = np.random.default_rng(7)
    base = rng.standard_normal(120)
    a = list(0.01 * base)
    b = list(0.01 * (0.97 * base + 0.243 * rng.standard_normal(120)))  # corr ~0.97, same var
    c = list(0.01 * rng.standard_normal(120))
    w = erc_weights({"a": a, "b": b, "c": c})
    iv = inverse_vol_weights({"a": a, "b": b, "c": c})
    assert w["c"] > w["a"] and w["c"] > w["b"]
    # And the diversification bonus exceeds anything inverse-vol granted.
    assert w["c"] - max(w["a"], w["b"]) > iv["c"] - max(iv["a"], iv["b"]) - 1e-6


def test_erc_uninformed_sleeve_gets_near_equal_share():
    rng = np.random.default_rng(9)
    rets = {
        "a": list(0.01 * rng.standard_normal(120)),
        "b": list(0.01 * rng.standard_normal(120)),
        "new": [0.01] * 5,
    }
    w = erc_weights(rets)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-4)
    assert w["new"] == pytest.approx(1 / 3, abs=0.10)


def test_erc_single_or_uninformed_falls_back():
    assert erc_weights({"only": [0.01] * 60}) == {"only": 1.0}
    # Fewer than two informed sleeves -> inverse-vol path.
    short = {"a": [0.01] * 5, "b": [0.02] * 5}
    assert erc_weights(short) == inverse_vol_weights(short)


# --- stage 4: bounded performance tilt -----------------------------------------
def test_tilt_leans_toward_higher_sharpe():
    w = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    tilted = performance_tilt(w, {"a": 2.0, "b": -2.0, "c": 0.0, "d": None})
    assert tilted["a"] > tilted["c"] > tilted["b"]
    assert tilted["d"] == pytest.approx(tilted["c"], abs=0.02)  # unknown ~ neutral
    assert sum(tilted.values()) == pytest.approx(1.0, abs=1e-4)


def test_tilt_is_bounded():
    w = {"a": 0.34, "b": 0.33, "c": 0.33}
    tilted = performance_tilt(w, {"a": 10.0, "b": -10.0, "c": 0.0}, floor=0.05, cap=0.35)
    assert max(tilted.values()) <= 0.4167 + 1e-6  # cap_eff = 1.25/3
    assert min(tilted.values()) >= 0.05 - 1e-9


# --- allocate(): automatic staging ----------------------------------------------
def test_allocate_stages_by_history_depth():
    rng = np.random.default_rng(21)
    young = {
        "a": list(0.01 * rng.standard_normal(25)),
        "b": list(0.02 * rng.standard_normal(25)),
    }
    assert allocate(young, method="auto") == inverse_vol_weights(young)

    base = rng.standard_normal(120)
    seasoned = {
        "a": list(0.01 * base),
        "b": list(0.01 * (0.97 * base + 0.243 * rng.standard_normal(120))),
        "c": list(0.01 * rng.standard_normal(120)),
    }
    auto = allocate(seasoned, {"a": None, "b": None, "c": None}, method="auto")
    assert auto != inverse_vol_weights(seasoned)
    assert auto["c"] > auto["a"]  # the ERC fingerprint


def test_allocate_explicit_methods():
    rng = np.random.default_rng(31)
    rets = {
        "a": list(0.01 * rng.standard_normal(120)),
        "b": list(0.03 * rng.standard_normal(120)),
    }
    iv = allocate(rets, method="inverse_vol")
    erc = allocate(rets, method="erc")
    tilted = allocate(rets, {"a": 3.0, "b": -3.0}, method="erc_tilt")
    assert iv["a"] > iv["b"]
    assert erc["a"] > erc["b"]
    assert tilted["a"] > erc["a"] - 1e-9  # the tilt leans further toward a
