"""Dedicated single-factor sleeves and cointegration-based pairs.

``FactorComposite`` blends momentum/low-vol/value/quality into one score, which
makes attribution muddy. These split each classic factor into its own sleeve so
every one accrues an independent paper track record (the whole point of running
a "plethora" of strategies for a month). All ship ``status="shadow"``.

References:
- Fama & French (1992/1993) — value (book-to-market / earnings yield).
- Asness, Frazzini & Pedersen (2019) — Quality Minus Junk (QMJ).
- Frazzini & Pedersen (2014) — Betting Against Beta / low-volatility.
- Banz (1981) — the size effect.
- Engle & Granger (1987); Gatev, Goetzmann & Rouwenhorst (2006) — pairs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant.analysis import indicators
from quant.analysis.cointegration import engle_granger
from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.base import UniverseStrategy

_EXCLUDE = frozenset({"SILVERBEES.NS", "GOLDBEES.NS", "NIFTYBEES.NS"})


def _is_equity(symbol: str) -> bool:
    return not symbol.startswith("^") and "=" not in symbol and symbol not in _EXCLUDE


class _FactorSleeve(UniverseStrategy):
    """Shared scaffolding for fundamentals-driven single-factor sleeves.

    Subclasses implement ``score(symbols, fundamentals)`` returning a
    percentile-ranked Series (higher = more attractive). The base handles
    rebalance cadence, top-N selection, conviction shaping, and flattening
    names that drop out of the basket.
    """

    style = "factor"  # slow sleeve: never dampened by the regime tilt

    def __init__(self, top_n: int = 8, rebalance_calendar_days: int = 90) -> None:
        self.top_n = top_n
        self.rebalance_calendar_days = rebalance_calendar_days
        self.min_bars = 30
        self._last_rebalance = None
        self._basket: set[str] = set()
        self._fundamentals = None

    def set_fundamentals(self, provider) -> None:
        self._fundamentals = provider

    def _fund(self) -> dict[str, dict]:
        if self._fundamentals is None:
            return {}
        try:
            return self._fundamentals() or {}
        except Exception:  # noqa: BLE001 - a bad provider must not kill the sleeve
            return {}

    def score(self, symbols: list[str], fundamentals: dict[str, dict],
              history: dict[str, pd.DataFrame]) -> pd.Series:  # pragma: no cover - abstract
        raise NotImplementedError

    def evaluate_universe(self, history: dict[str, pd.DataFrame]) -> list[SignalModel]:
        if not history:
            return []
        day = max(df.index[-1] for df in history.values()).date()
        if (
            self._last_rebalance is not None
            and (day - self._last_rebalance).days < self.rebalance_calendar_days
        ):
            return []
        symbols = [s for s in history if _is_equity(s)]
        scores = self.score(symbols, self._fund(), history).dropna().sort_values(ascending=False)
        if scores.empty:
            return []
        top = set(scores.head(self.top_n).index)
        signals: list[SignalModel] = []
        for sym in sorted(top):
            sc = float(scores[sym])
            signals.append(self._signal(sym, Stance.BUY, 0.3 + 0.5 * sc,
                                        score=round(sc, 3), rebalance=day.isoformat()))
        for sym in sorted(self._basket - top):
            signals.append(self._signal(sym, Stance.NEUTRAL, 0.0, rebalance=day.isoformat()))
        self._basket = top
        self._last_rebalance = day
        return signals

    @staticmethod
    def _rank(values: dict[str, float], ascending_is_better: bool = False) -> pd.Series:
        """Percentile rank in [0,1]; higher = better. ``ascending_is_better``
        flips so that *smaller* raw values (cheap P/E, low beta) score high."""
        if not values:
            return pd.Series(dtype=float)
        s = pd.Series(values, dtype=float)
        return (-s if ascending_is_better else s).rank(pct=True)


class ValueFactor(_FactorSleeve):
    """Value sleeve — Fama & French (1992/1993).

    Cheap stocks (low P/E and low P/B) outperform over the long run. Scores the
    average percentile of earnings-yield and book-yield (i.e. *inverse* P/E and
    P/B). Names with non-positive ratios (loss-makers) are dropped from that leg.
    """

    id = "value_factor"

    def score(self, symbols, fundamentals, history):
        pe = {s: fundamentals[s]["pe"] for s in symbols
              if s in fundamentals and (fundamentals[s].get("pe") or 0) > 0}
        pb = {s: fundamentals[s]["pb"] for s in symbols
              if s in fundamentals and (fundamentals[s].get("pb") or 0) > 0}
        pe_rank = self._rank(pe, ascending_is_better=True)   # low PE -> high score
        pb_rank = self._rank(pb, ascending_is_better=True)
        return pd.concat([pe_rank, pb_rank], axis=1).mean(axis=1, skipna=True)


class QualityFactor(_FactorSleeve):
    """Quality (QMJ) sleeve — Asness, Frazzini & Pedersen (2019).

    Profitable, well-run, safe companies command a premium. Scores high ROE and
    high profit margin (profitability) against low debt-to-equity (safety).
    """

    id = "quality_qmj"

    def score(self, symbols, fundamentals, history):
        roe = {s: fundamentals[s]["roe"] for s in symbols
               if s in fundamentals and fundamentals[s].get("roe") is not None}
        pm = {s: fundamentals[s]["profit_margin"] for s in symbols
              if s in fundamentals and fundamentals[s].get("profit_margin") is not None}
        de = {s: fundamentals[s]["debt_to_equity"] for s in symbols
              if s in fundamentals and (fundamentals[s].get("debt_to_equity") is not None
                                        and fundamentals[s]["debt_to_equity"] >= 0)}
        roe_rank = self._rank(roe)                          # high ROE -> high score
        pm_rank = self._rank(pm)
        de_rank = self._rank(de, ascending_is_better=True)  # low leverage -> high score
        return pd.concat([roe_rank, pm_rank, de_rank], axis=1).mean(axis=1, skipna=True)


class SizeFactor(_FactorSleeve):
    """Size sleeve — Banz (1981).

    Smaller-cap stocks have historically earned a premium over large caps.
    Scores the inverse of market capitalization (smallest = highest score).
    Falls back to recent dollar-volume as a liquidity-aware size proxy when a
    market cap is unavailable.
    """

    id = "size_factor"

    def score(self, symbols, fundamentals, history):
        mc: dict[str, float] = {}
        for s in symbols:
            cap = fundamentals.get(s, {}).get("market_cap")
            if cap is None and s in history and len(history[s]) >= 20:
                px = history[s]
                cap = float((px["close"] * px["volume"]).tail(20).mean())
            if cap and cap > 0:
                mc[s] = cap
        return self._rank(mc, ascending_is_better=True)     # small cap -> high score


class LowVolBAB(_FactorSleeve):
    """Low-volatility / Betting-Against-Beta — Frazzini & Pedersen (2014).

    Low-risk stocks deliver higher risk-adjusted returns than CAPM predicts.
    Price-only (no fundamentals needed): scores the inverse of a blend of beta
    to the market index and own annualized volatility, so the lowest-risk names
    rank highest. Beta uses the configured ``benchmark`` index when present.
    """

    id = "low_vol_bab"

    def __init__(self, top_n: int = 8, rebalance_calendar_days: int = 90,
                 vol_window: int = 120, beta_window: int = 120,
                 benchmark: str = "^NSEI") -> None:
        super().__init__(top_n, rebalance_calendar_days)
        self.vol_window, self.beta_window = vol_window, beta_window
        self.benchmark = benchmark
        self.min_bars = max(vol_window, beta_window) + 5

    def score(self, symbols, fundamentals, history):
        bench = history.get(self.benchmark)
        bench_ret = (
            bench["close"].pct_change().tail(self.beta_window)
            if bench is not None and len(bench) > self.beta_window else None
        )
        risk: dict[str, float] = {}
        for s in symbols:
            df = history.get(s)
            if df is None or len(df) < self.min_bars:
                continue
            vol = indicators.annualized_volatility(df["close"].tail(self.vol_window))
            if not np.isfinite(vol) or vol <= 0:
                continue
            beta = self._beta(df, bench_ret)
            # Blend standardized beta and vol; both "lower is better".
            risk[s] = 0.5 * vol + 0.5 * (abs(beta) * vol if beta is not None else vol)
        return self._rank(risk, ascending_is_better=True)   # low risk -> high score

    def _beta(self, df: pd.DataFrame, bench_ret: pd.Series | None) -> float | None:
        if bench_ret is None:
            return None
        stock_ret = df["close"].pct_change()
        aligned = pd.concat([stock_ret.rename("s"), bench_ret.rename("b")],
                            axis=1, join="inner").dropna().tail(self.beta_window)
        if len(aligned) < 30:
            return None
        var_b = float(aligned["b"].var(ddof=0))
        if var_b <= 0:
            return None
        cov = float(aligned["s"].cov(aligned["b"]))
        return cov / var_b


# Candidate pairs for cointegration screening (economically linked).
DEFAULT_CANDIDATE_PAIRS: list[tuple[str, str]] = [
    ("HDFCBANK.NS", "ICICIBANK.NS"),
    ("HDFCBANK.NS", "KOTAKBANK.NS"),
    ("ICICIBANK.NS", "AXISBANK.NS"),
    ("TCS.NS", "INFY.NS"),
    ("INFY.NS", "WIPRO.NS"),
    ("TCS.NS", "HCLTECH.NS"),
    ("RELIANCE.NS", "ONGC.NS"),
    ("MARUTI.NS", "M&M.NS"),
]


class CointegrationPairs(UniverseStrategy):
    """Cointegration pairs — Engle & Granger (1987); GGR (2006).

    Upgrades the rolling-ratio ``PairsZScore`` by *selecting* pairs that pass an
    Engle-Granger cointegration test on a formation window, then trading the
    z-score of the cointegrating residual (with the estimated hedge ratio
    ``beta``) rather than a naive log-ratio. Only pairs whose residual is
    stationary at 5% are eligible — the discipline that separates true mean
    reversion from spurious correlation. Long-only: the rich leg only flattens.
    """

    id = "coint_pairs"
    style = "stat_arb"
    long_short = True   # backtest with the short leg intact, not long-only (E1)

    def __init__(
        self,
        candidates: list[tuple[str, str]] | None = None,
        formation: int = 252,
        z_window: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        reselect_days: int = 21,
    ) -> None:
        self.candidates = candidates if candidates is not None else list(DEFAULT_CANDIDATE_PAIRS)
        self.formation, self.z_window = formation, z_window
        self.entry_z, self.exit_z = entry_z, exit_z
        self.reselect_days = reselect_days
        self.min_bars = formation + 5
        self._last_select = None
        # {(a,b): beta} for pairs that currently pass cointegration.
        self._active: dict[tuple[str, str], float] = {}

    def symbols(self) -> list[str]:
        return sorted({s for pair in self.candidates for s in pair})

    def _reselect(self, history: dict[str, pd.DataFrame], day) -> None:
        active: dict[tuple[str, str], float] = {}
        for a, b in self.candidates:
            da, db = history.get(a), history.get(b)
            if da is None or db is None:
                continue
            closes = pd.concat([da["close"].rename("a"), db["close"].rename("b")],
                               axis=1, join="inner").dropna().tail(self.formation)
            if len(closes) < self.formation:
                continue
            res = engle_granger(np.log(closes["a"].to_numpy()),
                                np.log(closes["b"].to_numpy()))
            if res.cointegrated and np.isfinite(res.beta) and res.beta > 0:
                active[(a, b)] = res.beta
        self._active = active
        self._last_select = day

    def evaluate_universe(self, history: dict[str, pd.DataFrame]) -> list[SignalModel]:
        if not history:
            return []
        day = max(df.index[-1] for df in history.values()).date()
        if self._last_select is None or (day - self._last_select).days >= self.reselect_days:
            self._reselect(history, day)

        signals: list[SignalModel] = []
        for (a, b), beta in self._active.items():
            da, db = history.get(a), history.get(b)
            if da is None or db is None:
                continue
            closes = pd.concat([da["close"].rename("a"), db["close"].rename("b")],
                               axis=1, join="inner").dropna()
            if len(closes) < self.z_window + 5:
                continue
            spread = np.log(closes["a"]) - beta * np.log(closes["b"])
            mean = spread.rolling(self.z_window, min_periods=self.z_window).mean()
            std = spread.rolling(self.z_window, min_periods=self.z_window).std(ddof=0)
            last_std = float(std.iloc[-1])
            if not np.isfinite(last_std) or last_std <= 0:
                continue
            z = float((spread.iloc[-1] - mean.iloc[-1]) / last_std)
            feats = {"pair": f"{a}/{b}", "beta": round(beta, 3), "zscore": round(z, 2)}
            if z >= self.entry_z:
                conv = min(1.0, 0.4 + 0.3 * (z - self.entry_z))
                signals.append(self._signal(b, Stance.BUY, conv, **feats))
                signals.append(self._signal(a, Stance.SELL, conv, **feats))
            elif z <= -self.entry_z:
                conv = min(1.0, 0.4 + 0.3 * (-z - self.entry_z))
                signals.append(self._signal(a, Stance.BUY, conv, **feats))
                signals.append(self._signal(b, Stance.SELL, conv, **feats))
            elif abs(z) <= self.exit_z:
                signals.append(self._signal(a, Stance.NEUTRAL, 0.0, **feats))
                signals.append(self._signal(b, Stance.NEUTRAL, 0.0, **feats))
        return signals
