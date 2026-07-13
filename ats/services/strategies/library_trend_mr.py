"""Trend / momentum and mean-reversion strategies (academically grounded).

Each class subclasses ``Strategy`` (per-symbol) or ``UniverseStrategy``
(cross-sectional) and carries its primary citation in the docstring. These ship
as ``status="shadow"`` (see reference.py) so they log signals and accrue a paper
track record without taking capital until a walk-forward backtest clears them.

References:
- Jegadeesh & Titman (1993) — cross-sectional momentum.
- George & Hwang (2004) — the 52-week-high momentum anomaly.
- Antonacci (2014) — dual (absolute + relative) momentum.
- Appel (MACD); Wilder (1978) ADX/DMI — classic trend confirmation.
- Lehmann (1990); Jegadeesh (1990) — short-horizon reversal.
- Keltner channels with an Ornstein-Uhlenbeck-style z-score for reversion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import indicators
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import Strategy, UniverseStrategy

# Non-equity instruments a cross-sectional equity model must never rank.
_NON_EQUITY = frozenset({"SILVERBEES.NS", "GOLDBEES.NS", "NIFTYBEES.NS"})


def _is_equity(symbol: str) -> bool:
    return not symbol.startswith("^") and "=" not in symbol and symbol not in _NON_EQUITY


# --- Trend / momentum --------------------------------------------------------
class CrossSectionalMomentum(UniverseStrategy):
    """Cross-sectional 12-1 momentum — Jegadeesh & Titman (1993).

    Ranks the equity universe by its formation-period return (default 252 bars)
    excluding the most recent ``skip`` bars (the 1-month short-term reversal),
    then BUYs the top ``decile`` fraction and flattens (SELL, long-only) the
    bottom fraction. Rebalances roughly monthly so the sleeve does not churn on
    every bar. Conviction scales with rank distance from the median.
    """

    id = "xs_momentum"
    style = "momentum"

    def __init__(
        self,
        formation: int = 252,
        skip: int = 21,
        decile: float = 0.2,
        rebalance_days: int = 21,
        min_names: int = 5,
    ) -> None:
        self.formation, self.skip = formation, skip
        self.decile = decile
        self.rebalance_days = rebalance_days
        self.min_names = min_names
        self.min_bars = formation + skip + 1
        self._last_rebalance = None
        self._long: set[str] = set()

    def evaluate_universe(self, history: dict[str, pd.DataFrame]) -> list[SignalModel]:
        if not history:
            return []
        day = max(df.index[-1] for df in history.values()).date()
        if (
            self._last_rebalance is not None
            and (day - self._last_rebalance).days < self.rebalance_days
        ):
            return []

        mom: dict[str, float] = {}
        for sym, df in history.items():
            if not _is_equity(sym) or len(df) < self.min_bars:
                continue
            close = df["close"]
            recent = float(close.iloc[-(self.skip + 1)])
            past = float(close.iloc[-(self.formation + self.skip + 1)])
            if past > 0 and np.isfinite(recent) and np.isfinite(past):
                mom[sym] = recent / past - 1.0
        if len(mom) < self.min_names:
            return []

        ranked = pd.Series(mom).sort_values(ascending=False)
        n_side = max(1, int(round(len(ranked) * self.decile)))
        winners = list(ranked.head(n_side).index)
        losers = list(ranked.tail(n_side).index)

        signals: list[SignalModel] = []
        for i, sym in enumerate(winners):
            conv = 0.4 + 0.4 * (1.0 - i / max(1, n_side))
            signals.append(self._signal(sym, Stance.BUY, conv,
                                         mom=round(mom[sym], 4), rank=i + 1,
                                         rebalance=day.isoformat()))
        for sym in losers:
            # Long-only: the short leg only flattens an existing holding.
            signals.append(self._signal(sym, Stance.SELL, 0.5,
                                         mom=round(mom[sym], 4), rebalance=day.isoformat()))
        # Names that left the long basket get flattened.
        for sym in sorted(self._long - set(winners)):
            if sym not in losers:
                signals.append(self._signal(sym, Stance.NEUTRAL, 0.0, rebalance=day.isoformat()))
        self._long = set(winners)
        self._last_rebalance = day
        return signals


class FiftyTwoWeekHigh(Strategy):
    """52-week-high momentum — George & Hwang (2004).

    The ratio of the current price to its trailing 252-bar high ("nearness")
    predicts future returns better than past return itself: stocks pressing
    their 52-week high tend to keep winning. BUY when nearness >= ``buy_near``
    in an uptrend; flag SELL when the price has fallen far below the high
    (``sell_near``) while below trend. Conviction scales with nearness.
    """

    id = "high_52w"
    style = "momentum"

    def __init__(
        self,
        lookback: int = 252,
        buy_near: float = 0.95,
        sell_near: float = 0.75,
        trend_window: int = 200,
    ) -> None:
        self.lookback = lookback
        self.buy_near, self.sell_near = buy_near, sell_near
        self.trend_window = trend_window
        self.min_bars = lookback + 1

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        close = df["close"]
        high_52w = float(close.tail(self.lookback).max())
        last = float(close.iloc[-1])
        if high_52w <= 0 or np.isnan(last):
            return None
        nearness = last / high_52w
        trend_sma = float(indicators.sma(close, self.trend_window).iloc[-1])
        uptrend = np.isfinite(trend_sma) and last >= trend_sma
        feats = {"nearness": round(nearness, 4), "high_52w": round(high_52w, 2),
                 "uptrend": bool(uptrend)}
        if nearness >= self.buy_near and uptrend:
            conv = min(1.0, 0.4 + 4.0 * (nearness - self.buy_near))
            return self._signal(symbol, Stance.BUY, conv, **feats)
        if nearness <= self.sell_near and not uptrend:
            return self._signal(symbol, Stance.SELL, min(1.0, self.sell_near - nearness + 0.4), **feats)
        return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)


class DualMomentum(UniverseStrategy):
    """Dual momentum — Antonacci (2014).

    Combines *relative* momentum (own the strongest assets) with an *absolute*
    momentum filter (only if that asset's own trailing return is positive,
    otherwise go to cash). Ranks the universe by ``lookback`` return, BUYs the
    top ``top_n`` whose absolute return clears ``abs_floor``, and flattens
    everything else. The absolute filter is what sidesteps bear markets.
    """

    id = "dual_momentum"
    style = "momentum"

    def __init__(
        self,
        lookback: int = 252,
        top_n: int = 5,
        abs_floor: float = 0.0,
        rebalance_days: int = 21,
    ) -> None:
        self.lookback, self.top_n = lookback, top_n
        self.abs_floor = abs_floor
        self.rebalance_days = rebalance_days
        self.min_bars = lookback + 1
        self._last_rebalance = None
        self._held: set[str] = set()

    def evaluate_universe(self, history: dict[str, pd.DataFrame]) -> list[SignalModel]:
        if not history:
            return []
        day = max(df.index[-1] for df in history.values()).date()
        if (
            self._last_rebalance is not None
            and (day - self._last_rebalance).days < self.rebalance_days
        ):
            return []

        ret: dict[str, float] = {}
        for sym, df in history.items():
            if not _is_equity(sym) or len(df) < self.min_bars:
                continue
            close = df["close"]
            past = float(close.iloc[-self.lookback])
            last = float(close.iloc[-1])
            if past > 0 and np.isfinite(last):
                ret[sym] = last / past - 1.0
        if not ret:
            return []

        ranked = pd.Series(ret).sort_values(ascending=False)
        # Relative winners that also pass the absolute floor.
        chosen = [s for s in ranked.head(self.top_n).index if ret[s] > self.abs_floor]

        signals: list[SignalModel] = []
        for i, sym in enumerate(chosen):
            conv = 0.45 + 0.4 * (1.0 - i / max(1, self.top_n))
            signals.append(self._signal(sym, Stance.BUY, conv,
                                         ret=round(ret[sym], 4), rank=i + 1,
                                         rebalance=day.isoformat()))
        for sym in sorted(self._held - set(chosen)):
            signals.append(self._signal(sym, Stance.NEUTRAL, 0.0, rebalance=day.isoformat()))
        self._held = set(chosen)
        self._last_rebalance = day
        return signals


class MacdAdxTrend(Strategy):
    """MACD trend with an ADX/DMI confirmation filter — Appel; Wilder (1978).

    A MACD line / signal cross gives direction; ADX gates it so signals fire
    only when a trend is actually present (ADX > ``adx_min``), and +DI/-DI must
    agree with the cross. In flat tape (low ADX) the strategy stays NEUTRAL,
    which is the whole point of the filter — MACD alone whipsaws in chop.
    """

    id = "macd_adx_trend"
    style = "trend"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        adx_window: int = 14,
        adx_min: float = 20.0,
    ) -> None:
        self.fast, self.slow, self.signal = fast, slow, signal
        self.adx_window, self.adx_min = adx_window, adx_min
        self.min_bars = slow + signal + adx_window + 5

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        macd = indicators.macd(df["close"], self.fast, self.slow, self.signal)
        dmi = indicators.adx(df, self.adx_window)
        hist = float(macd["hist"].iloc[-1])
        adx_now = float(dmi["adx"].iloc[-1])
        plus_di = float(dmi["plus_di"].iloc[-1])
        minus_di = float(dmi["minus_di"].iloc[-1])
        if any(np.isnan(v) for v in (hist, adx_now, plus_di, minus_di)):
            return None
        feats = {"macd_hist": round(hist, 4), "adx": round(adx_now, 1),
                 "plus_di": round(plus_di, 1), "minus_di": round(minus_di, 1)}
        if adx_now < self.adx_min:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)
        strength = min(1.0, (adx_now - self.adx_min) / 30.0 + 0.4)
        if hist > 0 and plus_di > minus_di:
            return self._signal(symbol, Stance.BUY, strength, **feats)
        if hist < 0 and minus_di > plus_di:
            return self._signal(symbol, Stance.SELL, strength, **feats)
        return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)


# --- Mean reversion ----------------------------------------------------------
class ShortTermReversal(UniverseStrategy):
    """Short-horizon (1-week) reversal — Lehmann (1990) / Jegadeesh (1990).

    Recent extreme moves tend to partially reverse over the following days.
    Ranks the universe by trailing ``lookback``-bar return and BUYs the biggest
    losers (expecting a bounce), flagging the biggest winners as SELL
    (long-only, so this only flattens). Evaluated each cycle (weekly horizon).
    """

    id = "st_reversal"
    style = "mean_reversion"

    def __init__(self, lookback: int = 5, decile: float = 0.2, min_names: int = 5,
                 adx_window: int = 14, adx_max: float = 25.0) -> None:
        self.lookback, self.decile = lookback, decile
        self.min_names = min_names
        # E5 trend filter: don't buy a loser that is in a *confirmed* strong
        # downtrend (a falling knife) — reversion's classic failure mode. adx_max
        # <= 0 disables the filter.
        self.adx_window, self.adx_max = adx_window, adx_max
        self.min_bars = lookback + 2

    def _adverse_downtrend(self, df: pd.DataFrame) -> bool:
        """True when the name is trending down with conviction: ADX above the
        threshold AND -DI over +DI. Buying its dip is catching a falling knife.
        Needs enough bars for ADX; too-short history reads as 'no trend' (safe)."""
        if self.adx_max <= 0 or len(df) < self.adx_window + 2:
            return False
        try:
            a = indicators.adx(df, self.adx_window)
            adx_now = float(a["adx"].iloc[-1])
            plus_di = float(a["plus_di"].iloc[-1])
            minus_di = float(a["minus_di"].iloc[-1])
        except Exception:  # noqa: BLE001 - a bad frame must not abort the sleeve
            return False
        return bool(np.isfinite(adx_now) and adx_now > self.adx_max and minus_di > plus_di)

    def evaluate_universe(self, history: dict[str, pd.DataFrame]) -> list[SignalModel]:
        ret: dict[str, float] = {}
        for sym, df in history.items():
            if not _is_equity(sym) or len(df) < self.min_bars:
                continue
            close = df["close"]
            past = float(close.iloc[-(self.lookback + 1)])
            last = float(close.iloc[-1])
            if past > 0 and np.isfinite(last):
                ret[sym] = last / past - 1.0
        if len(ret) < self.min_names:
            return []
        ranked = pd.Series(ret).sort_values()  # ascending: losers first
        n_side = max(1, int(round(len(ranked) * self.decile)))
        losers = list(ranked.head(n_side).index)
        winners = list(ranked.tail(n_side).index)
        signals: list[SignalModel] = []
        for sym in losers:
            # Skip the bounce trade when the loser is in a confirmed downtrend.
            if self._adverse_downtrend(history[sym]):
                continue
            conv = min(1.0, 0.4 + 2.0 * abs(ret[sym]))
            signals.append(self._signal(sym, Stance.BUY, conv, ret=round(ret[sym], 4)))
        for sym in winners:
            signals.append(self._signal(sym, Stance.SELL, 0.5, ret=round(ret[sym], 4)))
        return signals


class OuKeltnerReversion(Strategy):
    """Keltner-channel z-score mean reversion (Ornstein-Uhlenbeck intuition).

    Models price as mean-reverting around an EMA midline with ATR-scaled bands.
    The distance from the mid in band units is a volatility-normalized z-score:
    BUY when price is stretched below the lower band (``-z_entry``) and SELL
    when stretched above the upper band (``+z_entry``); both decay to NEUTRAL
    inside ``z_exit``. An ADX gate avoids fading a powerful trend.
    """

    id = "ou_keltner"
    style = "mean_reversion"

    def __init__(
        self,
        ema_window: int = 20,
        atr_window: int = 10,
        mult: float = 2.0,
        z_entry: float = 1.0,
        z_exit: float = 0.3,
        adx_window: int = 14,
        adx_max: float = 35.0,
    ) -> None:
        self.ema_window, self.atr_window, self.mult = ema_window, atr_window, mult
        self.z_entry, self.z_exit = z_entry, z_exit
        self.adx_window, self.adx_max = adx_window, adx_max
        self.min_bars = max(ema_window, atr_window, adx_window) + 10

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        kc = indicators.keltner_channel(df, self.ema_window, self.atr_window, self.mult)
        mid = float(kc["mid"].iloc[-1])
        upper = float(kc["upper"].iloc[-1])
        last = float(df["close"].iloc[-1])
        half_width = (upper - mid)
        if not np.isfinite(mid) or half_width <= 0:
            return None
        z = (last - mid) / half_width
        adx_now = float(indicators.adx(df, self.adx_window)["adx"].iloc[-1])
        feats = {"z": round(z, 3), "adx": round(adx_now, 1) if np.isfinite(adx_now) else None}
        # Don't fade a strong trend.
        if np.isfinite(adx_now) and adx_now > self.adx_max:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)
        if z <= -self.z_entry:
            return self._signal(symbol, Stance.BUY, min(1.0, 0.4 + 0.4 * (-z - self.z_entry)), **feats)
        if z >= self.z_entry:
            return self._signal(symbol, Stance.SELL, min(1.0, 0.4 + 0.4 * (z - self.z_entry)), **feats)
        if abs(z) <= self.z_exit:
            return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)
        return self._signal(symbol, Stance.NEUTRAL, 0.0, **feats)
