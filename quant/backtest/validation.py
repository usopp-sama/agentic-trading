"""Backtest hygiene: the anti-overfitting toolkit (roadmap Part 12).

A great-looking backtest is the default outcome of trying hard enough,
not evidence of an edge. These tools are the defense the roadmap
prescribes before any strategy touches the capital ladder:

- ``walk_forward``: optimize parameters on a training window, evaluate
  on the *next* unseen window, roll forward, and report ONLY the
  stitched out-of-sample performance.
- ``monte_carlo_drawdowns``: block-bootstrap the return series to get a
  *distribution* of drawdowns/CAGRs — size capital for the 95th
  percentile drawdown, not the backtest's one lucky path.
- ``plateau_ratio``: an edge that collapses when a parameter moves 20%
  is curve-fit noise; robust edges live on plateaus.
- ``deflated_sharpe_ratio``: Bailey & Lopez de Prado's correction for
  multiple testing — after trying N variants, the best one's Sharpe is
  inflated by selection; DSR is the probability the true Sharpe exceeds
  zero given how many things were tried.

Pure functions over pandas/numpy; the live system shares none of this
code path (it consumes conclusions, not curves).
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from quant.backtest.engine import BacktestResult, backtest_signals

# Euler-Mascheroni constant (expected-maximum formula).
_EULER_GAMMA = 0.5772156649015329

SignalFn = Callable[..., pd.Series]  # (prices, **params) -> target positions


# --- walk-forward ------------------------------------------------------------
def walk_forward_splits(
    n_obs: int, train: int, test: int, step: int | None = None
) -> list[tuple[slice, slice]]:
    """Rolling (train, test) index slices with the test always AFTER train."""
    if train < 2 or test < 1:
        raise ValueError("train must be >= 2 and test >= 1")
    step = step or test
    splits: list[tuple[slice, slice]] = []
    start = 0
    while start + train + test <= n_obs:
        splits.append(
            (slice(start, start + train), slice(start + train, start + train + test))
        )
        start += step
    return splits


def grid_search(
    prices: pd.Series,
    signal_fn: SignalFn,
    param_grid: dict[str, Sequence],
    metric: str = "sharpe",
    fee_bps: float = 1.0,
) -> tuple[dict, list[dict]]:
    """Exhaustive search over the grid; returns (best_params, all results)."""
    names = sorted(param_grid)
    results: list[dict] = []
    for combo in itertools.product(*(param_grid[n] for n in names)):
        params = dict(zip(names, combo))
        try:
            res = backtest_signals(prices, signal_fn(prices, **params), fee_bps=fee_bps)
            score = float(getattr(res, metric))
        except Exception:  # noqa: BLE001 - a bad combo scores worst, not fatal
            score = float("-inf")
        results.append({"params": params, metric: score})
    best = max(results, key=lambda r: r[metric])
    return best["params"], results


@dataclass
class WalkForwardResult:
    oos_returns: pd.Series          # stitched out-of-sample returns
    oos: BacktestResult | None      # stats over the stitched series
    windows: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        if self.oos is None:
            return "walk-forward: no complete windows"
        lines = [f"windows: {len(self.windows)}", "--- out-of-sample ---", self.oos.summary()]
        return "\n".join(lines)


def walk_forward(
    prices: pd.Series,
    signal_fn: SignalFn,
    param_grid: dict[str, Sequence],
    train: int = 252,
    test: int = 63,
    metric: str = "sharpe",
    fee_bps: float = 1.0,
) -> WalkForwardResult:
    """Roll: optimize on each train window, trade the NEXT test window.

    Signals for a window are computed from that window's prices only, so
    no information leaks across the train/test boundary. The number the
    strategy must be judged on is ``result.oos.sharpe`` — the in-sample
    picks are reported per window purely for inspection.
    """
    prices = prices.dropna()
    oos_parts: list[pd.Series] = []
    windows: list[dict] = []
    for train_sl, test_sl in walk_forward_splits(len(prices), train, test):
        train_px = prices.iloc[train_sl]
        test_px = prices.iloc[test_sl]
        best, _ = grid_search(train_px, signal_fn, param_grid, metric, fee_bps)
        # Warm indicators with trailing history, then keep only test-period
        # returns: context without leakage (the position on test day 1 is
        # decided by data through the last train day).
        warm_px = prices.iloc[train_sl.start : test_sl.stop]
        res = backtest_signals(warm_px, signal_fn(warm_px, **best), fee_bps=fee_bps)
        oos_part = res.returns.loc[test_px.index]
        oos_parts.append(oos_part)
        windows.append(
            {
                "train_end": str(train_px.index[-1]),
                "params": best,
                f"oos_{metric}": _safe_metric(oos_part, metric),
            }
        )
    if not oos_parts:
        return WalkForwardResult(oos_returns=pd.Series(dtype=float), oos=None)
    stitched = pd.concat(oos_parts)
    equity_prices = (1.0 + stitched).cumprod()
    # Re-derive stats on the stitched curve via a constant full position.
    oos_stats = backtest_signals(
        equity_prices, pd.Series(1.0, index=equity_prices.index), fee_bps=0.0
    )
    return WalkForwardResult(oos_returns=stitched, oos=oos_stats, windows=windows)


def _safe_metric(returns: pd.Series, metric: str) -> float:
    if returns.empty:
        return 0.0
    if metric == "sharpe":
        sd = returns.std(ddof=1)
        return float(returns.mean() / sd * math.sqrt(252)) if sd > 0 else 0.0
    equity = float((1.0 + returns).prod())
    return equity - 1.0  # total return fallback


# --- Monte Carlo --------------------------------------------------------------
def monte_carlo_drawdowns(
    returns: pd.Series,
    n_sims: int = 1000,
    block: int = 5,
    seed: int = 42,
) -> dict[str, float]:
    """Block-bootstrap the return series; report drawdown/CAGR percentiles.

    Blocks (default a trading week) preserve short-range autocorrelation
    that single-day resampling destroys. Drawdowns are negative numbers;
    ``dd_p95`` reads "95% of resampled histories drew down no worse than
    this" — the number to size capital against.
    """
    rets = returns.dropna().to_numpy()
    n = len(rets)
    if n < block * 4:
        raise ValueError(f"need at least {block * 4} observations, got {n}")
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=(n_sims, n_blocks))

    drawdowns = np.empty(n_sims)
    cagrs = np.empty(n_sims)
    years = n / 252.0
    for i in range(n_sims):
        path = np.concatenate([rets[s : s + block] for s in starts[i]])[:n]
        equity = np.cumprod(1.0 + path)
        peak = np.maximum.accumulate(equity)
        drawdowns[i] = float(np.min(equity / peak - 1.0))
        cagrs[i] = float(equity[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0

    return {
        "dd_p50": float(np.percentile(drawdowns, 50)),
        "dd_p90": float(np.percentile(drawdowns, 10)),   # 90% no worse than
        "dd_p95": float(np.percentile(drawdowns, 5)),    # 95% no worse than
        "dd_worst": float(drawdowns.min()),
        "cagr_p05": float(np.percentile(cagrs, 5)),
        "cagr_p50": float(np.percentile(cagrs, 50)),
        "n_sims": float(n_sims),
    }


# --- parameter robustness --------------------------------------------------------
def plateau_ratio(metric_by_param: dict, top_k: int = 3) -> float:
    """Mean of the top-k metric values over the best value, in [0, 1].

    Near 1.0: the best parameter sits on a plateau of similar neighbors
    (robust). Much below ~0.7: one spike outperforms everything around
    it — the classic curve-fit signature. Callers with multi-parameter
    grids apply this per axis.
    """
    if not metric_by_param:
        raise ValueError("metric_by_param is empty")
    values = sorted((float(v) for v in metric_by_param.values()), reverse=True)
    best = values[0]
    if best <= 0:
        return 0.0
    top = values[: max(1, min(top_k, len(values)))]
    return max(0.0, min(1.0, (sum(top) / len(top)) / best))


# --- deflated Sharpe ratio ----------------------------------------------------------
def deflated_sharpe_ratio(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    sharpe_std: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """Probability the true Sharpe exceeds 0 after multiple testing.

    Bailey & Lopez de Prado (2014): having tried ``n_trials`` strategy
    variants, the best observed Sharpe is inflated by selection. The
    expected maximum Sharpe under pure noise is subtracted before
    assessing significance; non-normal returns (skew, fat tails) widen
    the error bars. Values near 1.0 mean the edge survives its own
    search process; below ~0.95 the "discovery" is indistinguishable
    from picking the luckiest of N coin-flippers.

    ``sharpe`` is annualized; it is de-annualized internally. ``n_obs``
    is the number of return observations backing the estimate.
    """
    if n_trials < 1 or n_obs < 3:
        raise ValueError("need n_trials >= 1 and n_obs >= 3")
    from scipy.stats import norm

    sr = sharpe / math.sqrt(periods_per_year)  # per-period Sharpe
    # Expected max per-period Sharpe of n_trials pure-noise strategies.
    std0 = sharpe_std if sharpe_std is not None else math.sqrt(1.0 / (n_obs - 1))
    if n_trials == 1:
        sr0 = 0.0
    else:
        z1 = norm.ppf(1.0 - 1.0 / n_trials)
        z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
        sr0 = std0 * ((1.0 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2)
    denom = 1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * sr * sr
    if denom <= 0:
        return 0.0
    z = (sr - sr0) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return float(norm.cdf(z))
