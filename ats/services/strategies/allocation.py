"""Capital allocation across strategy sleeves (roadmap Part 8.4).

The plan's allocation ladder, all stages implemented here:

- **Stage 2 — inverse-volatility** (naive risk parity): weight each
  sleeve by 1/sigma of its daily virtual returns.
- **Stage 3 — equal risk contribution (ERC)**: full covariance-aware
  risk parity. The property stage 2 misses: two highly *correlated*
  sleeves are really one bet — ERC sizes them down together and hands
  the diversifying sleeve more capital.
- **Stage 4 — bounded performance tilt**: scale weights toward sleeves
  with better rolling Sharpe, bounded so performance-chasing can never
  concentrate the book.

``allocate`` is the entry point and stages automatically: ERC needs a
trustworthy covariance estimate, so until every-pair joint history is
long enough it falls back to inverse-vol (and the tilt only ever
applies on top of ERC).

Sleeves without enough history are treated as average-risk (median-vol
prior, zero correlation) rather than excluded — a brand-new strategy
should start at par, not at zero and not over-allocated.

Weights are bounded (default 5%–35%) and applied downstream as
**dampen-only conviction multipliers** (the highest-weighted sleeve
keeps multiplier 1.0), consistent with how regime tilts work: the
allocation layer can shrink a sleeve's voice, never amplify a signal
beyond what the strategy itself claimed.

Pure functions; the StrategyService owns when to recompute.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

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


def erc_weights(
    returns_by_sleeve: dict[str, Sequence[float]],
    floor: float = 0.05,
    cap: float = 0.35,
    min_days: int = 20,
) -> dict[str, float]:
    """Stage-3 equal-risk-contribution weights, bounded.

    The covariance matrix is built from the overlapping tail of each
    pair's history. Sleeves with fewer than ``min_days`` observations
    get a neutral prior: the median variance of informed sleeves and
    zero correlation with everyone (an unknown strategy is assumed
    average-risk and diversifying, which keeps it near the equal-weight
    share until evidence arrives).
    """
    ids = sorted(returns_by_sleeve)
    n = len(ids)
    if n == 0:
        return {}
    equal = 1.0 / n
    if n == 1:
        return {ids[0]: 1.0}
    floor_eff = min(floor, equal)
    cap_eff = min(1.0, max(cap, 1.25 / n))

    informed = [
        sid for sid in ids if len(returns_by_sleeve[sid]) >= min_days
    ]
    if len(informed) < 2:
        return inverse_vol_weights(returns_by_sleeve, floor, cap, min_days)

    variances = {
        sid: float(np.var(np.asarray(returns_by_sleeve[sid], dtype=float), ddof=1))
        for sid in informed
    }
    neutral_var = max(float(np.median(list(variances.values()))), _MIN_VOL**2)

    cov = np.full((n, n), 0.0)
    for i, a in enumerate(ids):
        cov[i, i] = max(variances.get(a, neutral_var), _MIN_VOL**2)
        for j in range(i + 1, n):
            b = ids[j]
            if a in variances and b in variances:
                ra = np.asarray(returns_by_sleeve[a], dtype=float)
                rb = np.asarray(returns_by_sleeve[b], dtype=float)
                k = min(len(ra), len(rb))
                if k >= min_days:
                    c = float(np.cov(ra[-k:], rb[-k:], ddof=1)[0, 1])
                    cov[i, j] = cov[j, i] = c
            # else: zero covariance prior for uninformed pairs.

    raw = _solve_erc(cov)
    weights = {sid: float(raw[i]) for i, sid in enumerate(ids)}
    return _clamp_normalize(weights, floor_eff, cap_eff)


def _solve_erc(cov: np.ndarray, iters: int = 500, tol: float = 1e-10) -> np.ndarray:
    """Fixed-point iteration for equal risk contributions.

    Update w_i <- w_i * (mean(RC) / RC_i)^0.5, renormalize; converges
    for positive-definite covariances at the handful-of-sleeves scale
    this is used at. Falls back to inverse-vol proportions if risk
    contributions degenerate.
    """
    n = cov.shape[0]
    vols = np.sqrt(np.clip(np.diag(cov), _MIN_VOL**2, None))
    w = (1.0 / vols) / np.sum(1.0 / vols)
    for _ in range(iters):
        marginal = cov @ w
        rc = w * marginal
        if np.any(rc <= 0):
            return w
        target = float(np.mean(rc))
        update = np.sqrt(target / rc)
        new = w * update
        new = new / np.sum(new)
        if float(np.max(np.abs(new - w))) < tol:
            return new
        w = new
    return w


def performance_tilt(
    weights: dict[str, float],
    sharpe_by_sleeve: dict[str, float | None],
    strength: float = 0.25,
    floor: float = 0.05,
    cap: float = 0.35,
) -> dict[str, float]:
    """Stage-4 bounded tilt toward sleeves with better rolling Sharpe.

    Each weight is scaled by ``1 + strength * tanh(sharpe / 2)`` — a
    Sharpe of +2 earns about a +19% scaling at the default strength, a
    deeply negative one the mirror image, and an unknown Sharpe is
    neutral. Bounds are re-applied after renormalizing, so the tilt can
    lean the book but never concentrate it.
    """
    if not weights:
        return {}
    n = len(weights)
    floor_eff = min(floor, 1.0 / n)
    cap_eff = min(1.0, max(cap, 1.25 / n))
    tilted = {}
    for sid, w in weights.items():
        sharpe = sharpe_by_sleeve.get(sid)
        scale = 1.0 + strength * math.tanh(sharpe / 2.0) if sharpe is not None else 1.0
        tilted[sid] = w * scale
    total = sum(tilted.values())
    if total <= 0:
        return dict(weights)
    tilted = {sid: w / total for sid, w in tilted.items()}
    return _clamp_normalize(tilted, floor_eff, cap_eff)


def allocate(
    returns_by_sleeve: dict[str, Sequence[float]],
    sharpe_by_sleeve: dict[str, float | None] | None = None,
    method: str = "auto",
    floor: float = 0.05,
    cap: float = 0.35,
    min_days: int = 20,
    erc_min_days: int = 40,
) -> dict[str, float]:
    """Allocation entry point with automatic staging.

    ``auto`` uses ERC + performance tilt once at least two sleeves have
    ``erc_min_days`` of history (a covariance needs more data than a
    vol estimate to be trustworthy), inverse-vol before that. Explicit
    methods: ``inverse_vol`` | ``erc`` | ``erc_tilt``.
    """
    if method == "inverse_vol":
        return inverse_vol_weights(returns_by_sleeve, floor, cap, min_days)
    seasoned = sum(
        1 for rets in returns_by_sleeve.values() if len(rets) >= erc_min_days
    )
    if method == "auto" and seasoned < 2:
        return inverse_vol_weights(returns_by_sleeve, floor, cap, min_days)
    weights = erc_weights(returns_by_sleeve, floor, cap, min_days)
    if method == "erc":
        return weights
    return performance_tilt(weights, sharpe_by_sleeve or {}, floor=floor, cap=cap)


def apply_committee_tilt(
    weights: dict[str, float], tilts: dict[str, float], max_tilt: float = 0.10
) -> dict[str, float]:
    """Apply an approved committee recommendation as bounded weight tilts.

    Each sleeve's weight is scaled by ``1 + tilt`` with tilt clamped to
    ``±max_tilt``, then the set is renormalized to sum to 1 — so the
    committee can nudge the mix by at most ±10% per sleeve and can never
    add or remove capital, only shift emphasis. Empty tilts = no-op.
    """
    if not weights or not tilts:
        return dict(weights)
    tilted = {}
    for sid, w in weights.items():
        try:
            t = float(tilts.get(sid, 0.0) or 0.0)
        except (TypeError, ValueError):
            t = 0.0
        tilted[sid] = max(0.0, w * (1.0 + max(-max_tilt, min(max_tilt, t))))
    total = sum(tilted.values())
    if total <= 0:
        return dict(weights)
    return {sid: round(w / total, 6) for sid, w in tilted.items()}


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
