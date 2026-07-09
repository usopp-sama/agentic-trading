"""Event, sentiment, seasonal, and volatility-overlay strategies.

These exploit non-price-trend effects. ``NewsSentimentMomentum`` consumes the
existing NLP sentiment via an injected provider (mirroring ``set_fundamentals``
on the factor sleeves); the others are price/calendar driven. All ship
``status="shadow"``.

References:
- Bernard & Thomas (1989) — post-earnings-announcement drift (PEAD).
- Tetlock (2007) — media pessimism predicts returns (news sentiment).
- Ariel (1987) — the turn-of-the-month return effect.
- Moreira & Muir (2017) — volatility-managed portfolios.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import indicators
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import Strategy


class PostEarningsDrift(Strategy):
    """Post-earnings-announcement drift — Bernard & Thomas (1989).

    Prices under-react to earnings surprises and keep drifting in the surprise
    direction for weeks. Without an earnings calendar wired in, this uses a
    *price proxy* for the announcement: an abnormally large gap (``gap_z`` sigma
    of recent daily returns) on elevated volume marks a likely earnings/news
    surprise. It then rides the drift in the gap's direction for ``drift_days``,
    decaying conviction over the window. Documented limitation: a real earnings
    date + standardized-unexpected-earnings (SUE) feed would sharpen this; the
    proxy is acceptable for paper evaluation.
    """

    id = "pead_drift"
    style = "momentum"

    def __init__(
        self,
        ret_window: int = 60,
        gap_z: float = 2.5,
        vol_window: int = 20,
        vol_mult: float = 1.5,
        drift_days: int = 10,
    ) -> None:
        self.ret_window, self.gap_z = ret_window, gap_z
        self.vol_window, self.vol_mult = vol_window, vol_mult
        self.drift_days = drift_days
        self.min_bars = ret_window + drift_days + 2

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        close = df["close"]
        rets = close.pct_change()
        recent = rets.tail(self.ret_window)
        sigma = float(recent.std(ddof=0))
        if not np.isfinite(sigma) or sigma <= 0:
            return None
        vol = df["volume"]
        vol_ma = float(vol.tail(self.vol_window).mean())

        # Find the most recent abnormal-gap day within the drift window.
        window = rets.tail(self.drift_days)
        event_idx, event_ret = None, 0.0
        for offset, (_, r) in enumerate(window.items()):
            if not np.isfinite(r):
                continue
            pos = len(df) - len(window) + offset
            v = float(vol.iloc[pos]) if pos < len(vol) else 0.0
            if abs(r) >= self.gap_z * sigma and vol_ma > 0 and v >= self.vol_mult * vol_ma:
                event_idx, event_ret = offset, float(r)
        if event_idx is None:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, gap=None)
        # Decay conviction with days since the event.
        days_since = len(window) - 1 - event_idx
        decay = max(0.0, 1.0 - days_since / self.drift_days)
        conv = min(1.0, 0.4 + 0.4 * decay)
        feats = {"gap_ret": round(event_ret, 4), "days_since": days_since,
                 "gap_sigma": round(abs(event_ret) / sigma, 2)}
        if event_ret > 0:
            return self._signal(symbol, Stance.BUY, conv, **feats)
        return self._signal(symbol, Stance.SELL, conv, **feats)


class NewsSentimentMomentum(Strategy):
    """News-sentiment momentum — Tetlock (2007).

    Trades the drift that follows a shift in news tone. Reads the rolling mean
    sentiment for the symbol from an injected provider (the NLP service's
    ``recent_sentiment``): strongly positive recent coverage with a confirming
    uptrend is a BUY; strongly negative coverage in a downtrend is a SELL.
    Requires a minimum article count so a single headline cannot move it.
    """

    id = "news_sentiment"
    style = "momentum"

    def __init__(
        self,
        buy_score: float = 0.25,
        sell_score: float = -0.25,
        min_count: int = 3,
        hours: int = 72,
        trend_window: int = 20,
    ) -> None:
        self.buy_score, self.sell_score = buy_score, sell_score
        self.min_count, self.hours = min_count, hours
        self.trend_window = trend_window
        self.min_bars = trend_window + 2
        self._sentiment = None

    def set_sentiment(self, provider) -> None:
        """Wire a callable ``(symbol, hours) -> {mean_score, count, label}``."""
        self._sentiment = provider

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if self._sentiment is None or len(df) < self.min_bars:
            return None
        try:
            snap = self._sentiment(symbol, self.hours) or {}
        except Exception:  # noqa: BLE001 - never let a provider error kill the cycle
            return None
        count = int(snap.get("count", 0))
        score = float(snap.get("mean_score", 0.0))
        if count < self.min_count:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, sent=score, n=count)
        close = df["close"]
        sma = float(indicators.sma(close, self.trend_window).iloc[-1])
        last = float(close.iloc[-1])
        uptrend = np.isfinite(sma) and last >= sma
        feats = {"sent": round(score, 3), "n": count, "uptrend": bool(uptrend)}
        if score >= self.buy_score and uptrend:
            return self._signal(symbol, Stance.BUY, min(1.0, 0.4 + score), **feats)
        if score <= self.sell_score and not uptrend:
            return self._signal(symbol, Stance.SELL, min(1.0, 0.4 + abs(score)), **feats)
        return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)


class TurnOfMonth(Strategy):
    """Turn-of-the-month seasonality — Ariel (1987).

    Equity returns cluster around the turn of the month (the last trading day
    plus the first few of the next). Goes BUY during that window and flat
    otherwise. Uses the bar's own date, so it works on any daily series; the
    signal flips to NEUTRAL outside the window, flattening the seasonal holding.
    """

    id = "turn_of_month"
    style = "other"  # calendar effect; not a trend/MR style
    min_bars = 5

    def __init__(self, days_before: int = 1, days_after: int = 3) -> None:
        self.days_before, self.days_after = days_before, days_after

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if df.empty:
            return None
        ts = df.index[-1]
        try:
            day = ts.day
            days_in_month = ts.days_in_month
        except AttributeError:
            ts = pd.Timestamp(ts)
            day, days_in_month = ts.day, ts.days_in_month
        in_window = (day <= self.days_after) or (day > days_in_month - self.days_before)
        feats = {"dom": int(day), "window": bool(in_window)}
        if in_window:
            return self._signal(symbol, Stance.BUY, 0.5, **feats)
        return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)


class VolatilityTarget(Strategy):
    """Volatility-managed exposure overlay — Moreira & Muir (2017).

    Scales long exposure inversely to recent realized volatility: size up in
    calm uptrends and de-risk when volatility spikes (the empirical finding that
    volatility-managed portfolios raise Sharpe). Conviction = clamp(target_vol /
    realized_vol) while price is above its trend SMA; NEUTRAL below trend or when
    realized vol blows past ``max_vol``. Intended as an overlay sleeve.
    """

    id = "vol_target"
    style = "other"

    def __init__(
        self,
        target_vol: float = 0.15,
        max_vol: float = 0.60,
        vol_window: int = 20,
        trend_window: int = 100,
    ) -> None:
        self.target_vol, self.max_vol = target_vol, max_vol
        self.vol_window, self.trend_window = vol_window, trend_window
        self.min_bars = trend_window + 5

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        close = df["close"]
        rv = indicators.annualized_volatility(close.tail(self.vol_window))
        sma = float(indicators.sma(close, self.trend_window).iloc[-1])
        last = float(close.iloc[-1])
        if not np.isfinite(rv) or rv <= 0 or not np.isfinite(sma):
            return None
        feats = {"realized_vol": round(rv, 3), "target_vol": self.target_vol,
                 "uptrend": bool(last >= sma)}
        if last < sma or rv >= self.max_vol:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)
        conv = max(0.0, min(1.0, self.target_vol / rv))
        return self._signal(symbol, Stance.BUY, conv, **feats)
