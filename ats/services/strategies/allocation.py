"""Capital allocation across strategy sleeves (roadmap Part 8.4).

Stage 2 of the plan's allocation ladder: **inverse-volatility weights**
(naive risk parity). Each sleeve is weighted by 1/sigma of its daily
virtual returns so every sleeve contributes roughly equal risk — a
volatile sleeve automatically gets less capital influence. Weights are
bounded (default 5%–35%) so no sleeve is starved or dominant, exactly
as the roadmap prescribes for the later performance-tilted stage.

Sleeves without enough history are treated as average-risk (they get
the equal-weight share) rather than excluded — a brand-new strategy
should start at par, not at zero and not over-allocated.

Applied downstream as **dampen-only conviction multipliers** (the
highest-weighted sleeve keeps multiplier 1.0), consistent with how
regime tilts work: the allocation layer can shrink a sleeve's voice,
never amplify a signal beyond what the strategy itself claimed.

Pure functions; the StrategyService owns when to recompute.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_MIN_VOL = 1e-6


def inverse_vol_weights(
    returns_by_sleeve: dict[str, Sequence[float]],
    floor: float = 0.05,
    cap: float = 0.35,
    min_days: int = 20,
) -> dict[str, float]:
    """Bounded inverse-volatility weights, summing to ~1.0.

    Sleeves with fewer than ``min_days`` observations are assigned the
    median vol of the informed sleeves (neutral prior). With no informed
    sleeve at all, everything is equal weight. Bounds are relaxed when N
    is too small for them to be satisfiable (e.g. two sleeves cannot both
    be under a 35% cap).
    """
    ids = sorted(returns_by_sleeve)
    n = len(ids)
    if n == 0:
        return {}
    equal = 1.0 / n
    floor_eff = min(floor, equal)
    # The cap needs headroom beyond 1/n, or small books are forced to exact
    # equality and the inverse-vol signal is destroyed (n=2, cap 0.35 ->
    # both sleeves pinned at 50%). 1.25/n keeps n*cap >= 1.25.
    cap_eff = min(1.0, max(cap, 1.25 / n))

    vols: dict[str, float | None] = {}
    for sid in ids:
        rets = list(returns_by_sleeve[sid])
        vols[sid] = _stdev(rets) if len(rets) >= min_days else None
    informed = [v for v in vols.values() if v is not None]
    if not informed:
        return {sid: equal for sid in ids}
    neutral = _median(informed)
    inv = {
        sid: 1.0 / max(v if v is not None else neutral, _MIN_VOL)
        for sid, v in vols.items()
    }

    total = sum(inv.values())
    weights = {sid: w / total for sid, w in inv.items()}
    return _clamp_normalize(weights, floor_eff, cap_eff)


def conviction_multipliers(weights: dict[str, float]) -> dict[str, float]:
    """Dampen-only multipliers: the top-weighted sleeve keeps 1.0."""
    if not weights:
        return {}
    top = max(weights.values())
    if top <= 0:
        return {sid: 1.0 for sid in weights}
    return {sid: w / top for sid, w in weights.items()}


def _clamp_normalize(
    weights: dict[str, float], floor: float, cap: float
) -> dict[str, float]:
    """Clamp to [floor, cap], then redistribute the imbalance
    proportionally to each sleeve's remaining headroom (under-allocated)
    or slack above the floor (over-allocated). Because the caller
    guarantees n*cap >= 1 >= n*floor, each redistribution step stays in
    bounds and the result sums to 1.
    """
    out = {sid: min(max(w, floor), cap) for sid, w in weights.items()}
    for _ in range(20):
        total = sum(out.values())
        if abs(total - 1.0) < 1e-9:
            break
        if total < 1.0:
            headroom = {sid: cap - w for sid, w in out.items()}
            room = sum(headroom.values())
            if room <= 0:
                break
            missing = 1.0 - total
            out = {sid: w + missing * headroom[sid] / room for sid, w in out.items()}
        else:
            slack = {sid: w - floor for sid, w in out.items()}
            give = sum(slack.values())
            if give <= 0:
                break
            excess = total - 1.0
            out = {sid: w - excess * slack[sid] / give for sid, w in out.items()}
    return {sid: round(w, 6) for sid, w in out.items()}


def _stdev(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean = sum(xs) / n
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))


def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0
