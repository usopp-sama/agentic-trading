"""Position sizing and risk helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def kelly_fraction(win_prob: float, win_loss_ratio: float) -> float:
    """Kelly criterion for a bet with asymmetric payoff.

    Parameters
    ----------
    win_prob:
        Probability of a winning outcome, in ``[0, 1]``.
    win_loss_ratio:
        Ratio of the size of a win to the size of a loss (b).

    Returns the fraction of capital to risk. Can be negative (don't bet).
    """
    if not 0.0 <= win_prob <= 1.0:
        raise ValueError("win_prob must be in [0, 1]")
    if win_loss_ratio <= 0:
        raise ValueError("win_loss_ratio must be positive")
    loss_prob = 1.0 - win_prob
    return win_prob - loss_prob / win_loss_ratio


def kelly_from_returns(returns: pd.Series) -> float:
    """Continuous Kelly fraction from a return series: mean / variance."""
    r = returns.dropna()
    var = r.var(ddof=1)
    if var == 0 or np.isnan(var):
        return 0.0
    return float(r.mean() / var)


def fractional_kelly(full_kelly: float, fraction: float = 0.5) -> float:
    """Scale a Kelly fraction down (half-Kelly is a common, safer choice)."""
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    return full_kelly * fraction


def position_size(
    capital: float,
    fraction: float,
    price: float,
    max_fraction: float = 0.25,
) -> int:
    """Convert a capital fraction into a whole-share position size.

    The fraction is clamped to ``[0, max_fraction]`` so a single position
    can never exceed a risk cap, regardless of an aggressive Kelly output.
    """
    if capital < 0 or price <= 0:
        raise ValueError("capital must be >= 0 and price > 0")
    clamped = float(np.clip(fraction, 0.0, max_fraction))
    return int((capital * clamped) // price)
