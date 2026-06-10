"""Market regime detection (roadmap Part 7.12).

Classifies a reference price series along two independent axes:

- **trend**: ``up`` / ``down`` / ``range`` — price vs its long moving
  average, with a neutral band so small oscillations around the average
  read as "range" instead of flip-flopping.
- **vol**: ``calm`` / ``normal`` / ``crisis`` — current realized
  volatility ranked against its own trailing distribution.

The two axes are consumed by different layers on purpose: strategy
conviction tilts use only the trend axis (does this style fit the
market?), while the risk layer uses only the vol axis (how much gross
exposure is prudent?). Keeping them separate avoids double-dampening.

Pure functions of a close series, so trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TREND_UP = "up"
TREND_DOWN = "down"
TREND_RANGE = "range"

VOL_CALM = "calm"
VOL_NORMAL = "normal"
VOL_CRISIS = "crisis"

# Dampen-only conviction multipliers: a style that fits the current trend
# regime keeps full conviction; a mismatched style is reduced, never boosted.
_STYLE_TILT: dict[str, dict[str, float]] = {
    TREND_UP: {"trend": 1.0, "momentum": 1.0, "mean_reversion": 0.7},
    TREND_DOWN: {"trend": 1.0, "momentum": 1.0, "mean_reversion": 0.7},
    TREND_RANGE: {"trend": 0.7, "momentum": 0.7, "mean_reversion": 1.0},
}


@dataclass(frozen=True)
class RegimeState:
    trend: str = TREND_RANGE
    vol: str = VOL_NORMAL

    @property
    def label(self) -> str:
        return f"{self.trend}/{self.vol}"


def classify_trend(
    close: pd.Series, ma_window: int = 200, band: float = 0.02
) -> str:
    """Price vs long MA with a +/-``band`` neutral zone."""
    if len(close) < ma_window:
        return TREND_RANGE
    ma = float(close.rolling(ma_window, min_periods=ma_window).mean().iloc[-1])
    last = float(close.iloc[-1])
    if not np.isfinite(ma) or ma <= 0:
        return TREND_RANGE
    if last > ma * (1.0 + band):
        return TREND_UP
    if last < ma * (1.0 - band):
        return TREND_DOWN
    return TREND_RANGE


def classify_vol(
    close: pd.Series,
    vol_window: int = 20,
    lookback: int = 252,
    calm_pctile: float = 0.30,
    crisis_pctile: float = 0.90,
) -> str:
    """Current realized vol ranked against its own trailing distribution."""
    log_ret = np.log(close / close.shift(1))
    realized = log_ret.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    history = realized.dropna().tail(lookback)
    # Need enough history for percentiles to mean anything.
    if len(history) < vol_window * 3:
        return VOL_NORMAL
    current = float(history.iloc[-1])
    calm_level = float(history.quantile(calm_pctile))
    crisis_level = float(history.quantile(crisis_pctile))
    if current >= crisis_level:
        return VOL_CRISIS
    if current <= calm_level:
        return VOL_CALM
    return VOL_NORMAL


def classify(
    close: pd.Series,
    ma_window: int = 200,
    band: float = 0.02,
    vol_window: int = 20,
    lookback: int = 252,
) -> RegimeState:
    """Full regime state; degrades to the neutral default on short history."""
    return RegimeState(
        trend=classify_trend(close, ma_window=ma_window, band=band),
        vol=classify_vol(close, vol_window=vol_window, lookback=lookback),
    )


def tilt_for(style: str, regime: RegimeState) -> float:
    """Conviction multiplier in (0, 1] for a strategy style in a regime.

    Uses only the trend axis; crisis-vol exposure cuts are the risk
    layer's job (see RiskService), not the signal layer's.
    """
    return _STYLE_TILT.get(regime.trend, {}).get(style, 1.0)
