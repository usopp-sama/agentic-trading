"""Engle-Granger cointegration test (self-contained, no statsmodels).

Used by the cointegration pairs strategy to *select* genuinely mean-reverting
pairs rather than trading any correlated-looking spread. The procedure:

1. OLS hedge ratio ``y = alpha + beta * x`` (the cointegrating regression).
2. Augmented Dickey-Fuller test on the residual: if the residual is stationary
   (rejects a unit root), the pair is cointegrated and its spread mean-reverts.

ADF critical values use MacKinnon (2010) response-surface constants for the
constant-only ("c") case. This keeps the dependency footprint at numpy only.

References:
- Engle & Granger (1987), Econometrica — cointegration and error correction.
- MacKinnon (2010) — critical values for cointegration tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CointegrationResult:
    beta: float          # hedge ratio (units of x per unit of y)
    alpha: float         # intercept of the cointegrating regression
    adf_stat: float      # ADF t-statistic on the residual
    crit_5pct: float     # 5% critical value (more negative = stronger)
    cointegrated: bool   # adf_stat < crit_5pct
    residual: np.ndarray # the spread (y - alpha - beta*x)


# MacKinnon (2010) approximate finite-sample critical values, constant case.
# tau = b_inf + b1/T + b2/T^2 for each significance level.
_MK_C = {
    "1pct": (-3.43035, -6.5393, -16.786),
    "5pct": (-2.86154, -2.8903, -4.234),
    "10pct": (-2.56677, -1.5384, -2.809),
}


def _adf_crit(level: str, n: int) -> float:
    b0, b1, b2 = _MK_C[level]
    return b0 + b1 / n + b2 / (n * n)


def adf_test(series: np.ndarray, max_lag: int | None = None) -> tuple[float, float]:
    """Augmented Dickey-Fuller t-stat with a constant; returns (stat, crit5%).

    Regression: Δy_t = c + rho*y_{t-1} + sum_i gamma_i*Δy_{t-i} + e_t.
    The t-stat on ``rho`` is the ADF statistic; a sufficiently negative value
    rejects the unit-root null (i.e. the series is stationary).
    """
    y = np.asarray(series, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 20:
        return float("nan"), _adf_crit("5pct", max(n, 1))
    if max_lag is None:
        # Schwert rule of thumb, capped for short samples.
        max_lag = int(min(12 * (n / 100.0) ** 0.25, n // 4))
    dy = np.diff(y)
    lagged_level = y[:-1]
    # Build design matrix: [const, y_{t-1}, Δy_{t-1}..Δy_{t-max_lag}].
    rows = len(dy) - max_lag
    if rows <= max_lag + 2:
        return float("nan"), _adf_crit("5pct", n)
    cols = [np.ones(rows), lagged_level[max_lag:]]
    for i in range(1, max_lag + 1):
        cols.append(dy[max_lag - i : -i] if i != 0 else dy)
    X = np.column_stack(cols)
    target = dy[max_lag:]
    beta, *_ = np.linalg.lstsq(X, target, rcond=None)
    resid = target - X @ beta
    dof = rows - X.shape[1]
    if dof <= 0:
        return float("nan"), _adf_crit("5pct", n)
    sigma2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    se_rho = float(np.sqrt(sigma2 * xtx_inv[1, 1]))
    if se_rho <= 0:
        return float("nan"), _adf_crit("5pct", n)
    adf_stat = float(beta[1] / se_rho)
    return adf_stat, _adf_crit("5pct", n)


def engle_granger(y: np.ndarray, x: np.ndarray) -> CointegrationResult:
    """Engle-Granger two-step test of ``y`` on ``x``.

    Fits the cointegrating regression by OLS, then runs an ADF test on the
    residual. ``cointegrated`` is True when the ADF stat clears the 5% bar.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    if len(y) < 20:
        return CointegrationResult(float("nan"), float("nan"), float("nan"),
                                   _adf_crit("5pct", max(len(y), 1)), False, np.array([]))
    A = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    resid = y - (alpha + beta * x)
    adf_stat, crit5 = adf_test(resid)
    cointegrated = bool(np.isfinite(adf_stat) and adf_stat < crit5)
    return CointegrationResult(beta, alpha, adf_stat, crit5, cointegrated, resid)
