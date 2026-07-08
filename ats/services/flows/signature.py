"""Pump-signature scoring (hypothesis #1, the defensive one).

Pure functions: OHLCV (+ optional delivery-percentage series) in, a scored
signature out. The signature an operator-driven pump leaves in public data:

- **price leg** — sharp multi-session rise (default > +10% over 5 sessions);
- **volume leg** — volume far above its own recent distribution
  (z-score > 3 on any of the last 5 sessions);
- **delivery leg** — the tell: delivery percentage *falling* vs its 20-day
  mean while price and volume surge means the paper is churning intraday,
  not being accumulated. Rising delivery instead suggests genuine
  accumulation and CLEARS the signature.

Retail entering mid-pump is the exit liquidity; the veto refuses to be it.
Without delivery data the signature still triggers on price+volume but at
reduced confidence — shadow mode exists to measure exactly this.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Component weights: price+volume alone leave the signature unconfirmed.
_SCORE_UNCONFIRMED = 0.7
_SCORE_CONFIRMED = 1.0


@dataclass(frozen=True)
class PumpSignature:
    symbol: str
    triggered: bool
    score: float                 # 0 = clean; 0.7 unconfirmed; 1.0 delivery-confirmed
    px_chg_5d: float | None = None
    vol_z_max_5d: float | None = None
    delivery_pct: float | None = None
    delivery_mean_20d: float | None = None
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "triggered": self.triggered,
            "score": self.score,
            "px_chg_5d": self.px_chg_5d,
            "vol_z_max_5d": self.vol_z_max_5d,
            "delivery_pct": self.delivery_pct,
            "delivery_mean_20d": self.delivery_mean_20d,
            "reasons": list(self.reasons),
        }


def pump_signature(
    symbol: str,
    df: pd.DataFrame,
    delivery: pd.Series | None = None,
    *,
    px_chg_5d: float = 0.10,
    vol_z: float = 3.0,
    delivery_drop: float = 0.10,
    vol_window: int = 20,
) -> PumpSignature:
    """Score one symbol's current pump signature from its daily bars.

    ``delivery`` is a Series of delivery percentages (0-100) indexed like the
    bars, and may be None/short — the delivery leg then reports "unconfirmed"
    rather than blocking the check.
    """
    need = vol_window + 6
    if df is None or len(df) < need:
        return PumpSignature(symbol, triggered=False, score=0.0,
                             reasons=["insufficient_history"])

    close = df["close"].astype(float)
    vol = df["volume"].astype(float)

    chg = float(close.iloc[-1] / close.iloc[-6] - 1.0)
    px_leg = chg > px_chg_5d

    # Volume z per bar vs the trailing window (shifted: today's spike is
    # measured against the *prior* 20 days, not itself).
    mean = vol.rolling(vol_window, min_periods=vol_window).mean().shift(1)
    std = vol.rolling(vol_window, min_periods=vol_window).std(ddof=0).shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (vol - mean) / std
    z_recent = z.iloc[-5:].replace([np.inf, -np.inf], np.nan).dropna()
    z_max = float(z_recent.max()) if not z_recent.empty else None
    vol_leg = z_max is not None and z_max > vol_z

    reasons: list[str] = []
    if px_leg:
        reasons.append(f"px_5d {chg:+.1%}")
    if vol_leg:
        reasons.append(f"vol_z {z_max:.1f}")

    if not (px_leg and vol_leg):
        return PumpSignature(symbol, triggered=False, score=0.0,
                             px_chg_5d=round(chg, 4), vol_z_max_5d=z_max,
                             reasons=reasons)

    # Delivery leg: confirms (falling), clears (rising), or stays unknown.
    dlv_last = dlv_mean = None
    if delivery is not None:
        dlv = pd.Series(delivery).astype(float).dropna()
        if len(dlv) >= vol_window:
            dlv_last = float(dlv.iloc[-1])
            dlv_mean = float(dlv.iloc[-vol_window:].mean())
            if dlv_last < dlv_mean * (1.0 - delivery_drop):
                reasons.append(f"delivery falling {dlv_last:.0f}%<{dlv_mean:.0f}%")
                return PumpSignature(symbol, True, _SCORE_CONFIRMED,
                                     round(chg, 4), z_max, dlv_last, dlv_mean, reasons)
            # Delivery holding/rising on a surge = accumulation, not churn.
            reasons.append(f"delivery holding {dlv_last:.0f}%")
            return PumpSignature(symbol, False, 0.0,
                                 round(chg, 4), z_max, dlv_last, dlv_mean, reasons)

    reasons.append("delivery_unconfirmed")
    return PumpSignature(symbol, True, _SCORE_UNCONFIRMED,
                         round(chg, 4), z_max, dlv_last, dlv_mean, reasons)
