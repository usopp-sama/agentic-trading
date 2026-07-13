"""Concrete strategies built on the ``quant`` analytics toolkit."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import indicators
from quant.analysis.levels import (
    classic_pivots,
    fibonacci_retracements,
    nearest_level,
)
from quant.analysis.summary import technical_summary
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import Strategy, UniverseStrategy


class SmaCrossover(Strategy):
    id = "sma_crossover"
    style = "trend"
    min_bars = 60

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        self.fast, self.slow = fast, slow

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.slow + 1:
            return None
        close = df["close"]
        fast = indicators.sma(close, self.fast).iloc[-1]
        slow = indicators.sma(close, self.slow).iloc[-1]
        if np.isnan(fast) or np.isnan(slow) or slow == 0:
            return None
        gap = float((fast - slow) / slow)
        if gap > 0:
            return self._signal(symbol, Stance.BUY, min(1.0, gap * 20), gap=round(gap, 4))
        if gap < 0:
            return self._signal(symbol, Stance.SELL, min(1.0, -gap * 20), gap=round(gap, 4))
        return self._signal(symbol, Stance.NEUTRAL, 0.0, gap=0.0)

    # --- opt-in parameter-robustness probe (E2 plateau check) --------------
    def param_grid(self) -> dict:
        return {"fast": [10, 15, 20, 25, 30], "slow": [40, 50, 60]}

    def signal_series(self, prices: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
        """Long-only target positions over the whole series (fast SMA above slow),
        so ``quant.backtest.validation`` can grid-search the parameters and test
        whether the chosen (fast, slow) sits on a robust plateau or a lucky spike."""
        f = indicators.sma(prices, int(fast))
        s = indicators.sma(prices, int(slow))
        return (f > s).astype(float)


class BollingerMeanReversion(Strategy):
    id = "mean_reversion"
    style = "mean_reversion"
    min_bars = 40

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        self.window, self.num_std = window, num_std

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.window + 2:
            return None
        bb = indicators.bollinger_bands(df["close"], self.window, self.num_std)
        pct_b = float(bb["pct_b"].iloc[-1])
        if np.isnan(pct_b):
            return None
        # Below the lower band -> oversold -> buy; above upper -> overbought -> sell.
        if pct_b < 0.0:
            return self._signal(symbol, Stance.BUY, min(1.0, -pct_b), pct_b=round(pct_b, 3))
        if pct_b > 1.0:
            return self._signal(symbol, Stance.SELL, min(1.0, pct_b - 1.0), pct_b=round(pct_b, 3))
        return self._signal(symbol, Stance.NEUTRAL, 0.0, pct_b=round(pct_b, 3))

    # --- opt-in parameter-robustness probe (E2 plateau check) --------------
    def param_grid(self) -> dict:
        return {"window": [10, 15, 20, 25, 30], "num_std": [1.5, 2.0, 2.5]}

    def signal_series(self, prices: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
        """Long-only target positions (long while price is below the lower band,
        i.e. oversold) for the parameter-robustness grid search."""
        bb = indicators.bollinger_bands(prices, int(window), float(num_std))
        return (bb["pct_b"] < 0.0).astype(float)


class VolumeBreakout(Strategy):
    id = "volume_breakout"
    style = "momentum"
    min_bars = 30

    def __init__(self, lookback: int = 20, vol_z: float = 2.0) -> None:
        self.lookback, self.vol_z = lookback, vol_z

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.lookback + 2:
            return None
        close = df["close"]
        vol = df["volume"]
        recent_high = close.iloc[-(self.lookback + 1):-1].max()
        vol_hist = vol.iloc[-(self.lookback + 1):-1]
        mean, std = float(vol_hist.mean()), float(vol_hist.std(ddof=0))
        if std <= 0:
            return None
        z = (float(vol.iloc[-1]) - mean) / std
        breakout = float(close.iloc[-1]) > float(recent_high)
        if z >= self.vol_z and breakout:
            return self._signal(
                symbol, Stance.BUY, min(1.0, z / 5.0), vol_z=round(z, 2), breakout=True
            )
        return self._signal(symbol, Stance.NEUTRAL, 0.0, vol_z=round(z, 2), breakout=breakout)


class DonchianTrend(Strategy):
    """Classic Turtle-style trend following (roadmap Part 7.1).

    Buy a breakout of the prior ``entry_window``-bar high; exit (sell)
    on a close below the prior ``exit_window``-bar low. Conviction grows
    with breakout strength measured in ATR units, so a marginal poke
    above the channel is a weak signal and a decisive thrust is strong.
    """

    id = "donchian_trend"
    style = "trend"

    def __init__(
        self, entry_window: int = 55, exit_window: int = 20, atr_window: int = 14
    ) -> None:
        self.entry_window, self.exit_window = entry_window, exit_window
        self.atr_window = atr_window
        self.min_bars = entry_window + 2

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        entry_upper = float(indicators.donchian(df, self.entry_window)["upper"].iloc[-1])
        exit_lower = float(indicators.donchian(df, self.exit_window)["lower"].iloc[-1])
        atr_now = float(indicators.atr(df, self.atr_window).iloc[-1])
        close = float(df["close"].iloc[-1])
        if any(np.isnan(v) for v in (entry_upper, exit_lower, atr_now)) or atr_now <= 0:
            return None
        if close > entry_upper:
            excess_atr = (close - entry_upper) / atr_now
            return self._signal(
                symbol, Stance.BUY, 0.4 + 0.3 * excess_atr,
                entry_upper=round(entry_upper, 2), atr=round(atr_now, 2),
                excess_atr=round(excess_atr, 2),
            )
        if close < exit_lower:
            depth_atr = (exit_lower - close) / atr_now
            return self._signal(
                symbol, Stance.SELL, 0.4 + 0.3 * depth_atr,
                exit_lower=round(exit_lower, 2), atr=round(atr_now, 2),
                depth_atr=round(depth_atr, 2),
            )
        return self._signal(
            symbol, Stance.NEUTRAL, 0.0,
            entry_upper=round(entry_upper, 2), exit_lower=round(exit_lower, 2),
        )


class Rsi2MeanReversion(Strategy):
    """Connors RSI(2) pullback (roadmap Part 7.3).

    Only buys pullbacks within a long-term uptrend (close above the
    ``trend_window`` SMA) — the filter that keeps this from catching
    falling knives. Deeper oversold readings earn higher conviction;
    an RSI(2) above ``exit_above`` signals the snap-back is done.
    """

    id = "rsi2_reversion"
    style = "mean_reversion"

    def __init__(
        self,
        rsi_window: int = 2,
        buy_below: float = 10.0,
        exit_above: float = 70.0,
        trend_window: int = 200,
    ) -> None:
        self.rsi_window, self.trend_window = rsi_window, trend_window
        self.buy_below, self.exit_above = buy_below, exit_above
        self.min_bars = trend_window + 10

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        close = df["close"]
        trend_sma = float(indicators.sma(close, self.trend_window).iloc[-1])
        rsi_now = float(indicators.rsi(close, self.rsi_window).iloc[-1])
        last = float(close.iloc[-1])
        if np.isnan(trend_sma) or np.isnan(rsi_now):
            return None
        if last <= trend_sma:
            # Below the long-term trend: stand aside no matter how oversold.
            return self._signal(
                symbol, Stance.NEUTRAL, 0.0, rsi2=round(rsi_now, 1), trend_ok=False
            )
        if rsi_now < self.buy_below:
            depth = (self.buy_below - rsi_now) / self.buy_below
            return self._signal(
                symbol, Stance.BUY, 0.5 + 0.5 * depth,
                rsi2=round(rsi_now, 1), trend_ok=True,
            )
        if rsi_now > self.exit_above:
            done = (rsi_now - self.exit_above) / (100.0 - self.exit_above)
            return self._signal(
                symbol, Stance.SELL, min(1.0, done),
                rsi2=round(rsi_now, 1), trend_ok=True,
            )
        return self._signal(
            symbol, Stance.NEUTRAL, 0.0, rsi2=round(rsi_now, 1), trend_ok=True
        )


class TimeSeriesMomentum(Strategy):
    """12-1 time-series momentum (roadmap Parts 7.1/7.2).

    Sign of the trailing ``formation``-bar return, excluding the most
    recent ``skip`` bars (short-term reversal pollutes the signal —
    Jegadeesh & Titman). Conviction is the vol-scaled strength of the
    move, so a quiet steady climb outranks an equal but violent one.
    """

    id = "ts_momentum"
    style = "momentum"

    def __init__(
        self, formation: int = 252, skip: int = 21, min_abs_return: float = 0.05
    ) -> None:
        self.formation, self.skip = formation, skip
        self.min_abs_return = min_abs_return
        self.min_bars = formation + skip + 1

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars:
            return None
        close = df["close"]
        recent = float(close.iloc[-(self.skip + 1)])
        past = float(close.iloc[-(self.formation + self.skip + 1)])
        if past <= 0 or np.isnan(recent) or np.isnan(past):
            return None
        mom = recent / past - 1.0
        ann_vol = indicators.annualized_volatility(close.tail(self.formation))
        strength = abs(mom) / ann_vol if ann_vol and not np.isnan(ann_vol) else abs(mom)
        if mom >= self.min_abs_return:
            return self._signal(
                symbol, Stance.BUY, min(1.0, strength),
                mom_return=round(mom, 4), ann_vol=round(ann_vol, 4),
            )
        if mom <= -self.min_abs_return:
            return self._signal(
                symbol, Stance.SELL, min(1.0, strength),
                mom_return=round(mom, 4), ann_vol=round(ann_vol, 4),
            )
        return self._signal(symbol, Stance.NEUTRAL, 0.0, mom_return=round(mom, 4))


# Economically-linked NSE pairs + the gold/silver ratio (roadmap Part 7.4).
DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("HDFCBANK.NS", "ICICIBANK.NS"),
    ("TCS.NS", "INFY.NS"),
    ("GOLDBEES.NS", "SILVERBEES.NS"),
]


class PairsZScore(UniverseStrategy):
    """Pairs trading on the z-score of the log price ratio (Part 7.4).

    Cointegration-lite: when log(A/B) stretches beyond ``entry_z`` of its
    rolling distribution, buy the cheap leg and flag the rich leg as a
    sell. The book is long-only in v1, so the "short" side only ever
    flattens an existing holding — it never opens a short. Signals decay
    to NEUTRAL once the spread re-enters ``exit_z``.
    """

    id = "pairs_zscore"
    style = "stat_arb"
    long_short = True   # backtest with the short leg intact, not long-only (E1)

    def __init__(
        self,
        pairs: list[tuple[str, str]] | None = None,
        window: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
    ) -> None:
        self.pairs = pairs if pairs is not None else list(DEFAULT_PAIRS)
        self.window, self.entry_z, self.exit_z = window, entry_z, exit_z
        self.min_bars = window + 5

    def symbols(self) -> list[str]:
        return sorted({s for pair in self.pairs for s in pair})

    def evaluate_universe(
        self, history: dict[str, pd.DataFrame]
    ) -> list[SignalModel]:
        signals: list[SignalModel] = []
        for sym_a, sym_b in self.pairs:
            df_a, df_b = history.get(sym_a), history.get(sym_b)
            if df_a is None or df_b is None:
                continue
            closes = pd.concat(
                [df_a["close"].rename("a"), df_b["close"].rename("b")],
                axis=1, join="inner",
            ).dropna()
            if len(closes) < self.min_bars:
                continue
            spread = np.log(closes["a"]) - np.log(closes["b"])
            mean = spread.rolling(self.window, min_periods=self.window).mean()
            std = spread.rolling(self.window, min_periods=self.window).std(ddof=0)
            last_std = float(std.iloc[-1])
            if not np.isfinite(last_std) or last_std <= 0:
                continue
            z = float((spread.iloc[-1] - mean.iloc[-1]) / last_std)
            pair_label = f"{sym_a}/{sym_b}"
            feats = {"pair": pair_label, "zscore": round(z, 2)}
            if z >= self.entry_z:
                # A rich vs B: buy the cheap leg, flatten the rich one.
                conviction = min(1.0, 0.4 + 0.3 * (z - self.entry_z))
                signals.append(self._signal(sym_b, Stance.BUY, conviction, **feats))
                signals.append(self._signal(sym_a, Stance.SELL, conviction, **feats))
            elif z <= -self.entry_z:
                conviction = min(1.0, 0.4 + 0.3 * (-z - self.entry_z))
                signals.append(self._signal(sym_a, Stance.BUY, conviction, **feats))
                signals.append(self._signal(sym_b, Stance.SELL, conviction, **feats))
            elif abs(z) <= self.exit_z:
                signals.append(self._signal(sym_a, Stance.NEUTRAL, 0.0, **feats))
                signals.append(self._signal(sym_b, Stance.NEUTRAL, 0.0, **feats))
        return signals


class FactorComposite(UniverseStrategy):
    """Cross-sectional factor sleeve (roadmap Part 7.10).

    Ranks the equity universe on an equally-weighted composite of
    percentile-ranked factors: 12-1 **momentum** and **low realized
    volatility** from prices, plus **value** (low P/E, low P/B) and
    **quality** (high ROE, low debt/equity) when a fundamentals provider
    is wired in (see ``set_fundamentals``; the FundamentalsService
    injects itself via the StrategyService). Missing data degrades
    gracefully: a factor a symbol lacks simply doesn't enter that
    symbol's average — never treated as zero.

    Holds the top ``top_n`` names, rebalances roughly quarterly, and
    names that drop out of the basket get a NEUTRAL signal so their
    sleeve holding is flattened.

    Indices and commodity/index ETFs are excluded — an equity factor
    model has no business ranking the Nifty against a silver ETF.
    """

    id = "factor_composite"
    style = "factor"  # not in the regime tilt matrix: the slow sleeve is never dampened

    DEFAULT_EXCLUDE = frozenset({"SILVERBEES.NS", "GOLDBEES.NS", "NIFTYBEES.NS"})

    def __init__(
        self,
        top_n: int = 10,
        formation: int = 252,
        skip: int = 21,
        vol_window: int = 60,
        rebalance_calendar_days: int = 90,
        exclude: frozenset[str] | None = None,
    ) -> None:
        self.top_n, self.formation, self.skip = top_n, formation, skip
        self.vol_window = vol_window
        self.rebalance_calendar_days = rebalance_calendar_days
        self.exclude = exclude if exclude is not None else self.DEFAULT_EXCLUDE
        self.min_bars = formation + skip + 1
        self._last_rebalance = None  # date of the last basket build
        self._basket: set[str] = set()
        # Callable returning {symbol: {pe, pb, roe, debt_to_equity, ...}}.
        self._fundamentals = None

    def set_fundamentals(self, provider) -> None:
        """Wire a fundamentals source; value/quality factors activate."""
        self._fundamentals = provider

    def evaluate_universe(
        self, history: dict[str, pd.DataFrame]
    ) -> list[SignalModel]:
        if not history:
            return []
        day = max(df.index[-1] for df in history.values()).date()
        if (
            self._last_rebalance is not None
            and (day - self._last_rebalance).days < self.rebalance_calendar_days
        ):
            return []

        mom: dict[str, float] = {}
        vol: dict[str, float] = {}
        for sym, df in history.items():
            if sym.startswith("^") or sym in self.exclude or len(df) < self.min_bars:
                continue
            close = df["close"]
            recent = float(close.iloc[-(self.skip + 1)])
            past = float(close.iloc[-(self.formation + self.skip + 1)])
            ann_vol = indicators.annualized_volatility(close.tail(self.vol_window))
            if past <= 0 or not np.isfinite(ann_vol) or ann_vol <= 0:
                continue
            mom[sym] = recent / past - 1.0
            vol[sym] = ann_vol
        if not mom:
            return []

        # Percentile ranks in [0, 1], higher = better on each factor.
        factors = pd.DataFrame(index=sorted(mom))
        factors["momentum"] = pd.Series(mom).rank(pct=True)
        factors["low_vol"] = (-pd.Series(vol)).rank(pct=True)
        for name, col in self._fundamental_ranks(list(factors.index)).items():
            factors[name] = col
        composite = factors.mean(axis=1, skipna=True).sort_values(ascending=False)
        top = set(composite.head(self.top_n).index)

        signals: list[SignalModel] = []
        for sym in sorted(top):
            score = float(composite[sym])
            feats = {
                "composite": round(score, 3),
                "mom": round(mom[sym], 4),
                "ann_vol": round(vol[sym], 4),
                "rebalance": day.isoformat(),
            }
            for name in ("value", "quality"):
                if name in factors.columns and pd.notna(factors.at[sym, name]):
                    feats[name] = round(float(factors.at[sym, name]), 3)
            signals.append(self._signal(sym, Stance.BUY, 0.3 + 0.5 * score, **feats))
        for sym in sorted(self._basket - top):
            signals.append(
                self._signal(sym, Stance.NEUTRAL, 0.0, rebalance=day.isoformat())
            )
        self._basket = top
        self._last_rebalance = day
        return signals

    def _fundamental_ranks(self, syms: list[str]) -> dict[str, pd.Series]:
        """Value/quality percentile ranks for symbols with data, or {}."""
        if self._fundamentals is None:
            return {}
        try:
            fund = self._fundamentals() or {}
        except Exception:  # noqa: BLE001 - factor sleeve must survive a bad provider
            return {}

        def _series(field: str, condition=lambda v: True) -> pd.Series:
            vals = {
                s: fund[s][field]
                for s in syms
                if s in fund and fund[s].get(field) is not None and condition(fund[s][field])
            }
            return pd.Series(vals, dtype=float)

        out: dict[str, pd.Series] = {}
        # Value: cheap on earnings and book (negative P/E means losses, skip).
        pe_rank = (-_series("pe", lambda v: v > 0)).rank(pct=True)
        pb_rank = (-_series("pb", lambda v: v > 0)).rank(pct=True)
        value = pd.concat([pe_rank, pb_rank], axis=1).mean(axis=1, skipna=True)
        if not value.empty:
            out["value"] = value
        # Quality: productive equity, conservative balance sheet.
        roe_rank = _series("roe").rank(pct=True)
        de_rank = (-_series("debt_to_equity", lambda v: v >= 0)).rank(pct=True)
        quality = pd.concat([roe_rank, de_rank], axis=1).mean(axis=1, skipna=True)
        if not quality.empty:
            out["quality"] = quality
        return out


# ETF -> underlying price reference for NAV arbitrage (roadmap Parts 1, 7.5).
DEFAULT_ETF_UNDERLYINGS: list[tuple[str, str]] = [
    ("SILVERBEES.NS", "SI=F"),
    ("GOLDBEES.NS", "GC=F"),
]


class NavPremium(UniverseStrategy):
    """ETF NAV premium/discount arbitrage (roadmap Part 7.5) — the plan's
    priority-one strategy and its very first project (SILVERBEES).

    Official iNAV comes from the AMC; as a proxy, the fair ETF/underlying
    price ratio is estimated as the rolling mean of the last ``window``
    ratios (this self-anchors, so slow drifts like USDINR are absorbed).
    Premium = current ratio / fair ratio - 1:

    - premium <= -``entry_discount``  -> BUY the ETF (it's cheap vs NAV)
    - premium >= +``exit_premium``    -> SELL (overpaying; exit/avoid)
    - in between                      -> NEUTRAL

    Only the ETF leg is ever signaled — the underlying is a COMEX price
    feed, not an NSE instrument, and the risk layer vetoes it anyway.
    """

    id = "nav_premium"
    style = "arbitrage"  # outside the regime tilt matrix on purpose

    def __init__(
        self,
        etf_underlyings: list[tuple[str, str]] | None = None,
        window: int = 60,
        entry_discount: float = 0.015,
        exit_premium: float = 0.010,
    ) -> None:
        self.etf_underlyings = (
            etf_underlyings if etf_underlyings is not None else list(DEFAULT_ETF_UNDERLYINGS)
        )
        self.window = window
        self.entry_discount, self.exit_premium = entry_discount, exit_premium
        self.min_bars = window + 5

    def symbols(self) -> list[str]:
        return sorted({s for pair in self.etf_underlyings for s in pair})

    def evaluate_universe(
        self, history: dict[str, pd.DataFrame]
    ) -> list[SignalModel]:
        signals: list[SignalModel] = []
        for etf, underlying in self.etf_underlyings:
            df_e, df_u = history.get(etf), history.get(underlying)
            if df_e is None or df_u is None:
                continue
            closes = pd.concat(
                [df_e["close"].rename("etf"), df_u["close"].rename("und")],
                axis=1, join="inner",
            ).dropna()
            if len(closes) < self.min_bars or (closes["und"] <= 0).any():
                continue
            ratio = closes["etf"] / closes["und"]
            fair = float(ratio.tail(self.window).mean())
            if not np.isfinite(fair) or fair <= 0:
                continue
            premium = float(ratio.iloc[-1] / fair - 1.0)
            feats = {
                "underlying": underlying,
                "premium_pct": round(premium * 100.0, 2),
                "fair_ratio": round(fair, 4),
            }
            if premium <= -self.entry_discount:
                stretch = -premium / self.entry_discount
                signals.append(
                    self._signal(etf, Stance.BUY, min(1.0, 0.4 + 0.3 * (stretch - 1.0)), **feats)
                )
            elif premium >= self.exit_premium:
                stretch = premium / self.exit_premium
                signals.append(
                    self._signal(etf, Stance.SELL, min(1.0, 0.4 + 0.3 * (stretch - 1.0)), **feats)
                )
            else:
                signals.append(self._signal(etf, Stance.NEUTRAL, 0.0, **feats))
        return signals


class TechConfluence(Strategy):
    """Confluence: composite technical summary + level support (QA-8).

    The medium-loop candidate built on the analytics engine. BUY only when the
    12-check ``technical_summary`` is strongly bullish (score ≥ +6) *and* price
    is sitting within ``near_pct`` of a pivot/fib support (trend + momentum
    agreeing at a floor — "buy the dip in an uptrend"). Exit when the summary
    rolls over (score ≤ 0). Shadow until the walk-forward gate promotes it; it
    is registered as a hypothesis so it walks the same lifecycle as everything
    else.
    """

    id = "tech_confluence"
    style = "trend"
    min_bars = 60

    def __init__(self, buy_score: int = 6, near_pct: float = 1.0) -> None:
        self.buy_score, self.near_pct = buy_score, near_pct

    def evaluate(self, symbol: str, df: pd.DataFrame) -> SignalModel | None:
        if len(df) < self.min_bars or "close" not in df.columns:
            return None
        ts = technical_summary(symbol, df)
        price = float(df["close"].iloc[-1])
        # Exit / short-bias when the composite rolls over.
        if ts.score <= 0:
            return self._signal(
                symbol, Stance.SELL, min(1.0, 0.1 + (-ts.score) / 12.0),
                tech_score=ts.score, reason="summary_rolled_over",
            )
        # BUY only at a level with a strongly bullish composite.
        if ts.score >= self.buy_score and all(c in df.columns for c in ("high", "low")):
            prev = df.iloc[-2]
            piv = classic_pivots(float(prev["high"]), float(prev["low"]), float(prev["close"]))
            win = df.tail(252)
            fib = fibonacci_retracements(
                float(win["high"].max()), float(win["low"].min()), "down"
            )
            supports = [lv for lv in (piv.all_levels() + list(fib.values()))
                        if 0 < lv <= price]
            if supports:
                nearest, dist = nearest_level(price, supports)
                if abs(dist) <= self.near_pct:
                    conv = min(1.0, 0.4 + 0.1 * (ts.score - self.buy_score))
                    return self._signal(
                        symbol, Stance.BUY, conv, tech_score=ts.score,
                        support=round(nearest, 2), dist_pct=round(dist, 3),
                    )
        return self._signal(symbol, Stance.NEUTRAL, 0.0, tech_score=ts.score)


def default_strategies() -> list[Strategy]:
    from ats.core.config import get_settings
    from ats.services.strategies.library_events import (
        NewsSentimentMomentum,
        PostEarningsDrift,
        TurnOfMonth,
        VolatilityTarget,
    )
    from ats.services.strategies.library_trend_mr import (
        FiftyTwoWeekHigh,
        MacdAdxTrend,
        OuKeltnerReversion,
    )

    s = get_settings()
    return [
        # Original v1 sleeves (paper).
        SmaCrossover(),
        BollingerMeanReversion(),
        VolumeBreakout(),
        DonchianTrend(),
        Rsi2MeanReversion(),
        TimeSeriesMomentum(),
        # Phase-2 per-symbol additions (shadow until the backtest gate clears).
        FiftyTwoWeekHigh(buy_near=s.high52_buy_near, sell_near=s.high52_sell_near),
        MacdAdxTrend(adx_min=s.macd_adx_min),
        OuKeltnerReversion(
            ema_window=s.ou_keltner_ema, atr_window=s.ou_keltner_atr,
            z_entry=s.ou_keltner_z_entry, z_exit=s.ou_keltner_z_exit,
        ),
        PostEarningsDrift(gap_z=s.pead_gap_z, drift_days=s.pead_drift_days),
        NewsSentimentMomentum(
            buy_score=s.news_sent_buy, sell_score=s.news_sent_sell,
            min_count=s.news_sent_min_count,
        ),
        TurnOfMonth(days_before=s.tom_days_before, days_after=s.tom_days_after),
        VolatilityTarget(target_vol=s.vol_target_annual, max_vol=s.vol_target_max),
        # QA-8: analytics-engine confluence sleeve (shadow until the gate clears).
        TechConfluence(buy_score=s.tech_confluence_buy_score,
                       near_pct=s.tech_confluence_near_pct),
    ]


def default_universe_strategies() -> list[UniverseStrategy]:
    from ats.core.config import get_settings
    from ats.services.strategies.core_allocation import CoreAllocation
    from ats.services.strategies.library_factors import (
        CointegrationPairs,
        LowVolBAB,
        QualityFactor,
        SizeFactor,
        ValueFactor,
    )
    from ats.services.strategies.library_trend_mr import (
        CrossSectionalMomentum,
        DualMomentum,
        ShortTermReversal,
    )

    s = get_settings()
    top_n, rb = s.factor_sleeve_top_n, s.factor_sleeve_rebalance_days
    return [
        # The core ballast (three-loop plan §2): regime-aware ETF allocation,
        # weekly rebalance + immediate rebalance on regime flips. Paper from
        # day 1 by design — it is the medium loop's primary earner.
        CoreAllocation(rebalance_days=s.core_alloc_rebalance_days),
        # Original v1 universe sleeves (paper).
        PairsZScore(),
        FactorComposite(),
        NavPremium(),
        # Phase-2 cross-sectional additions (shadow).
        CrossSectionalMomentum(
            formation=s.xs_mom_formation, skip=s.xs_mom_skip,
            decile=s.xs_mom_decile, rebalance_days=s.xs_mom_rebalance_days,
        ),
        DualMomentum(lookback=s.dual_mom_lookback, top_n=s.dual_mom_top_n,
                     rebalance_days=s.xs_mom_rebalance_days),
        ShortTermReversal(lookback=s.st_reversal_lookback, decile=s.st_reversal_decile,
                          adx_window=s.st_reversal_adx_window, adx_max=s.st_reversal_adx_max),
        ValueFactor(top_n=top_n, rebalance_calendar_days=rb),
        QualityFactor(top_n=top_n, rebalance_calendar_days=rb),
        SizeFactor(top_n=top_n, rebalance_calendar_days=rb),
        LowVolBAB(top_n=top_n, rebalance_calendar_days=rb),
        CointegrationPairs(
            formation=s.coint_formation, z_window=s.coint_z_window,
            entry_z=s.coint_entry_z, exit_z=s.coint_exit_z,
            reselect_days=s.coint_reselect_days,
        ),
    ]
